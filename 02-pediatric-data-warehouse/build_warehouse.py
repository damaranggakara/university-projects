"""Build the pediatric data warehouse end to end.

  1. create the normalised schema          (sql/01_normalised_schema.sql)
  2. seed reference dimensions             (sql/02_reference_data.sql)
  3. migrate the original coursework rows from data/*.xlsx
  4. generate additional synthetic patients so the warehouse has usable scale
  5. populate the fact table and views     (sql/03_build_fact.sql)
  6. verify with assertions and print a summary

All generated people are synthetic. The one patient in the source files is
already dummy data ("John Doe"), and the names added here are drawn from a
fixed list - no real patient information is involved.

Run:  python build_warehouse.py [--patients N]
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

ROOT = Path(__file__).parent
SQL = ROOT / "sql"
DATA = ROOT / "data"

RNG = random.Random(42)          # fixed seed: the build is reproducible

DEPAN_L = ["Budi", "Arif", "Rizki", "Dimas", "Fajar", "Bagus", "Yoga", "Hendra",
           "Teguh", "Galih", "Rafi", "Satria"]
DEPAN_P = ["Sari", "Dewi", "Ayu", "Intan", "Putri", "Rina", "Maya", "Lestari",
           "Anisa", "Wulan", "Citra", "Nadia"]
BELAKANG = ["Pratama", "Wijaya", "Santoso", "Nugroho", "Saputra", "Halim",
            "Permana", "Kusuma", "Hartono", "Siregar", "Maulana", "Rahayu"]
JALAN = ["Jl. Veteran", "Jl. Soekarno Hatta", "Jl. Ijen", "Jl. Diponegoro",
         "Jl. Gajayana", "Jl. Kawi", "Jl. Basuki Rahmat"]


# --------------------------------------------------------------------------- db

def connect():
    pwd = os.environ.get("POSTGRES_PASSWORD")
    if not pwd:
        sys.exit("POSTGRES_PASSWORD is not set - copy .env.example to .env and fill it in.")
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("PEDIATRIC_DB", "pediatric"),
        user=os.environ.get("POSTGRES_USER", "postgres"),
        password=pwd,
    )


def run_sql_file(cur, name):
    cur.execute((SQL / name).read_text(encoding="utf-8"))


def lookup(cur, table, key_col, id_col):
    cur.execute(f"SELECT {key_col}, {id_col} FROM {table}")
    return {k: v for k, v in cur.fetchall()}


# ------------------------------------------------------------------- generators

def paediatric_norms(age_years):
    """Plausible height and weight for a child of this age.

    Height follows a linear approximation of the WHO median curve. Weight is
    then DERIVED from a target BMI rather than drawn independently - sampling
    both separately produced incoherent pairs (a 76 cm toddler at 13 kg, BMI 23).
    Deriving weight guarantees the BMI distribution is realistic by construction.

    Still a simplification: real assessment uses BMI-for-age z-scores, which
    vary by age and sex.
    """
    height = 75 + 6.5 * (age_years - 1) + RNG.gauss(0, 3)
    height = max(55.0, height)
    target_bmi = max(11.0, RNG.gauss(16.2, 1.8))      # paediatric BMI centre/spread
    weight = target_bmi * (height / 100.0) ** 2
    return round(height, 1), round(max(3.0, weight), 2)


def make_patient(wilayah_ids):
    sex = RNG.choice("LP")
    first = RNG.choice(DEPAN_L if sex == "L" else DEPAN_P)
    age_years = RNG.randint(1, 12)
    birth = date.today() - timedelta(days=age_years * 365 + RNG.randint(0, 364))
    return dict(
        pasien_id=str(uuid.uuid4()),
        nama=f"{first} {RNG.choice(BELAKANG)}",
        tanggal_lahir=birth,
        kelamin=sex,
        alamat_jalan=f"{RNG.choice(JALAN)} No. {RNG.randint(1, 180)}",
        wilayah_id=RNG.choice(wilayah_ids),
        no_tlp=f"08{RNG.randint(1000000000, 9999999999)}",
    )


# ------------------------------------------------------------------- migration

def migrate_source(cur, wilayah_ids, dokter, diagnosis, tes, obat):
    """Load the original coursework rows into the normalised schema."""
    bio = pd.read_excel(DATA / "biodata_pasien.xlsx")
    peng = pd.read_excel(DATA / "pengkajian_pasien.xlsx")
    lab = pd.read_excel(DATA / "laboratorium.xlsx")
    kons = pd.read_excel(DATA / "konsultasi.xlsx")
    farm = pd.read_excel(DATA / "farmasi.xlsx")

    row = bio.iloc[0]
    pid = str(row["pasien_id"])
    # The source stores age, not birth date. `umur` is the age as of the LAST
    # recorded visit, not today: the assessments run 2015-2024 and start at
    # 50 cm / 3.5 kg, i.e. a newborn. Anchoring the birth date to today would
    # place it after the first visit and make every derived age wrong.
    last_visit = pd.to_datetime(peng["tanggal"]).max().date()
    birth = last_visit - timedelta(days=int(row["umur"]) * 365)
    cur.execute(
        """INSERT INTO pasien (pasien_id, nama, tanggal_lahir, kelamin,
                               alamat_jalan, wilayah_id, no_tlp)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (pid, str(row["nama"]), birth,
         "L" if str(row["kelamin"]).lower().startswith("l") else "P",
         str(row["alamat"])[:120], wilayah_ids[0], str(row["no_tlp"])[:20]))

    tb = peng["tinggi_bapak"].dropna()
    ti = peng["tinggi_ibu"].dropna()
    cur.execute(
        "INSERT INTO pasien_orangtua (pasien_id, tinggi_bapak, tinggi_ibu) VALUES (%s,%s,%s)",
        (pid, float(tb.iloc[0]) if len(tb) else None,
         float(ti.iloc[0]) if len(ti) else None))

    # one visit per assessment row
    visits = []
    for _, r in peng.iterrows():
        kid = str(uuid.uuid4())
        tanggal = pd.to_datetime(r["tanggal"]).date()
        visits.append((kid, tanggal))
        cur.execute("INSERT INTO kunjungan (kunjungan_id, pasien_id, tanggal) "
                    "VALUES (%s,%s,%s) ON CONFLICT (pasien_id, tanggal) DO NOTHING",
                    (kid, pid, tanggal))
        sis = dia = None
        tek = str(r.get("tekanan", "") or "")
        if "/" in tek:                                  # '120/80' -> two integers
            a, _, b = tek.partition("/")
            try:
                sis, dia = int(float(a)), int(float(b))
            except ValueError:
                sis = dia = None
        cur.execute(
            """INSERT INTO pengkajian (pengkajian_id, kunjungan_id, tinggi_cm,
                                       berat_kg, sistolik, diastolik, suhu_c)
               VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (kunjungan_id) DO NOTHING""",
            (str(uuid.uuid4()), kid, float(r["tinggi"]), float(r["berat"]),
             sis, dia, float(r["suhu"]) if pd.notna(r.get("suhu")) else None))

    visits = [v for v in visits if v]
    kept = [v[0] for v in visits]

    # The source lab/consultation/pharmacy rows carry a patient id but no visit
    # id, so they are distributed across that patient's visits in order. This is
    # a reconstruction, and it is why the new schema makes the visit explicit.
    for i, (_, r) in enumerate(lab.iterrows()):
        cur.execute("INSERT INTO hasil_lab (lab_id, kunjungan_id, jenis_tes_id, nilai) "
                    "VALUES (%s,%s,%s,%s)",
                    (str(uuid.uuid4()), kept[i % len(kept)],
                     tes.get(str(r["jenis_tes"]), list(tes.values())[0]),
                     _numeric(r["hasil_tes"])))

    for i, (_, r) in enumerate(kons.iterrows()):
        cur.execute("""INSERT INTO konsultasi (konsultasi_id, kunjungan_id, dokter_id,
                                               diagnosis_id, catatan)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (str(uuid.uuid4()), kept[i % len(kept)],
                     dokter.get(str(r["nama_dokter"]), list(dokter.values())[0]),
                     diagnosis.get(str(r["diagnosis"]), list(diagnosis.values())[0]),
                     str(r.get("deskripsi") or "")[:200]))

    for i, (_, r) in enumerate(farm.iterrows()):
        cur.execute("""INSERT INTO resep (resep_id, kunjungan_id, obat_id,
                                          dosis_per_hari, durasi_hari)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (str(uuid.uuid4()), kept[i % len(kept)],
                     obat.get(str(r["nama_obat"]), list(obat.values())[0]),
                     _leading_int(r.get("dosis"), 1, 6),
                     _leading_int(r.get("frekuensi"), 1, 30)))
    return 1, len(kept)


