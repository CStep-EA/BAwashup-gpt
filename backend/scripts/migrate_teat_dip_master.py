"""
Bower Ag CowCare Tool — Teat Dip Master Migration
Sprint 2: Reads all product sheets from Teat Dip Master and upserts into Supabase.

Usage:
  cd backend
  python scripts/migrate_teat_dip_master.py
  python scripts/migrate_teat_dip_master.py --dry-run

Source: Teat_Dip_Master_v3_1_APPROVED_FULL_WITH_OFB.xlsx
  Product sheets: A1 through A8 (README and SUPPORT_OFB_Formulas are skipped)
"""

import sys
import os
import re
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from app.db.supabase_client import get_supabase_client

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
EXCEL_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "..",
                 "uploaded_files", "Teat_Dip_Master_v3_1_APPROVED_FULL_WITH_OFB.xlsx"),
    "/home/user/uploaded_files/Teat_Dip_Master_v3_1_APPROVED_FULL_WITH_OFB.xlsx",
    os.path.join(os.path.dirname(__file__), "data",
                 "Teat_Dip_Master_v3_1_APPROVED_FULL_WITH_OFB.xlsx"),
]

# Sheets that contain product data (skip README, SUPPORT_OFB_Formulas)
PRODUCT_SHEETS = [
    "A1_Iodine_Bronopol_RTU",
    "A2_Iodine_Concentrates",
    "A3_Peroxide_Oxy",
    "A4A_Lactic_Acid",
    "A4B_Glycolic_Acid",
    "A5_Barrier_Dips",
    "A6_Winter_Extreme",
    "A7_CLO2_Systems",
    "A8_Emollient_Packs",
]

# Sheet name -> germicide_type mapping (inferred from tab context)
SHEET_GERMICIDE_MAP = {
    "A1_Iodine_Bronopol_RTU": "iodine",
    "A2_Iodine_Concentrates": "iodine",
    "A3_Peroxide_Oxy": "hydrogen_peroxide",
    "A4A_Lactic_Acid": "lactic_acid",
    "A4B_Glycolic_Acid": "glycolic_acid",
    "A5_Barrier_Dips": "barrier",
    "A6_Winter_Extreme": "winter_extreme",
    "A7_CLO2_Systems": "chlorine_dioxide",
    "A8_Emollient_Packs": "emollient_pack",
}

# Sellability column -> branch_code
SELLABILITY_MAP = {
    "CA": "TURLOCK",
    "KS": "ULYSSES",
    "Jerome": "JEROME",
    "Evans": "EVANS",
}

CA_ALSO_TULARE = True

REPORT_DIR = os.path.join(os.path.dirname(__file__), "migration_reports")


