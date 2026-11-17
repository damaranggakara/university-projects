# Pediatric Health Data Warehouse

A dimensional warehouse for paediatric clinic records: a normalised operational schema
(1NF → 3NF), an ETL pipeline that loads it, a star-schema fact table at visit grain, and
analysis views for nutritional status, diagnosis frequency and out-of-range lab results.

Coursework for Data Warehousing, Semester 4. Rebuilt because the original schema could
not support the questions the project set out to answer.

## Start here

**[`notebooks/normalisation_to_warehouse.ipynb`](notebooks/normalisation_to_warehouse.ipynb)**

The notebook is the main artifact. It works through 1NF → 2NF → 3NF on the real source
files, shows the defect that made the fact table impossible, builds the schema in
PostgreSQL, demonstrates the constraints by getting four inserts rejected, loads the data
and queries the result. It renders with its outputs on GitHub, so the reasoning and the
evidence are both readable without running anything.

Every claim in it is demonstrated rather than asserted. For instance, the fan trap is not
described, it is calculated:

```
records per table: {'pengkajian_pasien': 21, 'laboratorium': 21, 'konsultasi': 21, 'farmasi': 21}

unconstrained join for ONE patient: 194,481 rows
actual clinical events: 21
inflation factor: 9,261x
```

and the constraints are shown working:

```
rejected  a visit for a patient who does not exist
          violates foreign key constraint "kunjungan_pasien_id_fkey"
rejected  blood pressure with diastolic above systolic
          violates check constraint "pengkajian_check"
rejected  a patient with an invalid sex code
          violates check constraint "pasien_kelamin_check"
rejected  a patient born in the future
          violates check constraint "pasien_tanggal_lahir_check"
```

`build_warehouse.py` does the same build as a script, for repeatability; the notebook
imports it rather than duplicating the ETL.

## What was wrong with the original

The coursework had five flat tables and a `fact_checkup` that never contained a single row.
Three concrete defects:

**No referential integrity.** `laboratorium`, `konsultasi` and `farmasi` had **no
`pasien_id` column at all**: the `CREATE TABLE` omitted it, even though every source
spreadsheet supplies one. A lab result could not be traced to a patient, so the most basic
clinical question ("which of this child's results were abnormal?") was unanswerable.

**An unpopulatable fact table.** `fact_checkup`'s primary key was five columns
(`pasien_id`, `pengkajian_id`, `laboratorium_id`, `konsultasi_id`, `farmasi_id`). Since the
dimension tables had no patient key, nothing could be joined, and the table sat at 0 rows.
Worse, had it been joined naively, 21 records in each of four tables would have produced
21⁴ = **194,481 rows for one patient**, every measure double-counted, a textbook fan trap.

**Values that were not atomic, and data that did not belong.** Blood pressure was the
string `'120/80'`. Dosage was `'2x sehari'`. Father's and mother's height were repeated on
every checkup row.

## The normalised schema

`sql/01_normalised_schema.sql`. Each change below is marked in the DDL with a `DECISION`
comment naming the normal form it satisfies.

### 1NF: atomic values

| Original | Problem | Now |
|---|---|---|
| `tekanan varchar` = `'120/80'` | two measurements in one field | `sistolik int`, `diastolik int` |
| `dosis varchar` = `'2x sehari'` | must be parsed before use | `dosis_per_hari int` |
| `frekuensi varchar` = `'5 hari'` | must be parsed before use | `durasi_hari int` |
| `alamat text` = street + city + province | composite | `alamat_jalan` + FK to `dim_wilayah` |

Splitting blood pressure also allows a real constraint: `CHECK (sistolik > diastolik)`.

### 2NF: no partial dependencies

`tinggi_bapak` and `tinggi_ibu` sat on every row of `pengkajian_pasien`. Parental height is
a fact about the **patient**, not about an individual checkup, so storing it per visit
repeats it and invites contradiction. It now lives in `pasien_orangtua`, one row per
patient.

### 3NF: no transitive dependencies

The original repeated free text on every transaction row. Each of these attributes depends
on an entity, not on the transaction:

| Repeated text | Depends on | New dimension |
|---|---|---|
| `nama_dokter` | the doctor | `dim_dokter` (+ `spesialisasi`) |
| `jenis_tes` | the test type | `dim_jenis_tes` (+ unit, reference range) |
| `nama_obat` | the drug | `dim_obat` (+ form, strength) |
| `diagnosis` | the diagnosis | `dim_diagnosis` (+ ICD-10 code) |
| city, province | the region | `dim_wilayah` |

Normalising the lab test type is what makes `v_abnormal_labs` possible: reference ranges
now live with the test rather than nowhere at all.

### Derived data removed

The original stored `umur` (age) as an integer. Age is a function of birth date and the
current date, so a stored copy goes stale silently. The schema stores `tanggal_lahir`, and
age is derived per visit, which matters here, because the source records span ten years of
one child's growth.

### The visit entity

The fix that makes everything else work: `kunjungan` (visit). Every clinical record hangs
off a visit, and a visit belongs to exactly one patient, so every join path is unambiguous.