def _numeric(v, default=10.0):
    """'13.5 g/dL' -> 13.5 ; 'Normal' -> default."""
    import re
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(v))
    return float(m.group(0).replace(",", ".")) if m else default


def _leading_int(v, lo, hi):
    """'2x sehari' -> 2 ; '5 hari' -> 5, clamped into range."""
    import re
    m = re.search(r"\d+", str(v))
    return min(hi, max(lo, int(m.group(0)))) if m else lo


# ------------------------------------------------------------------- synthetic

def generate(cur, n_patients, wilayah_ids, dokter, diagnosis, tes, obat):
    dokter_ids = list(dokter.values())
    diag_ids = list(diagnosis.values())
    tes_ids = list(tes.values())
    obat_ids = list(obat.values())
    visits = 0

    for _ in range(n_patients):
        p = make_patient(wilayah_ids)
        cur.execute(
            """INSERT INTO pasien (pasien_id, nama, tanggal_lahir, kelamin,
                                   alamat_jalan, wilayah_id, no_tlp)
               VALUES (%(pasien_id)s,%(nama)s,%(tanggal_lahir)s,%(kelamin)s,
                       %(alamat_jalan)s,%(wilayah_id)s,%(no_tlp)s)""", p)
        cur.execute("INSERT INTO pasien_orangtua VALUES (%s,%s,%s)",
                    (p["pasien_id"], round(RNG.gauss(168, 6), 1), round(RNG.gauss(156, 6), 1)))

        age_years = max(1, (date.today() - p["tanggal_lahir"]).days // 365)
        used = set()
        for _ in range(RNG.randint(1, 4)):
            tanggal = date.today() - timedelta(days=RNG.randint(1, 900))
            if tanggal in used:
                continue
            used.add(tanggal)
            kid = str(uuid.uuid4())
            cur.execute("INSERT INTO kunjungan VALUES (%s,%s,%s) "
                        "ON CONFLICT (pasien_id, tanggal) DO NOTHING", (kid, p["pasien_id"], tanggal))
            h, w = paediatric_norms(age_years)
            cur.execute("""INSERT INTO pengkajian (pengkajian_id, kunjungan_id, tinggi_cm,
                                                   berat_kg, sistolik, diastolik, suhu_c)
                           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (str(uuid.uuid4()), kid, h, w,
                         RNG.randint(95, 118), RNG.randint(58, 76),
                         round(RNG.gauss(36.8, 0.5), 1)))
            cur.execute("""INSERT INTO konsultasi (konsultasi_id, kunjungan_id, dokter_id,
                                                   diagnosis_id, catatan)
                           VALUES (%s,%s,%s,%s,%s)""",
                        (str(uuid.uuid4()), kid, RNG.choice(dokter_ids),
                         RNG.choice(diag_ids), "Kondisi stabil"))
            for t in RNG.sample(tes_ids, RNG.randint(0, min(3, len(tes_ids)))):
                cur.execute("INSERT INTO hasil_lab VALUES (%s,%s,%s,%s)",
                            (str(uuid.uuid4()), kid, t, round(RNG.uniform(8, 190), 2)))
            for o in RNG.sample(obat_ids, RNG.randint(0, min(2, len(obat_ids)))):
                cur.execute("INSERT INTO resep VALUES (%s,%s,%s,%s,%s)",
                            (str(uuid.uuid4()), kid, o, RNG.randint(1, 3), RNG.randint(3, 10)))
            visits += 1
    return n_patients, visits


# ------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patients", type=int, default=60,
                    help="synthetic patients to generate in addition to the source row")
    args = ap.parse_args()

    conn = connect()
    conn.autocommit = False
    cur = conn.cursor()

    print("1. creating normalised schema")
    run_sql_file(cur, "01_normalised_schema.sql")
    print("2. seeding reference dimensions")
    run_sql_file(cur, "02_reference_data.sql")

    wilayah_ids = list(lookup(cur, "dim_wilayah", "kota", "wilayah_id").values())
    dokter = lookup(cur, "dim_dokter", "nama", "dokter_id")
    diagnosis = lookup(cur, "dim_diagnosis", "nama", "diagnosis_id")
    tes = lookup(cur, "dim_jenis_tes", "nama", "jenis_tes_id")
    obat = lookup(cur, "dim_obat", "nama", "obat_id")

    print("3. migrating original coursework rows")
    sp, sv = migrate_source(cur, wilayah_ids, dokter, diagnosis, tes, obat)
    print(f"   {sp} patient, {sv} visits from data/*.xlsx")

    print(f"4. generating {args.patients} synthetic patients")
    gp, gv = generate(cur, args.patients, wilayah_ids, dokter, diagnosis, tes, obat)
    print(f"   {gp} patients, {gv} visits")

    print("5. building fact table and views")
    run_sql_file(cur, "03_build_fact.sql")
    conn.commit()

    # ---------------------------------------------------------------- verify
    def one(q):
        cur.execute(q)
        return cur.fetchone()[0]

    n_visits = one("SELECT COUNT(*) FROM kunjungan")
    n_fact = one("SELECT COUNT(*) FROM fact_checkup")
    orphan_lab = one("""SELECT COUNT(*) FROM hasil_lab l
                        LEFT JOIN kunjungan k USING (kunjungan_id)
                        WHERE k.kunjungan_id IS NULL""")
    bad_bmi = one("SELECT COUNT(*) FROM fact_checkup WHERE bmi <= 0 OR bmi > 60")

    assert n_fact == n_visits, f"fact has {n_fact} rows, expected one per visit ({n_visits})"
    assert n_fact > 0, "fact table is empty - the defect this rebuild exists to fix"
    assert orphan_lab == 0, f"{orphan_lab} lab rows are not linked to a visit"
    assert bad_bmi == 0, f"{bad_bmi} implausible BMI values"

    print("\n6. verification")
    print(f"   patients {one('SELECT COUNT(*) FROM pasien')}"
          f"   visits {n_visits}"
          f"   fact rows {n_fact}   (one per visit)")
    print(f"   lab results {one('SELECT COUNT(*) FROM hasil_lab')}"
          f"   prescriptions {one('SELECT COUNT(*) FROM resep')}"
          f"   orphan rows {orphan_lab}")

    print("\n   nutrition status (v_nutrition_status)")
    cur.execute("SELECT * FROM v_nutrition_status")
    for r in cur.fetchall():
        print(f"      {r[0]:<14} visits {r[1]:>4}  patients {r[2]:>3}  mean BMI {r[3]:>6}")

    print("\n   top diagnoses (v_diagnosis_frequency)")
    cur.execute("SELECT * FROM v_diagnosis_frequency LIMIT 5")
    for r in cur.fetchall():
        print(f"      {r[0]:<14} {r[1]:<7} {r[2]:>4} visits  {r[3]:>5}%")

    print("\n   abnormal lab results (v_abnormal_labs) - impossible in the old schema")
    cur.execute("SELECT COUNT(*) FROM v_abnormal_labs")
    print(f"      {cur.fetchone()[0]} results outside reference range")

    cur.close()
    conn.close()
    print("\nOK: warehouse built, fact table populated, assertions passed.")


if __name__ == "__main__":
    main()
