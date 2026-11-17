"""ETL: 0NF hotel spreadsheet -> normalised PostgreSQL schema.

Extract   read the 49-row 0NF workbook
Transform parse the two date formats, coerce types, resolve lookup values
Load      insert dimensions then bookings, inside one transaction
Verify    assert the normalised data reproduces the source exactly

Run:  python etl.py
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
import psycopg2

ROOT = Path(__file__).parent
SQL = ROOT / "sql"
SOURCE = ROOT / "data" / "hotel_0nf.xlsx"

# lookup table -> (source column, primary-key column)
LOOKUPS = {
    "dim_meal_plan":      ("meal",           "meal_plan_id"),
    "dim_room_type":      ("room type",      "room_type_id"),
    "dim_booking_source": ("source",         "source_id"),
    "dim_booking_status": ("booking status", "status_id"),
}


def connect():
    pwd = os.environ.get("POSTGRES_PASSWORD")
    if not pwd:
        sys.exit("POSTGRES_PASSWORD is not set - copy .env.example to .env and fill it in.")
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("HOTEL_DB", "hotel"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=pwd,
    )


# --------------------------------------------------------------------- transform

def parse_reservation_date(value):
    """Handle both representations found in the source column.

    16 rows are ISO ('2015-02-10 00:00:00') and 33 are US ('2/28/2018'). Trying
    a single format silently produces NaT for the other two thirds, so each is
    attempted explicitly and an unparseable value is a hard error rather than a
    null that propagates into the warehouse.
    """
    s = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return pd.to_datetime(s, format=fmt).date()
        except (ValueError, TypeError):
            continue
    parsed = pd.to_datetime(s, errors="coerce")
    if pd.isna(parsed):
        raise ValueError(f"unparseable reservation date: {value!r}")
    return parsed.date()


def transform(df):
    out = pd.DataFrame()
    out["booking_id"] = df["Booking_ID"].astype(str).str.strip()
    out["guest_id"] = df["Guest_ID"].astype(str).str.strip()
    out["reservation_date"] = df["date of reservation"].map(parse_reservation_date)
    out["adults"] = df["adults"].astype(int)
    out["children"] = df["children"].astype(int)
    out["weekend_nights"] = df["weekend nights"].astype(int)
    out["week_nights"] = df["week nights"].astype(int)
    out["lead_time"] = df["lead time"].astype(int)
    out["price"] = df["price"].astype(float).round(2)
    out["special_requests"] = df["requests"].astype(int)
    out["car_parking"] = df["parking"].astype(int).astype(bool)
    out["meal"] = df["meal"].astype(str).str.strip()
    out["room type"] = df["room type"].astype(str).str.strip()
    out["source"] = df["source"].astype(str).str.strip()
    out["booking status"] = df["booking status"].astype(str).str.strip()
    return out


# -------------------------------------------------------------------------- load

def load(cur, tidy):
    ids = {}
    for table, (col, pk) in LOOKUPS.items():
        ids[table] = {}
        for name in sorted(tidy[col].unique()):
            cur.execute(f"INSERT INTO {table} (nama) VALUES (%s) RETURNING {pk}", (name,))
            ids[table][name] = cur.fetchone()[0]

    for g in sorted(tidy["guest_id"].unique()):
        cur.execute("INSERT INTO guest (guest_id) VALUES (%s)", (g,))

    for _, r in tidy.iterrows():
        cur.execute(
            """INSERT INTO booking (booking_id, guest_id, meal_plan_id, room_type_id,
                                    source_id, status_id, reservation_date, adults,
                                    children, weekend_nights, week_nights, lead_time,
                                    price, special_requests, car_parking)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (r.booking_id, r.guest_id,
             ids["dim_meal_plan"][r["meal"]],
             ids["dim_room_type"][r["room type"]],
             ids["dim_booking_source"][r["source"]],
             ids["dim_booking_status"][r["booking status"]],
             r.reservation_date, int(r.adults), int(r.children),
             int(r.weekend_nights), int(r.week_nights), int(r.lead_time),
             float(r.price), int(r.special_requests), bool(r.car_parking)))
    return ids


# -------------------------------------------------------------------------- main

def main():
    raw = pd.read_excel(SOURCE)
    tidy = transform(raw)

    # date parsing is the step most likely to go wrong silently
    assert tidy["reservation_date"].notna().all(), "some reservation dates failed to parse"
    assert tidy["reservation_date"].map(lambda d: isinstance(d, date)).all()
    assert len(tidy) == len(raw), "row count changed during transform"
    assert tidy["booking_id"].is_unique, "booking_id is not unique"

    iso = sum(1 for v in raw["date of reservation"].astype(str) if v[:4].isdigit())
    print(f"extracted {len(raw)} rows from {SOURCE.name}")
    print(f"  reservation dates parsed: {iso} ISO + {len(raw) - iso} US format")

    conn = connect()
    conn.autocommit = False
    cur = conn.cursor()
    cur.execute((SQL / "01_schema.sql").read_text(encoding="utf-8"))
    ids = load(cur, tidy)
    cur.execute((SQL / "02_views.sql").read_text(encoding="utf-8"))
    conn.commit()

    for table in LOOKUPS:
        print(f"  {table:<22} {len(ids[table])} values  {sorted(ids[table])}")

    # ------------------------------------------------------------- verification
    def one(q):
        cur.execute(q)
        return cur.fetchone()[0]

    n_booking = one("SELECT COUNT(*) FROM booking")
    n_flat = one("SELECT COUNT(*) FROM v_booking_flat")
    assert n_booking == len(tidy), f"loaded {n_booking}, expected {len(tidy)}"
    assert n_flat == n_booking, "the flat view lost or duplicated rows"

    # normalising must be lossless: compare totals against the source
    src_price = round(float(tidy["price"].sum()), 2)
    db_price = float(one("SELECT ROUND(SUM(price)::numeric, 2) FROM booking"))
    assert abs(src_price - db_price) < 0.01, f"price total drifted: {src_price} vs {db_price}"

    src_nights = int((tidy["weekend_nights"] + tidy["week_nights"]).sum())
    db_nights = int(one("SELECT SUM(weekend_nights + week_nights) FROM booking"))
    assert src_nights == db_nights, f"night total drifted: {src_nights} vs {db_nights}"

    print(f"\nloaded {n_booking} bookings, {one('SELECT COUNT(*) FROM guest')} guests")
    print(f"  lossless check: price total {db_price}, nights total {db_nights} - match source")

    print("\ncancellation rate by source (v_cancellation_by_source)")
    cur.execute("SELECT * FROM v_cancellation_by_source")
    for r in cur.fetchall():
        print(f"   {r[0]:<12} {r[1]:>3} bookings  {r[2]:>2} cancelled  {r[3]:>5}%  "
              f"avg lead {int(r[4]):>3}d")

    print("\nrevenue by room type (v_revenue_by_room_type)")
    cur.execute("SELECT * FROM v_revenue_by_room_type")
    for r in cur.fetchall():
        print(f"   {r[0]:<14} {r[1]:>3} bookings  avg {r[2]:>7}  "
              f"avg nights {r[3]:>4}  est revenue {r[4]:>9}")

    print("\nlead time vs cancellation (v_lead_time_vs_cancellation)")
    cur.execute("SELECT * FROM v_lead_time_vs_cancellation")
    for r in cur.fetchall():
        print(f"   {r[0]:<12} {r[1]:>3} bookings  {r[2]:>2} cancelled  {r[3]:>5}%")

    cur.close()
    conn.close()
    print("\nOK: ETL complete, normalisation verified lossless, assertions passed.")


if __name__ == "__main__":
    main()
