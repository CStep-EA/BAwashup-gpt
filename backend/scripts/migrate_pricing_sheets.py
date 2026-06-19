"""
Bower Ag CowCare Tool — PDF Pricing Sheet Migration
Sprint 2: Extracts pricing from 4 PDF files and upserts into Supabase.

Handles two PDF formats:
  1. CLEAN TABLES (Evans, Ulysses) — pdfplumber table extraction
  2. OCR/MESSY TEXT (Jerome, California) — regex-based text parsing

⚠️  LOW CONFIDENCE FLAGGING:
  Any field parsed from messy OCR text where confidence < 98% is flagged
  with 🔍 in the migration report for manual review.

Usage:
  cd backend
  python scripts/migrate_pricing_sheets.py
  python scripts/migrate_pricing_sheets.py --dry-run
"""

import sys
import os
import re
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pdfplumber
from dotenv import load_dotenv

load_dotenv()

from app.db.supabase_client import get_supabase_client

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
UPLOAD_DIR = "/home/user/uploaded_files"
FALLBACK_DIR = os.path.join(os.path.dirname(__file__), "data")

PDF_CONFIG = [
    {
        "filename": "Evans Colorado Cow Care Retail Price Sheet 21026.pdf",
        "branch_codes": ["EVANS"],
        "parse_mode": "table",
        "label": "Evans CO",
    },
    {
        "filename": "Ulysees Kansas Cow Care Retail Price Sheet 21026.pdf",
        "branch_codes": ["ULYSSES"],
        "parse_mode": "table",
        "label": "Ulysses KS",
    },
    {
        "filename": "Jerome Idaho Cow Care Retail Price Sheet 22026.pdf",
        "branch_codes": ["JEROME"],
        "parse_mode": "text",
        "label": "Jerome ID",
    },
    {
        "filename": "Turlock and Tulare California Cow Care Retail Price Sheet 2102026.pdf",
        "branch_codes": ["TURLOCK", "TULARE"],
        "parse_mode": "text",
        "label": "Turlock/Tulare CA",
    },
]

REPORT_DIR = os.path.join(os.path.dirname(__file__), "migration_reports")


def clean_price(price_str: str) -> float | None:
    """
    Clean price strings with embedded spaces from PDF extraction.
    Examples: '$ 3 8.42' -> 38.42, '$ 1 ,856.90' -> 1856.90, '$8.06' -> 8.06
    Returns None if unparseable.
    """
    if not price_str or price_str in ("None", "nan", "#N/A", "N/A", ""):
        return None

    # Remove $ sign, commas, and extra whitespace
    cleaned = price_str.replace("$", "").replace(",", "").strip()

    # Remove all spaces between digits (PDF artifact: '3 8.42' -> '38.42')
    cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned)
    cleaned = re.sub(r'(\d)\s+(\d)', r'\1\2', cleaned)  # Run twice for '1 ,8 56'
    cleaned = cleaned.strip()

    if not cleaned or cleaned == "-":
        return None

    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def compute_price_confidence(raw: str, parsed: float | None) -> int:
    """
    Estimate confidence (0-100) of a parsed price value.
    Returns lower confidence for OCR artifacts.
    """
    if parsed is None:
        return 0

    if not raw:
        return 0

    raw_clean = raw.strip()

    # Perfect: clean format like '$8.06' or '$ 8.06'
    if re.match(r'^\$\s*\d+[\d,]*\.\d{2}$', raw_clean):
        return 100

    # Good: has $ and a number but some spaces
    if "$" in raw_clean and re.search(r'\d+\.\d{2}', raw_clean.replace(" ", "")):
        # Count artifacts
        spaces_in_number = len(re.findall(r'\d\s+\d', raw_clean))
        if spaces_in_number == 0:
            return 99
        elif spaces_in_number <= 2:
            return 95
        else:
            return 85

    # Moderate: from OCR text line parsing
    if re.search(r'\d+\.\d{2}', raw_clean):
        return 90

    # Low: heavily mangled
    return 70


