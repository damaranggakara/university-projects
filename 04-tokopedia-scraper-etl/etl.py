"""ETL for scraped Tokopedia listings.

Extract  : raw scrape CSV (strings as they appear on the page)
Transform: parse Indonesian currency and sales text into numerics, normalise ratings,
           derive a promo flag and a clean location
Load     : SQLite warehouse (data/tokopedia.db) with a product dimension and a
           listing fact table, plus inventory-analysis views

Run:  python etl.py
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "tokopedia_raw.csv"
DB = ROOT / "data" / "tokopedia.db"


# --------------------------------------------------------------------------- transform

def parse_rupiah(value):
    """'Rp2.000.000' -> 2000000. Indonesian format uses '.' as thousands separator."""
    if pd.isna(value):
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


def parse_sold(value):
    """'100+ terjual' -> 100,  '17 terjual' -> 17,  missing -> None.

    The '+' means "at least", so the number is a floor, not an exact count.
    """
    if pd.isna(value):
        return None
    m = re.search(r"([\d.,]+)\s*(rb|jt)?", str(value), re.I)
    if not m:
        return None
    n = float(m.group(1).replace(".", "").replace(",", "."))
    unit = (m.group(2) or "").lower()
    if unit == "rb":
        n *= 1_000
    elif unit == "jt":
        n *= 1_000_000
    return int(n)


def transform(df):
    out = pd.DataFrame()
    out["product_name"] = df["Produk"].astype(str).str.strip()
    out["price_idr"] = df["Harga"].map(parse_rupiah)
    out["has_promo"] = df["Promo"].notna()
    out["promo_text"] = df["Promo"].where(df["Promo"].notna())
    out["rating"] = pd.to_numeric(df["Rating"], errors="coerce")
    out["units_sold_min"] = df["Terjual"].map(parse_sold)
    out["seller"] = df["Penjual"].astype(str).str.strip()
    out["location"] = df["Lokasi"].astype(str).str.strip()
    out["revenue_floor_idr"] = out["price_idr"] * out["units_sold_min"]
    return out


# ------------------------------------------------------------------------------- load

def load(df, db_path=DB):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    sellers = (df[["seller", "location"]].drop_duplicates()
                 .reset_index(drop=True).rename_axis("seller_id").reset_index())
    listings = df.merge(sellers, on=["seller", "location"], how="left")
    listings = listings.drop(columns=["seller", "location"]).rename_axis("listing_id").reset_index()

    sellers.to_sql("dim_seller", con, index=False)
    listings.to_sql("fact_listing", con, index=False)
    con.executescript("""
        CREATE VIEW v_inventory_by_location AS
        SELECT s.location,
               COUNT(*)                       AS listings,
               ROUND(AVG(f.price_idr))        AS avg_price_idr,
               SUM(COALESCE(f.units_sold_min, 0)) AS units_sold_min
        FROM fact_listing f JOIN dim_seller s USING (seller_id)
        GROUP BY s.location ORDER BY listings DESC;

        CREATE VIEW v_top_sellers AS
        SELECT s.seller, COUNT(*) AS listings,
               SUM(COALESCE(f.revenue_floor_idr, 0)) AS revenue_floor_idr
        FROM fact_listing f JOIN dim_seller s USING (seller_id)
        GROUP BY s.seller ORDER BY revenue_floor_idr DESC;
    """)
    con.commit()
    return con


# ------------------------------------------------------------------------------- main

def main():
    raw = pd.read_csv(RAW)
    df = transform(raw)

    assert len(df) == len(raw), "row count changed during transform"
    assert df["price_idr"].notna().all(), "every listing must have a parsed price"
    assert (df["price_idr"] > 0).all(), "prices must be positive"
    assert parse_rupiah("Rp2.000.000") == 2_000_000
    assert parse_rupiah("Rp115.000") == 115_000
    assert parse_sold("100+ terjual") == 100
    assert parse_sold("17 terjual") == 17
    assert parse_sold(None) is None

    con = load(df)
    print(f"loaded {len(df)} listings into {DB.relative_to(ROOT)}\n")

    print("price (IDR):")
    p = df["price_idr"]
    print(f"   min {p.min():,}   median {int(p.median()):,}   max {p.max():,}")
    print(f"   promo listings: {int(df['has_promo'].sum())}/{len(df)}")
    print(f"   rating present: {df['rating'].notna().sum()}/{len(df)}"
          f"   sales figure present: {df['units_sold_min'].notna().sum()}/{len(df)}\n")

    print("listings by location:")
    for row in con.execute("SELECT * FROM v_inventory_by_location LIMIT 5"):
        print(f"   {row[0]:<18} {row[1]:>3} listings   avg Rp{int(row[2]):,}")

    print("\ntop sellers by floor revenue:")
    for row in con.execute("SELECT * FROM v_top_sellers LIMIT 5"):
        print(f"   {row[0]:<22} {row[1]:>2} listings   >= Rp{int(row[2]):,}")
    con.close()
    print("\nOK: ETL completed and assertions passed.")


if __name__ == "__main__":
    main()