```
dim_wilayah ──┐
              ├── pasien ──┬── pasien_orangtua
dim_dokter ─┐ │            └── kunjungan ──┬── pengkajian   (1:1)
dim_diagnosis┼─┼── konsultasi ──────────────┤
dim_jenis_tes┼─┼── hasil_lab ───────────────┤
dim_obat ────┴─┴── resep ───────────────────┘
                                             └── fact_checkup (1 row per visit)
```

## The fact table

`sql/03_build_fact.sql`. **Grain: one row per visit.** Labs and prescriptions are
many-per-visit, so they are aggregated in subqueries *before* joining, which is what
avoids the fan trap. Measures: height, weight, BMI, BMI category, temperature, blood
pressure, lab count, prescription count, total medication days.

## Results

```
patients 61   visits 167   fact rows 167   (one per visit)
lab results 227   prescriptions 184   orphan rows 0

nutrition status            visits  patients  mean BMI
   Gizi Kurang                  14        12     13.26
   Normal                      108        55     16.07
   Gizi Lebih                   26        22     18.87
   Obesitas                     19         2     30.48

top diagnoses
   Alergi        T78.4    33 visits   19.8%
   Batuk         R05      33 visits   19.8%
   Gizi Kurang   E44.0    29 visits   17.4%
   Sehat         Z00.1    27 visits   16.2%

abnormal lab results: 137 outside reference range
```

The fact table has one row per visit and zero orphaned records: the two properties the
original schema could not achieve.

## Data

**All of it is synthetic.** The single patient in the source spreadsheets was already dummy
data (named "John Doe", UUID identifiers, "Dr. Andi", generic diagnoses). `build_warehouse.py`
migrates those 21 assessments and generates 60 further patients with 146 visits, from fixed
name lists and a seeded RNG, so builds are reproducible. No real patient information is
involved at any point.

Two honest caveats about the data:

**The source records are internally inconsistent.** They track one child across 2015-2024,
starting at 50 cm / 3.5 kg (a newborn) and reaching 27.5 kg, but height plateaus at 90 cm,
which is toddler range, while weight follows a normal ten-year curve. BMI therefore climbs
to 34 and all 18 of that patient's later visits classify as "Obesitas". The arithmetic is
right; the input never followed a growth curve. This is why 19 of the 21 Obesitas visits
belong to one patient.

Generating the synthetic patients surfaced the same trap: drawing height and weight
independently produced a 76 cm toddler weighing 13 kg (BMI 23). The generator now draws
height from the median curve and **derives** weight from a target BMI, so pairs are coherent
by construction.

**Diagnoses are assigned at random** to synthetic visits, so they do not correlate with the
computed BMI category. A "Gizi Kurang" diagnosis on a normal-BMI visit is an artefact of
dummy data, not a modelling claim.

**BMI banding is simplified.** Fixed cut-offs are used; real paediatric assessment uses
BMI-for-age z-scores against WHO growth standards, which vary by age and sex. The thresholds
here are readable, not clinical.

## Running it

```bash
pip install -r requirements.txt
createdb pediatric                     # or CREATE DATABASE pediatric;

jupyter notebook notebooks/normalisation_to_warehouse.ipynb   # the walkthrough
python build_warehouse.py              # the same build, scripted
python build_warehouse.py --patients 200
```

Credentials come from the environment; see `.env.example` at the repository root:

| Variable | Default |
|---|---|
| `POSTGRES_HOST` | `localhost` |
| `POSTGRES_PORT` | `5432` |
| `POSTGRES_USER` | `postgres` |
| `POSTGRES_PASSWORD` | *(required)* |
| `PEDIATRIC_DB` | `pediatric` |

`build_warehouse.py` asserts its own output: one fact row per visit, a non-empty fact table,
zero orphaned lab rows, and no implausible BMI values. A schema regression fails the build
rather than producing a quietly wrong warehouse.

## Files

```
sql/01_normalised_schema.sql   DDL, with a DECISION note per normalisation step
sql/02_reference_data.sql      dimension seed data
sql/03_build_fact.sql          fact population + analysis views
build_warehouse.py             orchestrates schema -> ETL -> generate -> fact -> verify
notebooks/normalisation_to_warehouse.ipynb   the walkthrough: 1NF -> 3NF -> PostgreSQL
notebooks/etl_load_warehouse.ipynb           original coursework (credentials parameterised)
notebooks/db_connection.ipynb                original coursework
notebooks/growth_analysis.ipynb              original coursework
notebooks/exploration.ipynb                  original coursework
data/                          source spreadsheets (synthetic)
```

The original notebooks are kept as submitted. The SQL and build script are the rebuild, so
the difference between the two is visible rather than hidden.

## Notes

The original connected with a hardcoded password, which also appeared in several other
coursework notebooks. All credentials are now environment variables.

Group coursework for Data Warehousing, Semester 4. The ER design, ETL and dashboard work
were the original assignment; the normalisation, fact-table rebuild and data generation
here are additions.
