"""
Bower Ag CowCare Tool — Domain Classifier
Sprint 5: Classify a dairy query into one of the known domains.

Uses a small Claude call (max_tokens=50) with LRU cache for identical queries.
Falls back to keyword-based classification if LLM is unavailable.
Returns 'UNKNOWN' if the response is not a valid domain.
"""

import logging
import os
import re
from functools import lru_cache
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

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
# Keyword-based fallback classifier (no LLM needed)
# ─────────────────────────────────────────────────────────────────────────────

# Pattern tuples: (compiled_regex, domain)
# Order matters — PRICING checked first per Document B priority rules.
_KEYWORD_PATTERNS: list[tuple[re.Pattern, str]] = [
    # PRICING — cost/price/availability keywords
    (re.compile(
        r"\b(price|pricing|cost|how much|per gallon|per drum|per pail|"
        r"per unit|what does .* cost|expense|quote|rate card|"
        r"do you carry|available at|sell at|retail)\b",
        re.IGNORECASE,
    ), "PRICING"),
    # TEAT_DIP — teat dip products and related
    (re.compile(
        r"\b(teat dips?|pre[- ]?dips?|post[- ]?dips?|curiass|pavise|shield|"
        r"aegis|barrier dips?|germicide|emollient|iodine dip|"
        r"chlorhexidine|clo2 dip|teat spray)\b",
        re.IGNORECASE,
    ), "TEAT_DIP"),
    # CHEMICAL_CIP — cleaning chemicals and CIP
    (re.compile(
        r"\b(cip|clean.in.place|acid wash|alkaline|detergent|sanitizer|"
        r"chlorinated|pipeline clean|wash cycle|cd114|acid foam|"
        r"bulk tank clean|milk stone|rinse)\b",
        re.IGNORECASE,
    ), "CHEMICAL_CIP"),
    # TROUBLESHOOTING — dairy system issues
    (re.compile(
        r"\b(bacteria|spc|coliform|water quality|hardness|flow rate|"
        r"pressure|liner|pulsation|vacuum|plug|clog|high count|"
        r"plate count|bulk tank|lab results|scc)\b",
        re.IGNORECASE,
    ), "TROUBLESHOOTING"),
    # COW_HEALTH — animal health topics
    (re.compile(
        r"\b(mastitis|teat end|hyperkeratosis|dry cow|fresh cow|"
        r"milking procedure|udder health|calf|colostrum|"
        r"somatic cell|teat condition|teat score|clinical)\b",
        re.IGNORECASE,
    ), "COW_HEALTH"),
]


def _keyword_classify(query: str) -> Optional[str]:
    """
    Fast keyword-based domain classification.
    Returns domain string if a clear match is found, None otherwise.
    Used as fallback when LLM classifier is unavailable.
    """
    for pattern, domain in _KEYWORD_PATTERNS:
        if pattern.search(query):
            return domain
    return None


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
        # Fallback to keyword-based classification when LLM unavailable
        fallback = _keyword_classify(query)
        if fallback:
            logger.info(f"[CLASSIFIER] LLM failed, keyword fallback → {fallback}")
            return fallback
        return "UNKNOWN"
