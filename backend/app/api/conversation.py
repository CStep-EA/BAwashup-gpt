"""
Bower Ag CowCare Tool - Conversation Pipeline
Sprint 5+: POST /conversation - the main chat endpoint.

CRITICAL PIPELINE ORDER (Steps 4.1 - 4.7):
  4.1  classify_domain       - if UNKNOWN: return clarifying question
  4.2  extract_entities      - product, location, container
  4.3  Location lock         - get from session or entities; require for pricing
  4.4  Governance            - ALWAYS runs when product/location context exists:
                               - PRICING: full pipeline (exists -> sellable -> pricing)
                               - TEAT_DIP / CHEMICAL_CIP: product governance
                                 (exists -> sellable -> product details)
                               - Any domain with location but no product:
                                 product listing (all sellable products at location)
  4.5  RAG (TROUBLESHOOTING/COW_HEALTH) - advisory search -> rag_context
  4.6  call_claude           - ONLY HERE, after governance/RAG completes
  4.7  Audit log             - non-blocking, always fires (even if Claude fails)

  Claude is NEVER called before governance completes for PRICING domain.
  Product existence/sellability is checked for ALL product-related domains.
  Audit log writes even if Claude API fails.
  Conversation history capped at system_config 'chat.max_history_length'.
"""

import asyncio
import json
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, NON_CUSTOMER_ROLES, require_role
from app.core.location_lock import location_lock_store
from app.db.supabase_client import get_supabase_client
from app.services.audit_service import log_governance_action
from app.services.classifier import classify_domain
from app.services.claude_service import call_claude
from app.services.entity_extractor import extract_entities

router = APIRouter(tags=["Conversation"])

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ConversationMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ConversationRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: Optional[str] = None
    conversation_history: list[ConversationMessage] = Field(default_factory=list)


class ConversationResponse(BaseModel):
    reply: str
    domain: str
    location_locked: Optional[str] = None
    governance_applied: bool = False
    needs_location: bool = False
    llm_called: bool = False
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_max_history_length() -> int:
    """Read chat.max_history_length from system_config (default 20)."""
    try:
        client = get_supabase_client()
        result = (
            client.table("system_config")
            .select("value")
            .eq("key", "chat.max_history_length")
            .execute()
        )
        if result.data:
            val = result.data[0].get("value")
            if isinstance(val, int):
                return val
            return int(val)
    except Exception:
        pass
    return 20


def _resolve_location(location_code: str) -> Optional[dict]:
    """Resolve a location branch_code to full location record."""
    client = get_supabase_client()
    loc_result = (
        client.table("locations")
        .select("id,name,branch_code")
        .eq("branch_code", location_code.upper())
        .execute()
    )
    if loc_result.data:
        return loc_result.data[0]
    return None


