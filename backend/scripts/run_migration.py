"""
Bower Ag CowCare Tool — Master Migration Runner
Sprint 2: Runs all 3 migration scripts in sequence.

Usage:
  cd backend
  python scripts/run_migration.py           # Live run
  python scripts/run_migration.py --dry-run  # Preview only
"""

import sys
import os
import subprocess
import argparse
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPTS_DIR, "..")

MIGRATION_SCRIPTS = [
    {
        "name": "Chemical Master",
        "script": "scripts/migrate_chemical_master.py",
        "description": "Products + sellability from Chemical & CIP Master Excel",
    },
    {
        "name": "Teat Dip Master",
        "script": "scripts/migrate_teat_dip_master.py",
        "description": "Products + sellability from Teat Dip Master Excel",
    },
    {
        "name": "Pricing Sheets",
        "script": "scripts/migrate_pricing_sheets.py",
        "description": "Pricing from 4 PDF price sheets (Evans, Ulysses, Jerome, CA)",
    },
]


def run_migration(dry_run: bool = False):
    """Run all migration scripts in sequence."""
    print("=" * 70)
    print("🐄 Bower Ag CowCare — Master Migration Runner")
    print(f"   Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"   Date: {datetime.now().isoformat()}")
    print("=" * 70)

    results = []

    for i, config in enumerate(MIGRATION_SCRIPTS, 1):
        print(f"\n{'─' * 70}")
        print(f"  Step {i}/3: {config['name']}")
        print(f"  {config['description']}")
        print(f"{'─' * 70}\n")

        cmd = [sys.executable, config["script"]]
        if dry_run:
            cmd.append("--dry-run")

        try:
            result = subprocess.run(
                cmd,
                cwd=BACKEND_DIR,
                capture_output=False,
                text=True,
            )
            results.append({
                "name": config["name"],
                "exit_code": result.returncode,
                "success": result.returncode == 0,
            })
        except Exception as e:
            print(f"  ❌ Failed to run {config['script']}: {e}")
            results.append({
                "name": config["name"],
                "exit_code": -1,
                "success": False,
            })

    # Summary
    print("\n" + "=" * 70)
    print("📊 MASTER MIGRATION SUMMARY")
    print("=" * 70)
    all_pass = True
    for r in results:
        status = "✅ PASS" if r["success"] else "❌ FAIL"
        print(f"  {status}: {r['name']} (exit code: {r['exit_code']})")
        if not r["success"]:
            all_pass = False

    if all_pass:
        print("\n  🎉 All migrations completed successfully!")
    else:
        print("\n  ⚠️  Some migrations had issues — review output above.")

    print("=" * 70)

    # Remind about verification
    print("\n  Next step: python scripts/verify_migration.py")
    print("  Then review migration_reports/ for any 🔍 low-confidence flags.\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run all Bower Ag data migrations")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run)