class PricingMigration:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_supabase_client()
        self.locations = {}
        self.products_cache = []  # All products for fuzzy matching
        self.stats = {
            "pdfs_processed": 0,
            "pricing_inserted": 0,
            "pricing_skipped_existing": 0,
            "pricing_skipped_no_match": 0,
            "warnings": [],
            "errors": [],
            "low_confidence": [],  # 🔍 Items needing review
        }

    def _load_locations(self):
        """Load location UUIDs."""
        result = self.client.table("locations").select("*").execute()
        for loc in result.data:
            self.locations[loc["branch_code"]] = loc["id"]
        print(f"  📍 Loaded {len(self.locations)} locations")

    def _load_products(self):
        """Load all products for fuzzy name matching."""
        result = self.client.table("products").select("id,product_name,part_number").execute()
        self.products_cache = result.data or []
        print(f"  📦 Loaded {len(self.products_cache)} products for matching")

    def _find_pdf(self, filename: str) -> str | None:
        """Find PDF file from known paths."""
        for base_dir in [UPLOAD_DIR, FALLBACK_DIR, os.path.dirname(__file__)]:
            path = os.path.join(base_dir, filename)
            if os.path.exists(path):
                return path
        return None

    def _match_product(self, name: str, part_number: str | None) -> dict | None:
        """
        Match a product by part_number (exact) or product_name (fuzzy).
        Returns product dict or None.
        """
        if not name and not part_number:
            return None

        # Exact part_number match
        if part_number and part_number not in ("#N/A", "N/A", "nan", "None", ""):
            pn_clean = part_number.strip()
            for p in self.products_cache:
                if p.get("part_number") and p["part_number"].strip() == pn_clean:
                    return p

        # Fuzzy name match (case-insensitive, strip whitespace)
        if name and name not in ("#N/A", "N/A", "nan", "None", ""):
            name_lower = name.strip().lower()

            # Exact case-insensitive match
            for p in self.products_cache:
                if p["product_name"].strip().lower() == name_lower:
                    return p

            # Partial match (name contained in product or vice versa)
            for p in self.products_cache:
                pname = p["product_name"].strip().lower()
                if name_lower in pname or pname in name_lower:
                    return p

            # Fuzzy: first word match (for "AcidSpl, MSR, 15 gal." -> "AcidSpl")
            first_word = re.split(r'[\s,]+', name_lower)[0]
            if len(first_word) >= 3:
                for p in self.products_cache:
                    pname = p["product_name"].strip().lower()
                    p_first = re.split(r'[\s,]+', pname)[0]
                    if first_word == p_first:
                        return p

        return None

    def _insert_pricing(self, product_id: str, location_id: str,
                        container_size: str, uom: str,
                        price_per_unit: float, extended_price: float | None,
                        raw_price: str = "", raw_extended: str = "",
                        source_label: str = ""):
        """Insert a pricing row if no active row exists."""
        # Check confidence
        conf_unit = compute_price_confidence(raw_price, price_per_unit)
        conf_ext = compute_price_confidence(raw_extended, extended_price) if extended_price else 100

        flag = ""
        if conf_unit < 98:
            flag = f"🔍 LOW CONFIDENCE ({conf_unit}%)"
            self.stats["low_confidence"].append(
                f"{source_label} | price_per_unit={price_per_unit} "
                f"(raw='{raw_price}', confidence={conf_unit}%)"
            )
        if conf_ext < 98 and extended_price:
            if not flag:
                flag = f"🔍 LOW CONFIDENCE ext ({conf_ext}%)"
            self.stats["low_confidence"].append(
                f"{source_label} | extended_price={extended_price} "
                f"(raw='{raw_extended}', confidence={conf_ext}%)"
            )

        if self.dry_run:
            print(f"      [DRY RUN] ${price_per_unit:.4f}/unit, "
                  f"${extended_price:.2f if extended_price else 0} ext "
                  f"{flag}")
            self.stats["pricing_inserted"] += 1
            return

        try:
            # Check if active pricing already exists for this product+location+container
            existing = (
                self.client.table("pricing")
                .select("id")
                .eq("product_id", product_id)
                .eq("location_id", location_id)
                .eq("container_size", container_size)
                .is_("superseded_date", "null")
                .execute()
            )

            if existing.data:
                self.stats["pricing_skipped_existing"] += 1
                return

            self.client.table("pricing").insert({
                "product_id": product_id,
                "location_id": location_id,
                "container_size": container_size,
                "uom": uom or "Gal",
                "price_per_unit": price_per_unit,
                "extended_price": extended_price,
                "version": 1,
            }).execute()
            self.stats["pricing_inserted"] += 1

            if flag:
                print(f"      {flag}")

        except Exception as e:
            self.stats["errors"].append(
                f"Pricing insert: {str(e)[:200]}"
            )

    # ═══════════════════════════════════════════════════════════════════════════
    # TABLE EXTRACTION (Evans, Ulysses — clean PDFs)
    # ═══════════════════════════════════════════════════════════════════════════
    def _extract_from_tables(self, pdf_path: str, branch_codes: list, label: str):
        """Extract pricing from clean table-format PDFs."""
        print(f"\n  📄 {label} — TABLE extraction mode")

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for table in tables:
                    if not table or len(table) < 2:
                        continue

                    # Detect header row
                    header = table[0]
                    header_lower = [str(h).lower() if h else "" for h in header]

                    # Find column indices
                    col_map = {}
                    for i, h in enumerate(header_lower):
                        if "product" in h and "type" not in h:
                            col_map["name"] = i
                        elif "part" in h and "number" in h:
                            col_map["part"] = i
                        elif h == "size":
                            col_map["size"] = i
                        elif h == "uom":
                            col_map["uom"] = i
                        elif "price per" in h or "per gal" in h:
                            col_map["price_per"] = i
                        elif "container" in h:
                            col_map["extended"] = i

                    if "name" not in col_map:
                        # First column is usually product name for merged tables
                        col_map.setdefault("name", 0)

                    for row in table[1:]:
                        if not row or all(not c or c == "#N/A" for c in row):
                            continue

                        name = str(row[col_map.get("name", 0)] or "").strip()
                        part_num = str(row[col_map.get("part", 1)] or "").strip() if "part" in col_map else None
                        size_raw = str(row[col_map.get("size", 2)] or "").strip() if "size" in col_map else ""
                        uom = str(row[col_map.get("uom", 3)] or "Gal").strip() if "uom" in col_map else "Gal"
                        raw_price = str(row[col_map.get("price_per", 5)] or "") if "price_per" in col_map else ""
                        raw_ext = str(row[col_map.get("extended", 6)] or "") if "extended" in col_map else ""

                        if name in ("#N/A", "N/A", "", "None", "nan"):
                            continue

                        price = clean_price(raw_price)
                        extended = clean_price(raw_ext)

                        if price is None and extended is None:
                            self.stats["warnings"].append(
                                f"{label} p{page_num+1}: No price for '{name}' "
                                f"(raw='{raw_price}', '{raw_ext}')"
                            )
                            continue

                        # If only extended price, compute per-unit
                        container_size = size_raw.replace("#N/A", "").strip() or "1"
                        try:
                            size_num = float(container_size.replace("x", "*").split("*")[0])
                        except ValueError:
                            size_num = 1

                        if price is None and extended:
                            price = round(extended / size_num, 4) if size_num > 0 else None

                        if price is None:
                            continue

                        product = self._match_product(name, part_num)
                        if not product:
                            self.stats["pricing_skipped_no_match"] += 1
                            self.stats["warnings"].append(
                                f"{label} p{page_num+1}: Product not found: '{name}' ({part_num})"
                            )
                            continue

                        for code in branch_codes:
                            loc_id = self.locations.get(code)
                            if not loc_id:
                                continue
                            self._insert_pricing(
                                product["id"], loc_id,
                                container_size, uom, price, extended,
                                raw_price, raw_ext,
                                f"{label} | {name} ({container_size} {uom})"
                            )

    # ═══════════════════════════════════════════════════════════════════════════
    # TEXT EXTRACTION (Jerome, California — messy OCR PDFs)
    # ═══════════════════════════════════════════════════════════════════════════
    def _extract_from_text(self, pdf_path: str, branch_codes: list, label: str):
        """Extract pricing from messy OCR text PDFs using regex."""
        print(f"\n  📄 {label} — TEXT/OCR extraction mode")
        print(f"      ⚠️  OCR mode: fields with <98% confidence flagged with 🔍")

        # Regex patterns for parsing messy OCR lines
        # Pattern: ProductName  PartNumber  Size  UOM  ProductType  $Price  $Extended
        # OCR artifacts: dashes (---), underscores (___), garbled chars
        price_pattern = re.compile(
            r'\$\s*([\d\s,]+\.[\d]{2})'
        )
        part_number_pattern = re.compile(
            r'((?:777-84-\d{6}-\d{3})|(?:\d{9,12})|(?:\d{7}\d*))'
        )
        size_pattern = re.compile(
            r'\b(\d+(?:\.\d+)?)\s*(?:Gal|gal|Oal|GAL)'
        )

        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue

                lines = text.strip().split('\n')

                for line in lines:
                    # Skip header/separator lines
                    if not line.strip() or line.strip().startswith("---") or line.strip().startswith("___"):
                        continue
                    if "Prepared" in line or "Printable" in line or "Price Sheet" in line:
                        continue
                    if "Part Number" in line or "Price Per" in line or "UOM" in line:
                        continue

                    # Clean OCR artifacts
                    clean_line = line
                    clean_line = re.sub(r'-{3,}', ' ', clean_line)  # Remove --- runs
                    clean_line = re.sub(r'_{3,}', ' ', clean_line)  # Remove ___ runs
                    clean_line = re.sub(r'\(cid:\d+\)', '', clean_line)  # Remove (cid:X)
                    clean_line = re.sub(r'\s{2,}', ' ', clean_line).strip()

                    if len(clean_line) < 5:
                        continue

                    # Find prices in line
                    prices = price_pattern.findall(clean_line)
                    if not prices:
                        continue

                    # Find part number
                    part_match = part_number_pattern.search(clean_line)
                    part_number = part_match.group(1).strip() if part_match else None

                    # Clean part number of OCR artifacts
                    if part_number:
                        part_number = re.sub(r'[\s-]+(?=\d)', '', part_number)
                        # Validate: GEA parts have 777-84- prefix, others are numeric
                        if not re.match(r'^(777-84-\d{6}-\d{3}|\d{6,12})$', part_number):
                            # Try to fix common OCR issues
                            pn_digits = re.sub(r'[^0-9]', '', part_number)
                            if 6 <= len(pn_digits) <= 15:
                                part_number = pn_digits
                            else:
                                part_number = None

                    # Find container size
                    size_match = size_pattern.search(clean_line)
                    container_size = size_match.group(1) if size_match else "1"

                    # Extract product name: everything before the part number or first $
                    name_end = len(clean_line)
                    if part_match:
                        name_end = min(name_end, part_match.start())
                    dollar_pos = clean_line.find('$')
                    if dollar_pos > 0:
                        name_end = min(name_end, dollar_pos)

                    product_name = clean_line[:name_end].strip()
                    # Clean product name of remaining artifacts
                    product_name = re.sub(r'[_\-·•]+\s*$', '', product_name).strip()
                    product_name = re.sub(r'^\s*[_\-·•]+', '', product_name).strip()

                    if len(product_name) < 2:
                        continue

                    # Parse prices
                    raw_price_str = prices[0] if prices else ""
                    raw_ext_str = prices[1] if len(prices) > 1 else ""

                    price_per = clean_price("$" + raw_price_str) if raw_price_str else None
                    extended = clean_price("$" + raw_ext_str) if raw_ext_str else None

                    if price_per is None and extended is None:
                        continue

                    # Compute per-unit if only extended available
                    try:
                        size_num = float(container_size)
                    except ValueError:
                        size_num = 1

                    if price_per is None and extended and size_num > 0:
                        price_per = round(extended / size_num, 4)

                    if price_per is None:
                        continue

                    # Confidence check on the whole parsed line
                    raw_for_conf = f"${raw_price_str}"
                    conf = compute_price_confidence(raw_for_conf, price_per)

                    # Also check product name confidence
                    name_conf = 100
                    if re.search(r'[_\-]{2,}', product_name) or '(cid:' in line:
                        name_conf = 80
                        self.stats["low_confidence"].append(
                            f"🔍 {label} p{page_num+1}: Product name may be garbled: "
                            f"'{product_name}' (raw line: '{line[:80]}...')"
                        )
                    elif re.search(r'[^\x20-\x7E]', product_name):
                        name_conf = 90

                    # Match product
                    product = self._match_product(product_name, part_number)
                    if not product:
                        self.stats["pricing_skipped_no_match"] += 1
                        self.stats["warnings"].append(
                            f"{label} p{page_num+1}: Product not found: "
                            f"'{product_name}' (part={part_number})"
                        )
                        continue

                    for code in branch_codes:
                        loc_id = self.locations.get(code)
                        if not loc_id:
                            continue
                        self._insert_pricing(
                            product["id"], loc_id,
                            container_size, "Gal", price_per, extended,
                            raw_for_conf,
                            f"${raw_ext_str}" if raw_ext_str else "",
                            f"{label} p{page_num+1} | {product_name} ({container_size} Gal)"
                        )

    def run(self):
        """Execute pricing migration for all PDFs."""
        print("=" * 70)
        print("💰 PDF Pricing Sheet Migration")
        print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("=" * 70)

        self._load_locations()
        self._load_products()

        for config in PDF_CONFIG:
            path = self._find_pdf(config["filename"])
            if not path:
                self.stats["errors"].append(
                    f"PDF not found: {config['filename']}"
                )
                print(f"\n  ❌ PDF not found: {config['filename']}")
                continue

            self.stats["pdfs_processed"] += 1

            if config["parse_mode"] == "table":
                self._extract_from_tables(path, config["branch_codes"], config["label"])
            else:
                self._extract_from_text(path, config["branch_codes"], config["label"])

        self._save_report()
        self._print_summary()

    def _save_report(self):
        """Save migration report with confidence flags."""
        os.makedirs(REPORT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        report_path = os.path.join(REPORT_DIR, f"{timestamp}_pricing_sheets.txt")

        with open(report_path, "w") as f:
            f.write("Bower Ag CowCare — Pricing Sheet Migration Report\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"PDFs processed:         {self.stats['pdfs_processed']}\n")
            f.write(f"Pricing rows inserted:  {self.stats['pricing_inserted']}\n")
            f.write(f"Skipped (existing):     {self.stats['pricing_skipped_existing']}\n")
            f.write(f"Skipped (no match):     {self.stats['pricing_skipped_no_match']}\n")
            f.write(f"Low confidence flags:   {len(self.stats['low_confidence'])}\n\n")

            if self.stats["low_confidence"]:
                f.write("=" * 70 + "\n")
                f.write("🔍 LOW CONFIDENCE ITEMS — REVIEW THESE MANUALLY\n")
                f.write("=" * 70 + "\n")
                for item in self.stats["low_confidence"]:
                    f.write(f"  {item}\n")
                f.write("\n")

            if self.stats["warnings"]:
                f.write("WARNINGS:\n")
                for w in self.stats["warnings"]:
                    f.write(f"  ⚠️  {w}\n")
                f.write("\n")

            if self.stats["errors"]:
                f.write("ERRORS:\n")
                for e in self.stats["errors"]:
                    f.write(f"  ❌ {e}\n")

        print(f"\n  📝 Report saved: {report_path}")

    def _print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 70)
        print("📊 PRICING SHEET MIGRATION SUMMARY")
        print("=" * 70)
        print(f"  PDFs processed:         {self.stats['pdfs_processed']}")
        print(f"  Pricing rows inserted:  {self.stats['pricing_inserted']}")
        print(f"  Skipped (existing):     {self.stats['pricing_skipped_existing']}")
        print(f"  Skipped (no match):     {self.stats['pricing_skipped_no_match']}")
        print(f"  Warnings:               {len(self.stats['warnings'])}")
        print(f"  Errors:                 {len(self.stats['errors'])}")

        if self.stats["low_confidence"]:
            print(f"\n  🔍 LOW CONFIDENCE FLAGS: {len(self.stats['low_confidence'])}")
            print("  These items need manual review (confidence < 98%):")
            for item in self.stats["low_confidence"][:20]:
                print(f"    {item}")
            if len(self.stats["low_confidence"]) > 20:
                print(f"    ... and {len(self.stats['low_confidence']) - 20} more (see report file)")

        if self.stats["errors"]:
            print("\n  ❌ ERRORS:")
            for e in self.stats["errors"]:
                print(f"    {e}")

        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate pricing PDFs to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    migration = PricingMigration(dry_run=args.dry_run)
    migration.run()
