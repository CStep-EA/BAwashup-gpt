"""
Bower Ag CowCare Tool — Domain Classifier
Sprint 5: Classify a dairy query into one of the known domains.

Uses a small Claude call (max_tokens=50) with LRU cache for identical queries.
Returns 'UNKNOWN' if the response is not a valid domain.
"""

import os
from functools import lru_cache
from typing import Optional

import anthropic

# ─────────────────────────────────────────────────────────────────────────────
# Valid domains (must match DOMAIN_ADDENDUM keys + PRICING)
# ─────────────────────────────────────────────────────────────────────────────

VALID_DOMAINS = {"TEAT_DIP", "CHEMICAL_CIP", "PRICING", "TROUBLESHOOTING", "COW_HEALTH"}

CLASSIFICATION_PROMPT = """\
You are a dairy industry domain classifier for Bower Ag.

Classify the following dairy query into EXACTLY ONE of these domains:
- TEAT_DIP: teat dip products, pre-dip, post-dip, iodine, CLO2, Curiass, Pavise, Shield, germicide, emollient
- CHEMICAL_CIP: CIP, clean-in-place, acid wash, alkaline, detergent, sanitizer, CD114, wash cycle, pipeline
- PRICING: price, cost, per gallon, per drum, how much, what does it cost, sellable, available, do you carry
- TROUBLESHOOTING: bacteria, SPC, water quality, hardness, flow, pressure, liner, pulsation, vacuum, CIP flow, plug, clog
- COW_HEALTH: mastitis, teat end, hyperkeratosis, scoring, dry cow, fresh cow, milking procedure, udder, calf, colostrum

If the query involves pricing or cost of a product, ALWAYS classify as PRICING.
If the query spans multiple domains, prioritize PRICING first, then product-specific, then advisory.

Return ONLY the domain name (one word). Nothing else.

Query: {query}"""

# ─────────────────────────────────────────────────────────────────────────────
# Singleton client
# ─────────────────────────────────────────────────────────────────────────────

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ─────────────────────────────────────────────────────────────────────────────
# Domain classifier with LRU cache
# ─────────────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=100)
def classify_domain(query: str) -> str:
    """
    Classify a dairy query into one of: TEAT_DIP, CHEMICAL_CIP, PRICING,
    TROUBLESHOOTING, COW_HEALTH.  Returns 'UNKNOWN' if unrecognizable.

    Uses a small Claude call (max_tokens=50).
    LRU-cached: identical queries return the same result without an API call.

    Args:
        query: The user's natural language dairy query.

    Returns:
        One of VALID_DOMAINS or 'UNKNOWN'.
    """
    client = _get_client()

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(query=query),
            }],
        )

        raw = response.content[0].text.strip().upper()

        # Clean up: sometimes Claude wraps in quotes or adds explanation
        # Take just the first word/line
        domain = raw.split("\n")[0].split(".")[0].strip().strip('"').strip("'")

        if domain in VALID_DOMAINS:
            return domain

        # Try partial match (e.g., "TEAT DIP" -> "TEAT_DIP")
        normalized = domain.replace(" ", "_")
        if normalized in VALID_DOMAINS:
            return normalized

        return "UNKNOWN"

    except Exception as e:
        print(f"[CLASSIFIER] Error classifying query: {str(e)[:200]}")
        return "UNKNOWN"