class TeatDipMasterMigration:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.client = get_supabase_client()
        self.stats = {
            "products_processed": 0,
            "products_inserted": 0,
            "products_updated": 0,
            "products_skipped": 0,
            "sellability_written": 0,
            "sheets_processed": 0,
            "warnings": [],
            "errors": [],
        }
        self.locations = {}

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
        raise FileNotFoundError("Teat Dip Master Excel not found.")

    def _parse_sellability(self, value) -> bool:
        """Parse ✔/✖ sellability markers."""
        if pd.isna(value) or value is None:
            return False
        s = str(value).strip()
        if s in ("✔", "✓", "YES", "Yes", "Y", "y", "TRUE", "True", "1", "X", "x"):
            return True
        if s in ("✖", "✗", "NO", "No", "N", "n", "FALSE", "False", "0", "", "—", "-", "nan"):
            return False
        self.stats["warnings"].append(f"Ambiguous sellability: '{value}'")
        return False

    def _parse_emollient(self, emollient_str: str) -> tuple:
        """
        Parse emollient string like '2%' or '10% glycerin' or '64% emollients (from glycerin)'.
        Returns (emollient_pct: float | None, emollient_type: str | None).
        """
        if not emollient_str or emollient_str in ("None", "nan", "NaN", "—"):
            return None, None

        # Extract percentage
        pct_match = re.search(r'(\d+\.?\d*)%', emollient_str)
        pct = float(pct_match.group(1)) if pct_match else None

        # Extract type (everything after %)
        emollient_type = emollient_str
        if pct_match:
            remainder = emollient_str[pct_match.end():].strip()
            if remainder:
                # Clean up "emollients (from glycerin)" -> "glycerin"
                clean = re.sub(r'emollients?\s*\(from\s+', '', remainder, flags=re.IGNORECASE)
                clean = clean.rstrip(')')
                emollient_type = clean.strip() if clean.strip() else emollient_str
            else:
                emollient_type = None

        return pct, emollient_type

    def _parse_usage_timing(self, product_name: str, chemistry: str) -> str | None:
        """Infer usage timing from product name or chemistry context."""
        combined = f"{product_name} {chemistry}".lower()

        if "pre/post" in combined or "pre & post" in combined:
            return "both"
        if "pre-dip" in combined or "pre dip" in combined or " pre " in combined:
            return "pre"
        if "post-dip" in combined or "post dip" in combined or " post " in combined:
            return "post"

        # Barrier dips are typically post
        if "barrier" in combined:
            return "post"
        # Concentrates can be both
        if "concentrate" in combined or "conc" in combined:
            return "both"

        return "both"  # Default for teat dips

    def _is_concentrate(self, product_name: str) -> bool:
        """Detect if product is a concentrate from name."""
        lower = product_name.lower()
        return any(x in lower for x in ["concentrate", "conc)", "conc.", "(conc)"])

    def _upsert_product(self, product_name: str, row: dict, sheet: str) -> str | None:
        """Upsert a teat dip product and return its UUID."""
        if not product_name or product_name in ("None", "nan"):
            self.stats["products_skipped"] += 1
            return None

        germicide_type = SHEET_GERMICIDE_MAP.get(sheet, "unknown")
        chemistry = row.get("Chemistry") or row.get("Chemistry/Type") or ""
        emollient_raw = row.get("Emollient") or row.get("Used With") or ""

        emollient_pct, emollient_type = self._parse_emollient(str(emollient_raw))
        usage_timing = self._parse_usage_timing(product_name, str(chemistry))
        is_concentrate = self._is_concentrate(product_name)

        # For A8_Emollient_Packs, the product column is "Emollient" not "Product"
        # and they're accessories, not dips. Still product_type = 'teat_dip' (accessory)
        category = "Teat Dip"
        if sheet == "A8_Emollient_Packs":
            category = "Emollient Pack"

        product_data = {
            "product_name": product_name,
            "category": category,
            "product_type": "teat_dip",
            "germicide_type": germicide_type,
            "chemistry_type": str(chemistry) if chemistry not in ("None", "nan", "") else None,
            "usage_timing": usage_timing,
            "is_concentrate": is_concentrate,
            "emollient_pct": emollient_pct,
            "emollient_type": emollient_type,
            "active": True,
        }

        if self.dry_run:
            print(f"    [DRY RUN] Would upsert: {product_name} (germicide={germicide_type})")
            self.stats["products_inserted"] += 1
            return "dry-run-uuid"

        try:
            # Search by product_name (case-insensitive)
            result = self.client.table("products").select("id").ilike(
                "product_name", product_name
            ).execute()

            if result.data:
                # Update existing
                self.client.table("products").update(product_data).eq(
                    "id", result.data[0]["id"]
                ).execute()
                self.stats["products_updated"] += 1
                return result.data[0]["id"]
            else:
                # Insert new
                result = self.client.table("products").insert(product_data).execute()
                self.stats["products_inserted"] += 1
                return result.data[0]["id"]

        except Exception as e:
            self.stats["errors"].append(
                f"Product '{product_name}' (sheet={sheet}): {type(e).__name__}: {str(e)[:200]}"
            )
            return None

    def _upsert_sellability(self, product_id: str, row: dict):
        """Upsert sellability for a teat dip product."""
        if not product_id or product_id == "dry-run-uuid":
            if self.dry_run:
                for col, code in SELLABILITY_MAP.items():
                    if col in row:
                        s = self._parse_sellability(row[col])
                        print(f"      [DRY RUN] {code}: {'✔' if s else '✖'}")
                        self.stats["sellability_written"] += 1
                        if code == "TURLOCK" and CA_ALSO_TULARE:
                            self.stats["sellability_written"] += 1
            return

        for col, branch_code in SELLABILITY_MAP.items():
            if col not in row:
                continue

            location_id = self.locations.get(branch_code)
            if not location_id:
                continue

            sellable = self._parse_sellability(row[col])

            try:
                self.client.table("product_sellability").upsert(
                    {
                        "product_id": product_id,
                        "location_id": location_id,
                        "sellable": sellable,
                    },
                    on_conflict="product_id,location_id",
                ).execute()
                self.stats["sellability_written"] += 1

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
                    f"Sellability {branch_code} for '{product_id}': {str(e)[:200]}"
                )

    def _process_sheet(self, xl: pd.ExcelFile, sheet: str):
        """Process a single product sheet."""
        df = pd.read_excel(xl, sheet_name=sheet)
        self.stats["sheets_processed"] += 1

        # Determine the product name column
        product_col = "Product"
        if sheet == "A8_Emollient_Packs":
            product_col = "Emollient"

        if product_col not in df.columns:
            self.stats["warnings"].append(f"Sheet '{sheet}': No '{product_col}' column found")
            return

        print(f"\n  ─── {sheet} ({len(df)} rows) ───")

        for _, row in df.iterrows():
            row_dict = row.to_dict()
            product_name = row_dict.get(product_col)

            if pd.isna(product_name) or not str(product_name).strip():
                self.stats["products_skipped"] += 1
                continue

            product_name = str(product_name).strip()
            self.stats["products_processed"] += 1

            print(f"    [{self.stats['products_processed']}] {product_name}", end="")

            product_id = self._upsert_product(product_name, row_dict, sheet)
            if product_id:
                self._upsert_sellability(product_id, row_dict)
                print(" ✔")
            else:
                print(" ✖")

    def run(self):
        """Execute the Teat Dip Master migration."""
        print("=" * 70)
        print("🧴 Teat Dip Master Migration")
        print(f"   Mode: {'DRY RUN' if self.dry_run else 'LIVE'}")
        print("=" * 70)

        self._load_locations()

        path = self._find_excel()
        print(f"  📂 Reading: {path}")

        xl = pd.ExcelFile(path)
        print(f"  📑 Sheets found: {xl.sheet_names}")
        print(f"  📑 Product sheets to process: {len(PRODUCT_SHEETS)}")

        for sheet in PRODUCT_SHEETS:
            if sheet in xl.sheet_names:
                self._process_sheet(xl, sheet)
            else:
                self.stats["warnings"].append(f"Sheet '{sheet}' not found in workbook")

        self._save_report()
        self._print_summary()

    def _save_report(self):
        """Save migration report."""
        os.makedirs(REPORT_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        report_path = os.path.join(REPORT_DIR, f"{timestamp}_teat_dip_master.txt")

        with open(report_path, "w") as f:
            f.write("Bower Ag CowCare — Teat Dip Master Migration Report\n")
            f.write(f"Date: {datetime.now().isoformat()}\n")
            f.write(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE'}\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Sheets processed:   {self.stats['sheets_processed']}\n")
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

        print(f"\n  📝 Report saved: {report_path}")

    def _print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 70)
        print("📊 TEAT DIP MASTER MIGRATION SUMMARY")
        print("=" * 70)
        print(f"  Sheets processed:   {self.stats['sheets_processed']}")
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

        print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate Teat Dip Master Excel to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    migration = TeatDipMasterMigration(dry_run=args.dry_run)
    migration.run()
