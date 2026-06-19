"""
Bower Ag CowCare Tool — Entity Extractor
Sprint 5: Extract product name, location code, and container size from a query.

Uses a small Claude call returning JSON only.
Falls back to regex-based extraction if LLM is unavailable.
Location codes must be one of: EVANS, ULYSSES, JEROME, TURLOCK, TULARE or null.
"""

import json
import logging
import os
import re
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Valid location codes (from Bower Ag's 5 branches)
# ─────────────────────────────────────────────────────────────────────────────

VALID_LOCATIONS = {"EVANS", "ULYSSES", "JEROME", "TURLOCK", "TULARE"}

# Location name → code mapping for regex fallback
_LOCATION_ALIASES: dict[str, str] = {
    "evans": "EVANS",
    "evans co": "EVANS",
    "colorado": "EVANS",
    "ulysses": "ULYSSES",
    "ulysses ks": "ULYSSES",
    "kansas": "ULYSSES",
    "jerome": "JEROME",
    "jerome id": "JEROME",
    "idaho": "JEROME",
    "turlock": "TURLOCK",
    "turlock ca": "TURLOCK",
    "tulare": "TULARE",
    "tulare ca": "TULARE",
    "california": "TURLOCK",  # Default CA to Turlock
}

# Known product names for regex fallback
_KNOWN_PRODUCTS = [
    "Curiass", "Pavise", "Shield", "Aegis", "ABS Express",
    "CD114", "Acid Foam", "Acid Blend", "Acidishine",
    "HydroSurge", "Chlor-Clean", "Power Wash",
]

_CONTAINER_PATTERNS = re.compile(
    r"\b(\d+[\.\d]*)\s*-?\s*(gallon|gal|drum|tote|pail|jug)\b",
    re.IGNORECASE,
)


def _regex_extract_entities(query: str) -> dict:
    """
    Regex-based entity extraction fallback when LLM is unavailable.
    Extracts product_name, location_code, and container_size using patterns.
    """
    result = {"product_name": None, "location_code": None, "container_size": None}

    query_lower = query.lower()

    # Extract location
    for alias, code in _LOCATION_ALIASES.items():
        if alias in query_lower:
            result["location_code"] = code
            break

    # Extract product name (case-insensitive match of known products)
    for product in _KNOWN_PRODUCTS:
        if product.lower() in query_lower:
            result["product_name"] = product
            break

    # Extract container size
    match = _CONTAINER_PATTERNS.search(query)
    if match:
        size = match.group(1)
        unit = match.group(2).capitalize()
        if unit == "Gal":
            unit = "Gallon"
        result["container_size"] = f"{size}-{unit}"

    return result

EXTRACTION_PROMPT = """\
You are an entity extractor for a dairy industry product system (Bower Ag).

Extract the following entities from this query. Return ONLY valid JSON, nothing else.

{{
  "product_name": "<product name or null if not mentioned>",
  "location_code": "<one of EVANS, ULYSSES, JEROME, TURLOCK, TULARE or null>",
  "container_size": "<container size like '55-Gallon Drum', '275-Gallon Tote', \
'2.5-Gallon Jug', '5-Gallon Pail' or null>"
}}

Rules:
- product_name: Extract the product name as mentioned (e.g., "Curiass", "Shield", \
"CD114", "Pavise"). Keep the original name, don't add suffixes.
- location_code: Must be EXACTLY one of: EVANS, ULYSSES, JEROME, TURLOCK, TULARE. \
If the user mentions a location by city name, map it. If no location, return null.
- container_size: Common sizes include 55-Gallon Drum, 275-Gallon Tote, \
2.5-Gallon Jug, 5-Gallon Pail, 15-Gallon Drum, 30-Gallon Drum. If not mentioned, null.

Return ONLY the JSON object. No markdown, no explanation.

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
# Entity extraction
# ─────────────────────────────────────────────────────────────────────────────

def extract_entities(query: str) -> dict:
    """
    Extract product_name, location_code, and container_size from a query.

    Args:
        query: The user's natural language dairy query.

    Returns:
        {
            "product_name": str | None,
            "location_code": str | None,   # Validated against VALID_LOCATIONS
            "container_size": str | None,
        }
    """
    client = _get_client()

    default = {"product_name": None, "location_code": None, "container_size": None}

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=200,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT.format(query=query),
            }],
        )

        raw_text = response.content[0].text.strip()

        # Strip markdown code fences if Claude wraps the JSON
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            # Remove first and last lines (```json and ```)
            raw_text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        result = json.loads(raw_text)

        # Validate location code
        loc = result.get("location_code")
        if loc and loc.upper() not in VALID_LOCATIONS:
            result["location_code"] = None
        elif loc:
            result["location_code"] = loc.upper()

        # Ensure all keys exist
        for key in default:
            if key not in result:
                result[key] = None

        return result

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"[ENTITY_EXTRACTOR] JSON parse error: {str(e)[:200]}")
        return _regex_extract_entities(query)
    except Exception as e:
        print(f"[ENTITY_EXTRACTOR] Error extracting entities: {str(e)[:200]}")
        # Fallback to regex-based extraction
        fallback = _regex_extract_entities(query)
        if any(v is not None for v in fallback.values()):
            logger.info(f"[ENTITY_EXTRACTOR] LLM failed, regex fallback → {fallback}")
        return fallback