def _run_governance_pipeline(
    product_name: str,
    location_code: str,
    container_size: Optional[str],
) -> dict:
    """
    Run the full governance pipeline for PRICING domain:
      1. Product exists?
      2. Product sellable at location?
      3. Get pricing

    Returns governance_data dict.
    """
    client = get_supabase_client()

    # Step 1: Product exists?
    products = (
        client.table("products")
        .select(
            "id,product_name,part_number,category,product_type,"
            "active_ingredient,chemistry_type,germicide_type,usage_timing"
        )
        .ilike("product_name", f"%{product_name}%")
        .eq("active", True)
        .limit(10)
        .execute()
    )

    if not products.data:
        # Also try part_number match
        products = (
            client.table("products")
            .select(
                "id,product_name,part_number,category,product_type,"
                "active_ingredient,chemistry_type,germicide_type,usage_timing"
            )
            .ilike("part_number", f"%{product_name}%")
            .eq("active", True)
            .limit(10)
            .execute()
        )

    if not products.data:
        return {
            "exists": False,
            "product_name": product_name,
            "message": (
                f"Product '{product_name}' is not in our current lineup. "
                "It does not exist in the Teat Dip Master or Chemical & CIP Master."
            ),
        }

    product = products.data[0]
    product_id = product["id"]

    # Step 2: Resolve location
    location = _resolve_location(location_code)
    if not location:
        return {
            "exists": True,
            "product_name": product["product_name"],
            "error": f"Location '{location_code}' not found.",
        }

    location_id = location["id"]

    # Step 3: Product sellable at location?
    sell_result = (
        client.table("product_sellability")
        .select("sellable")
        .eq("product_id", product_id)
        .eq("location_id", location_id)
        .execute()
    )

    sellable = False
    if sell_result.data:
        sellable = sell_result.data[0].get("sellable", False)

    if not sellable:
        return {
            "exists": True,
            "sellable": False,
            "product_name": product["product_name"],
            "product_type": product.get("product_type"),
            "category": product.get("category"),
            "location": location["name"],
            "location_code": location_code.upper(),
            "message": (
                f"{product['product_name']} is not currently available at "
                f"your {location['name']} location. Let's look at what we "
                f"do have that'll get you the same result."
            ),
        }

    # Step 4: Get pricing
    pricing_query = (
        client.table("pricing")
        .select(
            "container_size,uom,price_per_unit,extended_price,"
            "version,effective_date"
        )
        .eq("product_id", product_id)
        .eq("location_id", location_id)
        .is_("superseded_date", "null")
    )

    if container_size:
        pricing_query = pricing_query.eq("container_size", container_size)

    pricing_result = pricing_query.execute()
    pricing_rows = pricing_result.data or []

    return {
        "exists": True,
        "sellable": True,
        "product_name": product["product_name"],
        "part_number": product.get("part_number"),
        "category": product.get("category"),
        "product_type": product.get("product_type"),
        "active_ingredient": product.get("active_ingredient"),
        "chemistry_type": product.get("chemistry_type"),
        "usage_timing": product.get("usage_timing"),
        "location": location["name"],
        "location_code": location_code.upper(),
        "pricing": [
            {
                "container_size": p.get("container_size"),
                "uom": p.get("uom"),
                "price_per_unit": p.get("price_per_unit"),
                "extended_price": p.get("extended_price"),
                "version": p.get("version"),
                "effective_date": p.get("effective_date"),
            }
            for p in pricing_rows
        ],
        "pricing_count": len(pricing_rows),
    }


def _run_product_governance(
    product_name: str,
    location_code: Optional[str],
) -> dict:
    """
    Run product existence and sellability governance for non-PRICING domains
    (TEAT_DIP, CHEMICAL_CIP). Does NOT pull pricing.

    This ensures Claude ALWAYS knows whether a product exists and whether
    it's sellable at the rep's location - even for informational queries.

    Returns governance_data dict with product details and sellability.
    """
    client = get_supabase_client()

    # Step 1: Product exists? Search with broader matching
    products = (
        client.table("products")
        .select(
            "id,product_name,part_number,category,product_type,"
            "active_ingredient,chemistry_type,germicide_type,"
            "usage_timing,is_concentrate,emollient_pct,emollient_type,notes"
        )
        .ilike("product_name", f"%{product_name}%")
        .eq("active", True)
        .limit(10)
        .execute()
    )

    if not products.data:
        # Also try part_number match
        products = (
            client.table("products")
            .select(
                "id,product_name,part_number,category,product_type,"
                "active_ingredient,chemistry_type,germicide_type,"
                "usage_timing,is_concentrate,emollient_pct,emollient_type,notes"
            )
            .ilike("part_number", f"%{product_name}%")
            .eq("active", True)
            .limit(10)
            .execute()
        )

    if not products.data:
        return {
            "exists": False,
            "product_name": product_name,
            "message": (
                f"Product '{product_name}' is not in our current lineup. "
                "It does not exist in the Teat Dip Master or Chemical & CIP Master."
            ),
        }

    # Return all matching products with details
    product_list = []
    for product in products.data:
        product_info = {
            "product_name": product["product_name"],
            "part_number": product.get("part_number"),
            "category": product.get("category"),
            "product_type": product.get("product_type"),
            "active_ingredient": product.get("active_ingredient"),
            "chemistry_type": product.get("chemistry_type"),
            "germicide_type": product.get("germicide_type"),
            "usage_timing": product.get("usage_timing"),
            "is_concentrate": product.get("is_concentrate"),
            "emollient_pct": product.get("emollient_pct"),
            "emollient_type": product.get("emollient_type"),
            "notes": product.get("notes"),
        }

        # Check sellability if we have a location
        if location_code:
            location = _resolve_location(location_code)
            if location:
                sell_result = (
                    client.table("product_sellability")
                    .select("sellable")
                    .eq("product_id", product["id"])
                    .eq("location_id", location["id"])
                    .execute()
                )
                sellable = False
                if sell_result.data:
                    sellable = sell_result.data[0].get("sellable", False)
                product_info["sellable_at_location"] = sellable
                product_info["location"] = location["name"]
                product_info["location_code"] = location_code.upper()

        product_list.append(product_info)

    return {
        "exists": True,
        "product_name": products.data[0]["product_name"],
        "products_found": len(product_list),
        "products": product_list,
        "governance_note": (
            "These products are verified from the Bower Ag product masters. "
            "Present this data confidently - it is governance-verified."
        ),
    }


