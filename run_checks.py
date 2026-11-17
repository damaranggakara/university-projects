"""Run every project's verification script and report one table.

Each project carries its own assert-based check. Running them by hand means
nobody runs them, so this is the single entry point, and it is what CI calls.

  python run_checks.py              # everything available
  python run_checks.py --no-db      # skip checks that need PostgreSQL
  python run_checks.py -k hamming   # only checks whose name matches

Exit code is 0 only if every check that ran passed, so CI fails on regression.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent

# (project directory, script, needs_postgres, extra env)
CHECKS = [
    ("11-image-compression",          "test_hamming.py",        False, {}),
    ("11-image-compression",          "experiment_error_rate.py", False, {}),
    ("13-python-software-engineering", "smoke_test.py",          False, {}),
    ("15-symbolic-ai",                "test_reasoners.py",       False, {}),
    ("10-ml-methods-survey",          "compare_clustering.py",   False, {}),
    ("10-ml-methods-survey",          "compare_classifiers.py",  False, {}),
    ("01-credit-risk-analysis",       "test_baselines.py",       False, {}),
    ("04-tokopedia-scraper-etl",      "etl.py",                  False, {}),
    ("05-real-estate-price-prediction","test_tuning.py",          False, {}),
    ("06-diamond-price-ann",          "test_model.py",           False, {}),
    ("07-rl-trading-agent",           "test_baseline.py",        False, {}),
    ("03-twitter-sentiment-analysis", "test_classifier.py",      False, {}),
    ("14-clinical-prediction",        "test_results.py",         False, {}),
    ("09-ecommerce-analytics",        "significance_check.py",   False, {}),
    ("02-pediatric-data-warehouse",   "build_warehouse.py",      True,  {"PEDIATRIC_DB": "pediatric"}),
    ("09-ecommerce-analytics",        "load_to_postgres.py",     True,  {"ECOMMERCE_DB": "ecommerce"}),
    ("12-hotel-etl-normalisation",    "etl.py",                  True,  {"HOTEL_DB": "hotel"}),
    ("12-hotel-etl-normalisation",    "significance_check.py",   True,  {"HOTEL_DB": "hotel"}),
]


def load_dotenv():
    """Minimal .env reader - avoids a dependency for six lines of parsing."""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())


def postgres_available():
    if not os.environ.get("POSTGRES_PASSWORD"):
        return False, "POSTGRES_PASSWORD not set"
    try:
        import psycopg2
    except ImportError:
        return False, "psycopg2 not installed"
    try:
        psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            dbname="postgres",
            user=os.environ.get("POSTGRES_USER", "postgres"),
            password=os.environ["POSTGRES_PASSWORD"],
            connect_timeout=5,
        ).close()
        return True, "connected"
    except Exception as e:
        return False, type(e).__name__


def ensure_databases():
    """Create the databases the checks expect, if they are missing."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    con = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname="postgres",
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=os.environ["POSTGRES_PASSWORD"],
    )
    con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = con.cursor()
    for db in ("pediatric", "ecommerce", "hotel"):
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db,))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {db}")
    cur.close()
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-db", action="store_true", help="skip checks needing PostgreSQL")
    ap.add_argument("-k", metavar="PATTERN", help="only checks whose path matches")
    args = ap.parse_args()

    load_dotenv()
    db_ok, db_why = (False, "skipped by --no-db") if args.no_db else postgres_available()
    if db_ok:
        try:
            ensure_databases()
        except Exception as e:
            db_ok, db_why = False, f"could not create databases: {type(e).__name__}"

    print(f"python     {sys.version.split()[0]}")
    print(f"postgres   {'available' if db_ok else 'unavailable - ' + db_why}\n")

    width = max(len(f"{d}/{s}") for d, s, _, _ in CHECKS) + 2
    print(f"{'check':<{width}}{'result':<10}{'time':>7}  detail")
    print("-" * (width + 46))

    passed = failed = skipped = 0
    failures = []

    for proj, script, needs_db, extra in CHECKS:
        label = f"{proj}/{script}"
        if args.k and args.k.lower() not in label.lower():
            continue
        path = ROOT / proj / script
        if not path.exists():
            print(f"{label:<{width}}{'MISSING':<10}{'':>7}  {path.relative_to(ROOT)}")
            failed += 1
            failures.append((label, "script not found"))
            continue
        if needs_db and not db_ok:
            print(f"{label:<{width}}{'skip':<10}{'':>7}  needs PostgreSQL")
            skipped += 1
            continue

        env = {**os.environ, **extra, "PYTHONIOENCODING": "utf-8"}
        t0 = time.time()
        r = subprocess.run([sys.executable, script], cwd=ROOT / proj,
                           capture_output=True, text=True, env=env, timeout=1800)
        dt = time.time() - t0
        if r.returncode == 0:
            tail = [l for l in r.stdout.strip().splitlines() if l.strip()]
            detail = tail[-1][:48] if tail else ""
            print(f"{label:<{width}}{'PASS':<10}{dt:>6.1f}s  {detail}")
            passed += 1
        else:
            err = (r.stderr or r.stdout).strip().splitlines()
            detail = err[-1][:48] if err else f"exit {r.returncode}"
            print(f"{label:<{width}}{'FAIL':<10}{dt:>6.1f}s  {detail}")
            failed += 1
            failures.append((label, "\n".join(err[-15:])))

    print("-" * (width + 46))
    print(f"{passed} passed, {failed} failed, {skipped} skipped")

    if failures:
        print("\nfailure detail")
        for label, detail in failures:
            print(f"\n=== {label}\n{detail}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
