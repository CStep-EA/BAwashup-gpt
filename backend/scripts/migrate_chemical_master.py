"""
Bower Ag CowCare Tool — Chemical Master Migration
Sprint 2: Reads Chemical & CIP Master Excel and upserts into Supabase.

Usage:
  cd backend
  python scripts/migrate_chemical_master.py
  python scripts/migrate_chemical_master.py --dry-run

Source: Cow_Care_Chemical_Master_GOVERNANCE_CLEAN_v2.2.1.xlsx
  Sheet: 'Chemical & CIP Master v2.2'
  Headers start row 5 (0-indexed row 4)
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from app.db.supabase_client import get_supabase_client


def _sanitize_for_json(data: dict) -> dict:
    """Replace NaN/Inf float values with None so JSON serialization works."""
    clean = {}
    for k, v in data.items():
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            clean[k] = None
        elif v == "nan" or v == "None":
            clean[k] = None
        else:
            clean[k] = v
    return clean

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
EXCEL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..",
    "uploaded_files", "Cow_Care_Chemical_Master_GOVERNANCE_CLEAN_v2.2.1.xlsx"
)
# Fallback paths
EXCEL_PATHS = [
    EXCEL_PATH,
    "/home/user/uploaded_files/Cow_Care_Chemical_Master_GOVERNANCE_CLEAN_v2.2.1.xlsx",
    os.path.join(os.path.dirname(__file__), "data", "Cow_Care_Chemical_Master_GOVERNANCE_CLEAN_v2.2.1.xlsx"),
]

SHEET_NAME = "Chemical & CIP Master v2.2"
HEADER_ROW = 4  # 0-indexed: row 5 in Excel

# Map Excel column names to our sellability location codes
SELLABILITY_MAP = {
    "Sellable CA": "TURLOCK",  # CA maps to both Turlock + Tulare
    "Sellable CO": "EVANS",
    "Sellable KS": "ULYSSES",
    "Sellable Jerome": "JEROME",
    "Sellable NW": None,  # NW not a current location — log but skip
}

# CA also means Tulare
CA_ALSO_TULARE = True

REPORT_DIR = os.path.join(os.path.dirname(__file__), "migration_reports")


class ChemicalMasterMigration:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_supabase_client()
        self.stats = {
            "products_processed": 0,
            "products_inserted": 0,
            "products_updated": 0,
            "products_skipped": 0,
            "sellability_written": 0,
            "warnings": [],
            "errors": [],
        }
        self.locations = {}  # branch_code -> uuid

    def _load_locations(self):
        """Load location UUIDs from DB."""
        result = self.client.table("locations").select("*").execute()
        for loc in result.data:
            self.locations[loc["branch_code"]] = loc["id"]
        print(f"  📍 Loaded {len(self.locations)} locations: {list(self.locations.keys())}")

    def _find_excel(self) -> str:
        """Find the Excel file from known paths."""
        for path in EXCEL_PATHS:
            resolved = os.path.abspath(path)
            if os.path.exists(resolved):
                return resolved
        raise FileNotFoundError(
            f"Chemical Master Excel not found. Searched:\n"
            + "\n".join(f"  - {p}" for p in EXCEL_PATHS)
        )

    def _read_excel(self) -> pd.DataFrame:
        """Read and clean the Chemical Master sheet."""
        path = self._find_excel()
        print(f"  📂 Reading: {path}")

        df = pd.read_excel(path, sheet_name=SHEET_NAME, header=HEADER_ROW)

        # Rename columns (they come from the header row)
        # Expected: Category, Product, Manufacturer, Brand, Primary Chemistry,
        #   SDS Status, Unit of Measure, Part Number, Sellable CA, Sellable CO,
        #   Sellable KS, Sellable Jerome, Sellable NW, Notes, SDS_Product_ID
        print(f"  📊 Raw columns: {list(df.columns)}")
        print(f"  📊 Raw rows: {len(df)}")

        # Drop rows where Product is NaN (section headers, blank rows)
        df = df.dropna(subset=["Product"])

        # Drop rows where Product looks like a header (contains 'Product' text)
        df = df[~df["Product"].astype(str).str.strip().isin(["Product", ""])]

        # Strip whitespace from string columns
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace("nan", None).replace("None", None)

        print(f"  📊 Clean rows: {len(df)}")
        return df

    def _parse_sellability(self, value) -> bool:
        """Parse sellability column value to boolean."""
        if value is None:
            return False
        if isinstance(value, float) and math.isnan(value):
            return False
        if pd.isna(value):
            return False
        s = str(value).strip().upper()
        if s in ("✔", "YES", "Y", "TRUE", "1", "X", "✓"):
            return True
        if s in ("✖", "NO", "N", "FALSE", "0", "", "NAN", "NONE", "—", "-"):
            return False
        # Non-empty string might mean sellable
        self.stats["warnings"].append(f"Ambiguous sellability value: '{value}'")
        return False

    def _upsert_product(self, row: dict) -> str | None:
        """Upsert a product and return its UUID."""
        product_name = row.get("Product")
        part_number = row.get("Part Number")
        category = row.get("Category") or "Uncategorized"
        chemistry = row.get("Primary Chemistry")
        manufacturer = row.get("Manufacturer")
        brand = row.get("Brand")
        sds_status = row.get("SDS Status")
        uom = row.get("Unit of Measure")
        notes = row.get("Notes")
        sds_id = row.get("SDS_Product_ID")

        if not product_name or product_name in ("None", "nan"):
            self.stats["products_skipped"] += 1
            return None

        # Clean part number
        if part_number is None or part_number in ("None", "nan", ""):
            part_number = None
        elif isinstance(part_number, float) and math.isnan(part_number):
            part_number = None
        else:
            part_number = str(part_number).strip() or None

        product_data = _sanitize_for_json({
            "product_name": product_name,
            "part_number": part_number,
            "category": category,
            "product_type": "chemical",
            "active_ingredient": chemistry if chemistry not in ("None", "nan") else None,
            "chemistry_type": chemistry if chemistry not in ("None", "nan") else None,
            "notes": notes if notes not in ("None", "nan") else None,
            "sds_verified": sds_status == "Verified" if sds_status else False,
            "active": True,
        })

        if self.dry_run:
            print(f"    [DRY RUN] Would upsert product: {product_name} ({part_number})")
            self.stats["products_inserted"] += 1
            return "dry-run-uuid"

        try:
            # Try to find existing product by part_number first
            existing = None
            if part_number:
                result = self.client.table("products").select("id").eq(
                    "part_number", part_number
                ).execute()
                if result.data:
                    existing = result.data[0]

            # Fallback: search by product_name (case-insensitive)
            if not existing:
                result = self.client.table("products").select("id").ilike(
                    "product_name", product_name
                ).execute()
                if result.data:
                    existing = result.data[0]

            if existing:
                # Update existing
                self.client.table("products").update(product_data).eq(
                    "id", existing["id"]
                ).execute()
                self.stats["products_updated"] += 1
                return existing["id"]
            else:
                # Insert new
                result = self.client.table("products").insert(product_data).execute()
                self.stats["products_inserted"] += 1
                return result.data[0]["id"]

        except Exception as e:
            self.stats["errors"].append(
                f"Product '{product_name}': {type(e).__name__}: {str(e)[:200]}"
            )
            return None

    def _upsert_sellability(self, product_id: str, row: dict):
        """Upsert sellability records for a product across locations."""
        if not product_id or product_id == "dry-run-uuid":
            if self.dry_run:
                for col, code in SELLABILITY_MAP.items():
                    if code and col in row:
                        sellable = self._parse_sellability(row.get(col))
                        print(f"      [DRY RUN] {code}: {'✔' if sellable else '✖'}")
                        self.stats["sellability_written"] += 1
                        if code == "TURLOCK" and CA_ALSO_TULARE:
                            self.stats["sellability_written"] += 1
            return

        for col, branch_code in SELLABILITY_MAP.items():
            if branch_code is None:
                continue  # Skip NW
            if col not in row:
                continue

            location_id = self.locations.get(branch_code)
            if not location_id:
                self.stats["warnings"].append(
                    f"Location '{branch_code}' not in DB — skipping sellability"
                )
                continue

            sellable = self._parse_sellability(row.get(col))

            try:
                # Upsert: try insert, on conflict update
                self.client.table("product_sellability").upsert(
                    {
                        "product_id": product_id,
                        "location_id": location_id,
                        "sellable": sellable,
                    },
                    on_conflict="product_id,location_id",
                ).execute()
                self.stats["sellability_written"] += 1

                # CA also means Tulare
                if branch_code == "TURLOCK" and CA_ALSO_TULARE:
                    tulare_id = self.locations.get("TULARE")
                    if tulare_id:
                        self.client.table("product_sellability").upsert(
                            {
                                "product_id": product_id,
                                "location_id": tulare_id,
                                "sellable": sellable,
                            },
                            on_conflict="product_id,location_id",
                        ).execute()
                        self.stats["sellability_written"] += 1

            except Exception as e:
                self.stats["errors"].append(
                    f"Sellability '{branch_code}' for product_id={product_id}: {str(e)[:200]}"
                )

    def run(self):
        """Execute the Chemical Master migration.
        
        The Excel has multiple rows per product (one per container size / part number).
        We deduplicate by product name: insert/update ONE product row, write sellability
        once, and track all part_numbers + sizes for the pricing migration to match later.
        """
        print("=" * 70)
        print("🧪 Chemical Master Migration")
        print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("=" * 70)

        self._load_locations()
        df = self._read_excel()

        # ── Group rows by product name (deduplicate) ──
        current_category = None
        product_groups = {}  # product_name -> { "rows": [...], "category": str }

        for idx, row in df.iterrows():
            row_dict = row.to_dict()

            # Track category (it only appears in the first row of each section)
            cat = row_dict.get("Category")
            if cat and cat not in ("None", "nan"):
                current_category = cat

            product_name = row_dict.get("Product", "")
            if not product_name or product_name in ("None", "nan"):
                continue

            if product_name not in product_groups:
                product_groups[product_name] = {
                    "category": current_category,
                    "rows": [],
                }
            product_groups[product_name]["rows"].append(row_dict)

        unique_count = len(product_groups)
        print(f"\n  📊 {len(df)} Excel rows → {unique_count} unique products")
        print(f"  Processing {unique_count} unique products...\n")

        counter = 0
        for product_name, group in product_groups.items():
            counter += 1
            self.stats["products_processed"] += 1

            # Use the first row for product metadata + sellability
            first_row = group["rows"][0]
            first_row["Category"] = group["category"]

            # Prefer the first row's part_number (usually the largest container)
            # but fallback to any row that has one
            part_number = first_row.get("Part Number")
            if not part_number or str(part_number).strip() in ("", "None", "nan"):
                for r in group["rows"]:
                    pn = r.get("Part Number")
                    if pn and str(pn).strip() not in ("", "None", "nan"):
                        first_row["Part Number"] = pn
                        break

            print(f"  [{counter}] {product_name} ({len(group['rows'])} sizes)", end="")

            product_id = self._upsert_product(first_row)
            if product_id:
                self._upsert_sellability(product_id, first_row)
                print(" ✔")
            else:
                print(" ✖ (skipped)")

        self._save_report()
        self._print_summary()

    def _save_report(self):
        """Save migration report to file."""
        os.makedirs(REPORT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        report_path = os.path.join(REPORT_DIR, f"{timestamp}_chemical_master.txt")

        with open(report_path, "w") as f:
            f.write("Bower Ag CowCare — Chemical Master Migration Report\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Products processed: {self.stats['products_processed']}\n")
            f.write(f"Products inserted:  {self.stats['products_inserted']}\n")
            f.write(f"Products updated:   {self.stats['products_updated']}\n")
            f.write(f"Products skipped:   {self.stats['products_skipped']}\n")
            f.write(f"Sellability rows:   {self.stats['sellability_written']}\n\n")

            if self.stats["warnings"]:
                f.write("WARNINGS:\n")
                for w in self.stats["warnings"]:
                    f.write(f"  ⚠️  {w}\n")
                f.write("\n")

            if self.stats["errors"]:
                f.write("ERRORS:\n")
                for e in self.stats["errors"]:
                    f.write(f"  ❌ {e}\n")
                f.write("\n")

        print(f"\n  📝 Report saved: {report_path}")

    def _print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 70)
        print("📊 CHEMICAL MASTER MIGRATION SUMMARY")
        print("=" * 70)
        print(f"  Products processed: {self.stats['products_processed']}")
        print(f"  Products inserted:  {self.stats['products_inserted']}")
        print(f"  Products updated:   {self.stats['products_updated']}")
        print(f"  Products skipped:   {self.stats['products_skipped']}")
        print(f"  Sellability rows:   {self.stats['sellability_written']}")
        print(f"  Warnings:           {len(self.stats['warnings'])}")
        print(f"  Errors:             {len(self.stats['errors'])}")

        if self.stats["errors"]:
            print("\n  ❌ ERRORS:")
            for e in self.stats["errors"]:
                print(f"    {e}")

        if self.stats["warnings"]:
            print(f"\n  ⚠️  {len(self.stats['warnings'])} warning(s) — see report for details")

        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Chemical Master Excel to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    migration = ChemicalMasterMigration(dry_run=args.dry_run)
    migration.run()
