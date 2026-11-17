"""Load the cleaned e-commerce dataset into PostgreSQL.

The coursework had a gap: `Data Cleaning.ipynb` writes a CSV, and `SQL Insights.ipynb`
queries `public.ecommerce_cleaned`, but nothing ever created that table, so the notebook
only ran if the CSV had been imported by hand in pgAdmin. This closes the pipeline.

Two things need reconciling between the CSV and the SQL:
  * the queries use lower-case identifiers (PostgreSQL folds unquoted names to lower case)
  * the CSV calls the income band `Income_Class`; the queries call it `income_level`

Run:  python load_to_postgres.py
"""
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.types import Numeric

ROOT = Path(__file__).parent
CSV = ROOT / "data" / "ecommerce_cleaned.csv"
TABLE = "ecommerce_cleaned"

RENAME = {"income_class": "income_level"}
REQUIRED = ["age", "gender", "income_level", "purchase_amount",
            "frequency_of_purchase", "loyalty_member"]


def engine_from_env():
    user = os.environ.get("POSTGRES_USER", "postgres")
    pwd = os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("ECOMMERCE_DB", "ecommerce")
    if not pwd:
        sys.exit("POSTGRES_PASSWORD is not set - copy .env.example to .env and fill it in.")
    return create_engine(f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}",
                         client_encoding="utf8")


def main():
    df = pd.read_csv(CSV)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns=RENAME)

    missing = [c for c in REQUIRED if c not in df.columns]
    assert not missing, f"cleaned CSV is missing columns the SQL needs: {missing}"
    assert len(df) > 0, "cleaned CSV is empty"

    eng = engine_from_env()
    # MySQL's ROUND(x, 2) accepts floats; PostgreSQL's two-argument round() is defined
    # only for numeric, not double precision. Loading float columns as NUMERIC fixes
    # every downstream ROUND(..., 2) at the boundary instead of rewriting each query.
    dtypes = {c: Numeric(14, 4) for c in df.columns if str(df[c].dtype).startswith("float")}
    df.to_sql(TABLE, eng, if_exists="replace", index=False, dtype=dtypes)

    with eng.connect() as con:
        n = con.execute(text(f"SELECT COUNT(*) FROM public.{TABLE}")).scalar()
        # POSIX class rather than a hex range: inside an f-string the escape for a null
        # byte would expand into a real control character and truncate the statement.
        nonascii = con.execute(text(
            f"SELECT COUNT(*) FROM public.{TABLE} WHERE location ~ '[^[:ascii:]]'")).scalar()
        rev = con.execute(text(
            f"SELECT ROUND(SUM(purchase_amount)::numeric, 2) FROM public.{TABLE}")).scalar()

    assert n == len(df), f"loaded {n} rows but CSV has {len(df)}"
    print(f"loaded {n} rows x {len(df.columns)} columns into public.{TABLE}")
    print(f"  non-ASCII locations preserved: {nonascii}")
    print(f"  total purchase amount: {rev}")
    print("\nOK: load complete and assertions passed.")


if __name__ == "__main__":
    main()
