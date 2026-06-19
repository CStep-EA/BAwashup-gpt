"""
Bower Ag CowCare Tool — Claude Service
Sprint 5: System prompt assembly and Claude API calls.

CRITICAL RULE: Claude is called ONLY at Step 6 of the conversation pipeline.
              Never before governance completes for PRICING domain.

Every call logs input_tokens + output_tokens to audit_log.
"""

import json
import os
from typing import Optional

import anthropic

from app.core.prompts import BASE_SYSTEM_PROMPT, DOMAIN_ADDENDUM, REPORT_WRITING_ADDENDUM

# ─────────────────────────────────────────────────────────────────────────────
# Configuration (from Doc B §7.3)
# ─────────────────────────────────────────────────────────────────────────────

CLAUDE_MODEL = "claude-sonnet-4-20250514"
CHAT_MAX_TOKENS = 2048
REPORT_MAX_TOKENS = 4096


# ─────────────────────────────────────────────────────────────────────────────
# Singleton client
# ─────────────────────────────────────────────────────────────────────────────

_client: Optional[anthropic.Anthropic] = None


def _get_client() -> anthropic.Anthropic:
    """Lazy-load the Anthropic client (cached)."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set in environment")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


# ─────────────────────────────────────────────────────────────────────────────
# System prompt assembly (Doc B §7.1)
# ─────────────────────────────────────────────────────────────────────────────

def build_system_prompt(
    domain: str,
    is_report: bool,
    user_role: str,
    location_code: Optional[str] = None,
) -> str:
    """
    Assemble the system prompt from base + role + domain addendum + report addendum.

    Args:
        domain: Upper-case domain name (TEAT_DIP, CHEMICAL_CIP, PRICING, etc.)
        is_report: Whether this is a customer-facing report generation
        user_role: The authenticated user's role (consultant, technician, etc.)
        location_code: Currently locked location code (if any)
    """
    parts = [BASE_SYSTEM_PROMPT]

    # Role context
    parts.append(f"The current user role is: {user_role}")

    # Location context
    if location_code:
        parts.append(
            f"The current session is location-locked to: {location_code}. "
            f"All pricing in this session is for {location_code} only."
        )

    # Domain-specific addendum
    if domain and domain in DOMAIN_ADDENDUM:
        addendum = DOMAIN_ADDENDUM[domain]
        if addendum:  # Skip empty addendums (e.g., PRICING)
            parts.append(addendum)

    # Report writing rules
    if is_report:
        parts.append(REPORT_WRITING_ADDENDUM)

    return "\n\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# Claude API call (Doc B §7.1 + §7.2)
# ─────────────────────────────────────────────────────────────────────────────

def call_claude(
    messages: list[dict],
    governance_data: Optional[dict],
    domain: str,
    is_report: bool,
    user_role: str,
    location_code: Optional[str] = None,
    rag_context: Optional[str] = None,
) -> dict:
    """
    Call Claude with assembled system prompt and governance/RAG context.

    CRITICAL: This function is ONLY called at Step 6 of the pipeline.
              Governance must be complete before reaching this point.

    Args:
        messages: Conversation history [{role, content}, ...]
        governance_data: Verified governance data dict (injected as context)
        domain: Upper-case domain name
        is_report: Whether generating a customer report
        user_role: Authenticated user's role
        location_code: Session-locked location code
        rag_context: RAG advisory content string (for troubleshooting/cow_health)

    Returns:
        {
            "reply": str,           # Claude's response text
            "input_tokens": int,    # For audit logging / cost tracking
            "output_tokens": int,
            "model": str,
        }
    """
    client = _get_client()

    # Assemble system prompt
    system = build_system_prompt(domain, is_report, user_role, location_code)

    # Build the messages list — inject governance/RAG context before the
    # conversation so Claude sees it first.
    augmented_messages = []

    context_parts = []
    if governance_data:
        context_parts.append(
            "[GOVERNANCE DATA -- USE THIS EXACTLY]\n"
            + json.dumps(governance_data, indent=2, default=str)
            + "\n[END GOVERNANCE DATA]\n"
            "Do not modify, estimate, or supplement these values. "
            "Present them exactly as provided."
        )

    if rag_context:
        context_parts.append(
            "[ADVISORY REFERENCE CONTENT]\n"
            + rag_context
            + "\n[END ADVISORY REFERENCE]\n"
            "Use this content to inform your response. Cite it as Tier 3 advisory."
        )

    if context_parts:
        context_message = {
            "role": "user",
            "content": "\n\n".join(context_parts),
        }
        # Claude requires alternating user/assistant messages.
        # Inject context as a user message, then an assistant ack, then the real history.
        augmented_messages.append(context_message)
        augmented_messages.append({
            "role": "assistant",
            "content": "Understood. I have the governance and advisory data. "
                       "I'll use it exactly as provided.",
        })

    augmented_messages.extend(messages)

    max_tokens = REPORT_MAX_TOKENS if is_report else CHAT_MAX_TOKENS

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=augmented_messages,
    )

    return {
        "reply": response.content[0].text,
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "model": response.model,
    }