def _run_product_listing(
    location_code: str,
    product_type_filter: Optional[str] = None,
) -> dict:
    """
    List all sellable products at a given location. Optionally filter by
    product_type (teat_dip, chemical, cip).

    Used when users ask "what's available?" or "what teat dips do you have?"
    without naming a specific product.
    """
    client = get_supabase_client()

    # Resolve location
    location = _resolve_location(location_code)
    if not location:
        return {
            "error": f"Location '{location_code}' not found.",
            "products": [],
        }

    location_id = location["id"]

    # Get all sellable product IDs at this location
    sell_result = (
        client.table("product_sellability")
        .select("product_id")
        .eq("location_id", location_id)
        .eq("sellable", True)
        .execute()
    )

    if not sell_result.data:
        return {
            "location": location["name"],
            "location_code": location_code.upper(),
            "products": [],
            "message": f"No products found as sellable at {location['name']}.",
        }

    sellable_ids = [row["product_id"] for row in sell_result.data]

    # Get product details for all sellable products
    products_query = (
        client.table("products")
        .select(
            "id,product_name,part_number,category,product_type,"
            "active_ingredient,chemistry_type,germicide_type,usage_timing"
        )
        .in_("id", sellable_ids)
        .eq("active", True)
        .order("product_name")
    )

    if product_type_filter:
        products_query = products_query.eq("product_type", product_type_filter)

    products_result = products_query.execute()

    product_list = [
        {
            "product_name": p["product_name"],
            "part_number": p.get("part_number"),
            "category": p.get("category"),
            "product_type": p.get("product_type"),
            "active_ingredient": p.get("active_ingredient"),
            "chemistry_type": p.get("chemistry_type"),
            "germicide_type": p.get("germicide_type"),
            "usage_timing": p.get("usage_timing"),
        }
        for p in (products_result.data or [])
    ]

    type_label = product_type_filter or "all"
    return {
        "location": location["name"],
        "location_code": location_code.upper(),
        "product_type_filter": product_type_filter,
        "products": product_list,
        "products_count": len(product_list),
        "governance_note": (
            f"These are ALL {type_label} products confirmed sellable at "
            f"{location['name']}. This is governance-verified data from the "
            f"product sellability matrix. Present with confidence."
        ),
    }


def _run_rag_search(query: str, domain: str, limit: int = 4) -> Optional[str]:
    """
    Run RAG advisory search for TROUBLESHOOTING or COW_HEALTH domains.
    Returns formatted context string or None.
    """
    from app.api.rag import (
        _embed_query,
        _parse_embedding,
        SIMILARITY_THRESHOLD,
    )
    import numpy as np

    # Map conversation domain -> RAG domain
    domain_map = {
        "TROUBLESHOOTING": "troubleshooting",
        "COW_HEALTH": None,  # Search all domains for cow health
    }
    rag_domain = domain_map.get(domain)

    try:
        query_embedding = _embed_query(query)
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        client = get_supabase_client()

        # Need embeddings for similarity - fetch with embedding column
        qb_with_emb = client.table("document_chunks").select(
            "section_title, content, source_doc, domain, embedding"
        )
        if rag_domain:
            qb_with_emb = qb_with_emb.eq("domain", rag_domain)

        result = qb_with_emb.execute()

        if not result.data:
            return None

        scored = []
        for row in result.data:
            if not row.get("embedding"):
                continue
            doc_vec = _parse_embedding(row["embedding"])
            if doc_vec is None:
                continue
            doc_norm = np.linalg.norm(doc_vec)
            if query_norm == 0 or doc_norm == 0:
                continue
            similarity = float(np.dot(query_vec, doc_vec) / (query_norm * doc_norm))
            if similarity >= SIMILARITY_THRESHOLD:
                scored.append((similarity, row))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:limit]

        if not top:
            return None

        # Format as context string
        parts = []
        for sim, row in top:
            parts.append(
                f"[Source: {row['source_doc']} | Section: {row['section_title']} | "
                f"Domain: {row['domain']} | Relevance: {sim:.2f}]\n"
                f"{row['content'][:1000]}"
            )

        return "\n\n---\n\n".join(parts)

    except Exception as e:
        print(f"[RAG] Error during advisory search: {str(e)[:200]}")
        return None


