"""
Bower Ag CowCare Tool — Migration Verification Script
Sprint 2: Confirms data migrated correctly from Excel & PDF sources.

Usage:
  cd backend
  python scripts/verify_migration.py

Checks:
  1. products count > 20
  2. product_sellability count > 50
  3. pricing count > 30
  4. Each location has at least 5 sellable products
  5. Spot check: 'Curiass' exists with sellability data
  6. Spot check: Evans has at least 1 active pricing row
  7. Both product_types present (chemical + teat_dip)
  8. At least one pricing row has confidence data
  9. No orphan sellability rows (all reference valid products)
  10. No orphan pricing rows (all reference valid products)

Exit codes:
  0 = All checks PASS
  1 = One or more checks FAIL
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

load_dotenv()

from app.db.supabase_client import get_supabase_client


class MigrationVerifier:
    """Verifies Sprint 2 data migration succeeded."""

    def __init__(self):
        self.client = get_supabase_client()
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    # ─────────────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────────────

    def check(self, name: str, condition: bool, detail: str = ""):
        """Record a PASS/FAIL check."""
        if condition:
            self.passed += 1
            status = "✅ PASS"
        else:
            self.failed += 1
            status = "❌ FAIL"
        msg = f"  {status}: {name}"
        if detail and not condition:
            msg += f" — {detail}"
        print(msg)

    def warn(self, name: str, detail: str = ""):
        """Record a warning (non-fatal)."""
        self.warnings += 1
        msg = f"  ⚠️  WARN: {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)

    def _query(self, table: str, select: str = "*", limit: int = 1000):
        """Safely query a table. Returns (data_list, error_str)."""
        try:
            result = self.client.table(table).select(select).limit(limit).execute()
            return (result.data or [], None)
        except Exception as e:
            return (None, str(e)[:200])

    def _count(self, table: str) -> int:
        """Get approximate count of rows in a table."""
        data, err = self._query(table, select="id", limit=1000)
        if data is None:
            return -1
        return len(data)

    # ─────────────────────────────────────────────────────────────
    # Verification Checks
    # ─────────────────────────────────────────────────────────────

    def verify_products_count(self):
        """Check 1: products count > 20."""
        print("\n─── PRODUCTS ───")
        count = self._count("products")
        self.check(
            f"Products count > 20 (found {count})",
            count > 20,
            f"Only {count} products found — expected at least 20 from Chemical + Teat Dip masters"
        )

        # Check both product types are present
        data, err = self._query("products", select="product_type")
        if data:
            types_found = set(row.get("product_type") for row in data if row.get("product_type"))
            self.check(
                f"Both product_types present: {sorted(types_found)}",
                "chemical" in types_found and "teat_dip" in types_found,
                f"Found types: {sorted(types_found)}"
            )

            # Count per type
            chemical_count = sum(1 for r in data if r.get("product_type") == "chemical")
            teat_dip_count = sum(1 for r in data if r.get("product_type") == "teat_dip")
            print(f"     📊 Chemical products: {chemical_count}")
            print(f"     📊 Teat dip products: {teat_dip_count}")
        else:
            self.check("Both product_types present", False, err or "No product data")

    def verify_sellability_count(self):
        """Check 2: product_sellability count > 50."""
        print("\n─── PRODUCT SELLABILITY ───")
        count = self._count("product_sellability")
        self.check(
            f"Sellability count > 50 (found {count})",
            count > 50,
            f"Only {count} sellability rows — expected at least 50"
        )

    def verify_pricing_count(self):
        """Check 3: pricing count > 30."""
        print("\n─── PRICING ───")
        count = self._count("pricing")
        self.check(
            f"Pricing count > 30 (found {count})",
            count > 30,
            f"Only {count} pricing rows — expected at least 30 from 4 PDF price sheets"
        )

    def verify_location_coverage(self):
        """Check 4: Each location has at least 5 sellable products."""
        print("\n─── LOCATION COVERAGE ───")

        # Get all locations
        locations_data, err = self._query("locations", select="id,branch_code,name")
        if locations_data is None:
            self.check("Locations readable", False, err)
            return

        # Get all sellability rows with location info
        sell_data, err = self._query(
            "product_sellability",
            select="location_id,sellable",
            limit=1000
        )
        if sell_data is None:
            self.check("Sellability data readable", False, err)
            return

        # Build location_id → count of sellable products
        location_sellable_counts = {}
        for row in sell_data:
            loc_id = row.get("location_id")
            is_sellable = row.get("sellable", False)
            if is_sellable:
                location_sellable_counts[loc_id] = location_sellable_counts.get(loc_id, 0) + 1

        # Check each location
        for loc in locations_data:
            loc_id = loc["id"]
            code = loc.get("branch_code", "UNKNOWN")
            count = location_sellable_counts.get(loc_id, 0)
            self.check(
                f"Location '{code}' has ≥ 5 sellable products (found {count})",
                count >= 5,
                f"Only {count} sellable products at {code}"
            )

    def verify_curiass_spot_check(self):
        """Check 5: 'Curiass' exists in products with sellability data."""
        print("\n─── SPOT CHECK: CURIASS ───")

        # Search for Curiass product (case-insensitive via ilike)
        try:
            result = self.client.table("products") \
                .select("id,product_name,product_type") \
                .ilike("product_name", "%Curiass%") \
                .execute()
            products = result.data or []
        except Exception as e:
            self.check("Curiass product lookup", False, str(e)[:200])
            return

        self.check(
            f"Curiass exists in products (found {len(products)} match(es))",
            len(products) > 0,
            "Product 'Curiass' not found — check Chemical or Teat Dip migration"
        )

        if products:
            product_id = products[0]["id"]
            product_name = products[0]["product_name"]
            print(f"     📊 Found: '{product_name}' (type: {products[0].get('product_type')})")

            # Check sellability exists for this product
            try:
                sell_result = self.client.table("product_sellability") \
                    .select("id,location_id,sellable") \
                    .eq("product_id", product_id) \
                    .execute()
                sell_rows = sell_result.data or []
            except Exception as e:
                self.check("Curiass sellability data", False, str(e)[:200])
                return

            self.check(
                f"Curiass has sellability rows (found {len(sell_rows)})",
                len(sell_rows) > 0,
                "No sellability rows for Curiass"
            )
            if sell_rows:
                sellable_count = sum(1 for r in sell_rows if r.get("sellable"))
                print(f"     📊 Sellable at {sellable_count} of {len(sell_rows)} locations")

    def verify_evans_pricing_spot_check(self):
        """Check 6: Evans has at least 1 active pricing row."""
        print("\n─── SPOT CHECK: EVANS PRICING ───")

        # Get Evans location ID
        try:
            loc_result = self.client.table("locations") \
                .select("id,branch_code") \
                .eq("branch_code", "EVANS") \
                .execute()
            locations = loc_result.data or []
        except Exception as e:
            self.check("Evans location lookup", False, str(e)[:200])
            return

        if not locations:
            self.check("Evans location exists", False, "EVANS not in locations table")
            return

        evans_id = locations[0]["id"]

        # Get active pricing (superseded_date IS NULL)
        try:
            price_result = self.client.table("pricing") \
                .select("id,product_id,price_per_unit,extended_price,effective_date,superseded_date") \
                .eq("location_id", evans_id) \
                .is_("superseded_date", "null") \
                .execute()
            active_prices = price_result.data or []
        except Exception as e:
            self.check("Evans pricing lookup", False, str(e)[:200])
            return

        self.check(
            f"Evans has ≥ 1 active pricing row (found {len(active_prices)})",
            len(active_prices) >= 1,
            "No active pricing rows for Evans location"
        )

        if active_prices:
            # Show some price stats
            unit_prices = [
                float(r["price_per_unit"])
                for r in active_prices
                if r.get("price_per_unit") is not None
            ]
            if unit_prices:
                print(f"     📊 Evans unit prices: min=${min(unit_prices):.2f}, max=${max(unit_prices):.2f}, count={len(unit_prices)}")

    def verify_pricing_confidence(self):
        """Check 8: Confidence data stored in migration reports (not in DB column)."""
        print("\n─── PRICING CONFIDENCE ───")

        # Confidence is logged to migration_reports/, not stored as a DB column.
        # Check that the report directory has files.
        reports_dir = os.path.join(os.path.dirname(__file__), "migration_reports")
        if os.path.isdir(reports_dir):
            report_files = [f for f in os.listdir(reports_dir) if f.endswith(".txt")]
            self.check(
                f"Migration reports generated ({len(report_files)} files)",
                len(report_files) > 0,
                "No migration report files found in migration_reports/"
            )
            # Check for pricing report specifically
            pricing_reports = [f for f in report_files if "pricing" in f]
            if pricing_reports:
                latest = sorted(pricing_reports)[-1]
                report_path = os.path.join(reports_dir, latest)
                with open(report_path, "r") as f:
                    content = f.read()
                low_conf_count = content.count("LOW CONFIDENCE")
                print(f"     📊 Latest pricing report: {latest}")
                print(f"     🔍 Low confidence flags in report: {low_conf_count}")
                if low_conf_count > 0:
                    print(f"     ⚠️  Review {report_path} for items needing manual confirmation")
        else:
            self.warn("Migration reports directory not found")

    def verify_data_integrity(self):
        """Checks 9-10: No orphan rows in sellability or pricing."""
        print("\n─── DATA INTEGRITY ───")

        # Get all product IDs
        products_data, err = self._query("products", select="id", limit=1000)
        if products_data is None:
            self.check("Products readable for integrity check", False, err)
            return

        product_ids = set(row["id"] for row in products_data)

        # Check sellability references valid products
        sell_data, err = self._query("product_sellability", select="product_id", limit=1000)
        if sell_data is not None:
            orphan_sell = [r for r in sell_data if r.get("product_id") not in product_ids]
            self.check(
                f"No orphan sellability rows (orphans: {len(orphan_sell)})",
                len(orphan_sell) == 0,
                f"{len(orphan_sell)} sellability rows reference non-existent products"
            )
        else:
            self.check("Sellability integrity check", False, err)

        # Check pricing references valid products
        price_data, err = self._query("pricing", select="product_id", limit=1000)
        if price_data is not None:
            orphan_price = [r for r in price_data if r.get("product_id") not in product_ids]
            self.check(
                f"No orphan pricing rows (orphans: {len(orphan_price)})",
                len(orphan_price) == 0,
                f"{len(orphan_price)} pricing rows reference non-existent products"
            )
        else:
            self.check("Pricing integrity check", False, err)

    def verify_all_locations_have_pricing(self):
        """Check: Each location has at least 1 pricing row."""
        print("\n─── PRICING COVERAGE PER LOCATION ───")

        # Get all locations
        locations_data, err = self._query("locations", select="id,branch_code")
        if locations_data is None:
            self.check("Locations readable", False, err)
            return

        # Get pricing rows grouped by location
        pricing_data, err = self._query("pricing", select="location_id", limit=1000)
        if pricing_data is None:
            self.check("Pricing readable", False, err)
            return

        location_pricing_counts = {}
        for row in pricing_data:
            loc_id = row.get("location_id")
            location_pricing_counts[loc_id] = location_pricing_counts.get(loc_id, 0) + 1

        for loc in locations_data:
            loc_id = loc["id"]
            code = loc.get("branch_code", "UNKNOWN")
            count = location_pricing_counts.get(loc_id, 0)
            self.check(
                f"Location '{code}' has ≥ 1 pricing row (found {count})",
                count >= 1,
                f"No pricing data for {code}"
            )

    # ─────────────────────────────────────────────────────────────
    # Runner
    # ─────────────────────────────────────────────────────────────

    def run(self):
        """Run all migration verification checks."""
        print("=" * 60)
        print("🐄 Bower Ag CowCare — Migration Verification (Sprint 2)")
        print("=" * 60)

        try:
            self.verify_products_count()
            self.verify_sellability_count()
            self.verify_pricing_count()
            self.verify_location_coverage()
            self.verify_curiass_spot_check()
            self.verify_evans_pricing_spot_check()
            self.verify_pricing_confidence()
            self.verify_data_integrity()
            self.verify_all_locations_have_pricing()
        except ValueError as e:
            print(f"\n❌ CONFIGURATION ERROR: {e}")
            print("   Ensure .env has SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # ─── Summary ───
        print("\n" + "=" * 60)
        total = self.passed + self.failed
        print(f"RESULTS: {self.passed}/{total} checks passed")
        if self.warnings:
            print(f"         {self.warnings} warning(s)")

        if self.failed == 0:
            print("🎉 ALL CHECKS PASS — Migration data verified!")
            print("=" * 60)
            print("\nNext steps:")
            print("  1. Review migration_reports/ for 🔍 low-confidence OCR flags")
            print("  2. Commit Sprint 2 and push to GitHub")
            sys.exit(0)
        else:
            print(f"⚠️  {self.failed} check(s) FAILED — review above and re-run migrations.")
            print("=" * 60)
            sys.exit(1)


if __name__ == "__main__":
    verifier = MigrationVerifier()
    verifier.run()
