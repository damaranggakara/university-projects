"""Fetch the full CDC BRFSS 2015 diabetes dataset.

The repository commits a stratified 20% sample (`diabetes_brfss2015_sample.csv`,
~4 MB) so the notebooks run on a fresh clone. The full file is 253,680 rows and
22 MB, which is most of this repository's size for a dataset that is publicly
available, so it is fetched rather than stored.

  python fetch_data.py            # download the full dataset
  python fetch_data.py --check    # report what is present locally

Requires the Kaggle API: pip install kaggle, and an API token at
~/.kaggle/kaggle.json (Kaggle > Account > Create New API Token).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DATA = Path(__file__).parent / "data"
FULL = DATA / "diabetes_brfss2015.csv"
SAMPLE = DATA / "diabetes_brfss2015_sample.csv"

SLUG = "alexteboul/diabetes-health-indicators-dataset"
MEMBER = "diabetes_012_health_indicators_BRFSS2015.csv"
EXPECTED_ROWS = 253_680


def check():
    for label, path in (("full", FULL), ("sample", SAMPLE)):
        if path.exists():
            n = sum(1 for _ in path.open(encoding="utf-8")) - 1
            print(f"  {label:<7} {path.name:<38} {n:>7,} rows  "
                  f"{path.stat().st_size / 1e6:>5.1f} MB")
        else:
            print(f"  {label:<7} {path.name:<38} not present")


def download():
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError:
        sys.exit("The kaggle package is not installed. Run: pip install kaggle")
    except OSError as e:          # missing or unreadable kaggle.json
        sys.exit(f"Kaggle credentials not found: {e}")

    api = KaggleApi()
    api.authenticate()
    DATA.mkdir(parents=True, exist_ok=True)
    print(f"downloading {SLUG} ...")
    api.dataset_download_file(SLUG, MEMBER, path=str(DATA), force=True)

    # the API may leave either the csv or a zip of it
    zipped = DATA / (MEMBER + ".zip")
    if zipped.exists():
        import zipfile
        with zipfile.ZipFile(zipped) as z:
            z.extract(MEMBER, path=DATA)
        zipped.unlink()
    (DATA / MEMBER).replace(FULL)

    n = sum(1 for _ in FULL.open(encoding="utf-8")) - 1
    print(f"saved {FULL.name}: {n:,} rows")
    if n != EXPECTED_ROWS:
        print(f"  warning: expected {EXPECTED_ROWS:,} rows - the dataset may have changed")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report local files only")
    args = ap.parse_args()
    print("local data:")
    check()
    if args.check:
        return
    if FULL.exists():
        print("\nfull dataset already present; nothing to do.")
        return
    print()
    download()


if __name__ == "__main__":
    main()