# ---------------------------------------------------------------------------
# POST /conversation
# ---------------------------------------------------------------------------

@router.post("/conversation", response_model=ConversationResponse)
async def conversation(
    body: ConversationRequest,
    user: CurrentUser = Depends(require_role(NON_CUSTOMER_ROLES)),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
):
    """
    Main conversation endpoint - the heart of the CowCare Tool.

    Pipeline runs in EXACT order:
      4.1 -> classify_domain
      4.2 -> extract_entities
      4.3 -> Location lock
      4.4 -> Governance (ALL product-related domains)
      4.5 -> RAG (TROUBLESHOOTING / COW_HEALTH only)
      4.6 -> call_claude (ONLY after governance/RAG)
      4.7 -> Audit log (non-blocking)

    Auth: Any role except customer.
    """
    start = time.time()
    session_id = body.session_id or x_session_id or "default"

    governance_data = None
    rag_context = None
    location_locked = None
    governance_applied = False
    llm_called = False
    input_tokens = None
    output_tokens = None

    # -- 4.1: Classify domain --
    domain = classify_domain(body.message)

    if domain == "UNKNOWN":
        duration_ms = int((time.time() - start) * 1000)
        # Audit even for clarification
        asyncio.create_task(log_governance_action(
            user_id=user.id,
            action="conversation.clarify",
            domain="unknown",
            query_text=body.message,
            llm_called=False,
            response_summary="Domain unclear, asked for clarification",
            duration_ms=duration_ms,
        ))
        return ConversationResponse(
            reply=(
                "To make sure I give you the right information - are you asking "
                "about product pricing, a troubleshooting issue, or something "
                "related to cow health? A little more detail will help me get "
                "you the best answer."
            ),
            domain="UNKNOWN",
            governance_applied=False,
            llm_called=False,
        )

    # -- 4.2: Extract entities --
    entities = extract_entities(body.message)
    product_name = entities.get("product_name")
    entity_location = entities.get("location_code")
    container_size = entities.get("container_size")

    # -- 4.3: Location lock --
    # Try session lock first, then entity extraction
    location_locked = location_lock_store.get_location(session_id)

    if not location_locked and entity_location:
        # Lock to the extracted location
        location_lock_store.set_location(session_id, entity_location, user.id)
        location_locked = entity_location

    # If PRICING domain and no location - ask for it
    if domain == "PRICING" and not location_locked:
        duration_ms = int((time.time() - start) * 1000)
        asyncio.create_task(log_governance_action(
            user_id=user.id,
            action="conversation.needs_location",
            domain="pricing",
            query_text=body.message,
            llm_called=False,
            response_summary="Location required for pricing query",
            duration_ms=duration_ms,
        ))
        return ConversationResponse(
            reply=(
                "I want to make sure I get you the right pricing - which "
                "location are we looking at? We've got Evans, Ulysses, "
                "Jerome, Turlock, and Tulare."
            ),
            domain=domain,
            needs_location=True,
            governance_applied=False,
            llm_called=False,
        )

    # -- 4.4: Governance pipeline --
    # PRICING domain: full pipeline (exists -> sellable -> pricing)
    # TEAT_DIP / CHEMICAL_CIP: product governance (exists -> sellable -> details)
    # Any domain with location + no product: product listing
    if domain == "PRICING":
        if product_name:
            governance_data = _run_governance_pipeline(
                product_name=product_name,
                location_code=location_locked,
                container_size=container_size,
            )
            governance_applied = True
        elif location_locked:
            # No specific product in a pricing query but have location -
            # list all sellable products so Claude can present options
            governance_data = _run_product_listing(
                location_code=location_locked,
            )
            governance_applied = True
        else:
            # No product AND no location - ask for location first
            duration_ms = int((time.time() - start) * 1000)
            asyncio.create_task(log_governance_action(
                user_id=user.id,
                action="conversation.needs_product",
                domain="pricing",
                query_text=body.message,
                location_locked=location_locked,
                llm_called=False,
                response_summary="Product name required for pricing",
                duration_ms=duration_ms,
            ))
            return ConversationResponse(
                reply=(
                    "Sure, I can help with pricing! Which product are you "
                    "looking at? Give me the name and I'll pull the exact "
                    "numbers for your location."
                ),
                domain=domain,
                location_locked=location_locked,
                governance_applied=False,
                llm_called=False,
            )

    elif domain in ("TEAT_DIP", "CHEMICAL_CIP"):
        # Product-specific domains: ALWAYS check product governance
        if product_name:
            # Check existence + sellability (no pricing)
            governance_data = _run_product_governance(
                product_name=product_name,
                location_code=location_locked,
            )
            governance_applied = True
        elif location_locked:
            # No specific product but have location - list available products
            # of the relevant type
            type_filter = "teat_dip" if domain == "TEAT_DIP" else "chemical"
            governance_data = _run_product_listing(
                location_code=location_locked,
                product_type_filter=type_filter,
            )
            governance_applied = True
        # If no product and no location, Claude will handle with its
        # domain knowledge and governance rules (ask for specifics)

    # -- 4.5: RAG search (TROUBLESHOOTING / COW_HEALTH only) --
    if domain in ("TROUBLESHOOTING", "COW_HEALTH"):
        rag_context = _run_rag_search(body.message, domain, limit=4)

    # -- 4.6: Call Claude --
    # Cap conversation history at system_config max_history_length
    max_history = _get_max_history_length()
    history = body.conversation_history[-max_history:]

    # Build messages: history + current message
    messages = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]
    messages.append({"role": "user", "content": body.message})

    claude_error = None
    try:
        result = call_claude(
            messages=messages,
            governance_data=governance_data,
            domain=domain,
            is_report=False,
            user_role=user.role,
            location_code=location_locked,
            rag_context=rag_context,
        )
        reply = result["reply"]
        input_tokens = result["input_tokens"]
        output_tokens = result["output_tokens"]
        llm_called = True

    except Exception as e:
        claude_error = str(e)[:200]
        # Fallback: return raw governance data or a helpful message
        if governance_data:
            reply = (
                "I'm having a moment pulling together a polished response, but "
                "here's what the governance engine confirmed:\n\n"
                + json.dumps(governance_data, indent=2, default=str)
            )
        elif rag_context:
            reply = (
                "I'm having trouble putting this together right now, but "
                "here's what our advisory docs say:\n\n"
                + rag_context[:1500]
            )
        else:
            reply = (
                "I'm running into a technical issue right now. Give me a moment "
                "and try that question again - I want to make sure I get you "
                "the right answer."
            )

    # -- 4.7: Audit log (non-blocking - always fires) --
    duration_ms = int((time.time() - start) * 1000)
    asyncio.create_task(log_governance_action(
        user_id=user.id,
        action="conversation.reply",
        domain=domain.lower(),
        query_text=body.message,
        location_locked=location_locked,
        llm_called=llm_called,
        governance_result={
            "domain": domain,
            "governance_applied": governance_applied,
            "product_name": product_name,
            "location_code": location_locked,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "claude_error": claude_error,
        },
        response_summary=reply[:200],
        duration_ms=duration_ms,
    ))

    return ConversationResponse(
        reply=reply,
        domain=domain,
        location_locked=location_locked,
        governance_applied=governance_applied,
        llm_called=llm_called,
        needs_location=False,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
