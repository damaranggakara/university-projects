-- ============================================================================
-- Pediatric data warehouse - normalised schema (1NF -> 3NF) + star-schema fact
--
-- The original coursework schema had five flat tables. This rebuild fixes the
-- defects it contained and documents which normal form each change satisfies.
-- Every DECISION note below corresponds to a concrete problem in the original.
-- ============================================================================

DROP TABLE IF EXISTS fact_checkup       CASCADE;
DROP TABLE IF EXISTS resep              CASCADE;
DROP TABLE IF EXISTS konsultasi         CASCADE;
DROP TABLE IF EXISTS hasil_lab          CASCADE;
DROP TABLE IF EXISTS pengkajian         CASCADE;
DROP TABLE IF EXISTS kunjungan          CASCADE;
DROP TABLE IF EXISTS pasien_orangtua    CASCADE;
DROP TABLE IF EXISTS pasien             CASCADE;
DROP TABLE IF EXISTS dim_diagnosis      CASCADE;
DROP TABLE IF EXISTS dim_obat           CASCADE;
DROP TABLE IF EXISTS dim_jenis_tes      CASCADE;
DROP TABLE IF EXISTS dim_dokter         CASCADE;
DROP TABLE IF EXISTS dim_wilayah        CASCADE;

-- ----------------------------------------------------------------------------
-- Reference dimensions
--
-- DECISION (3NF): the original stored `nama_dokter`, `jenis_tes`, `nama_obat`,
-- `diagnosis` and `treatment` as free text repeated on every transaction row.
-- Those attributes depend on the doctor / test / drug / diagnosis, not on the
-- transaction, which is a transitive dependency. Each becomes its own table.
-- ----------------------------------------------------------------------------

CREATE TABLE dim_wilayah (
    wilayah_id   serial PRIMARY KEY,
    kota         varchar(60)  NOT NULL,
    provinsi     varchar(60)  NOT NULL,
    UNIQUE (kota, provinsi)
);

CREATE TABLE dim_dokter (
    dokter_id    serial PRIMARY KEY,
    nama         varchar(80)  NOT NULL UNIQUE,
    spesialisasi varchar(60)  NOT NULL
);

CREATE TABLE dim_jenis_tes (
    jenis_tes_id serial PRIMARY KEY,
    nama         varchar(60)  NOT NULL UNIQUE,
    satuan       varchar(20),             -- unit of measure
    ref_bawah    numeric(8,2),            -- lower reference bound
    ref_atas     numeric(8,2)             -- upper reference bound
);

CREATE TABLE dim_obat (
    obat_id      serial PRIMARY KEY,
    nama         varchar(60)  NOT NULL UNIQUE,
    bentuk       varchar(30),             -- tablet, syrup, ...
    kekuatan     varchar(30)              -- e.g. 500 mg
);

CREATE TABLE dim_diagnosis (
    diagnosis_id serial PRIMARY KEY,
    kode_icd10   varchar(10),
    nama         varchar(80)  NOT NULL UNIQUE
);

-- ----------------------------------------------------------------------------
-- Patient
--
-- DECISION (1NF): `alamat` was a single free-text blob holding street, city and
-- province together. City and province are now a foreign key to dim_wilayah and
-- only the street line stays on the patient.
--
-- DECISION (derived data): the original stored `umur` (age) as an integer. Age
-- is not a fact about a person, it is a function of birth date and today, so it
-- silently goes stale. We store `tanggal_lahir` and derive age in views.
-- ----------------------------------------------------------------------------

CREATE TABLE pasien (
    pasien_id      uuid PRIMARY KEY,
    nama           varchar(80)  NOT NULL,
    tanggal_lahir  date         NOT NULL,
    kelamin        char(1)      NOT NULL CHECK (kelamin IN ('L','P')),
    alamat_jalan   varchar(120),
    wilayah_id     int          REFERENCES dim_wilayah(wilayah_id),
    no_tlp         varchar(20),
    CHECK (tanggal_lahir <= CURRENT_DATE)
);

-- DECISION (2NF): `tinggi_bapak` and `tinggi_ibu` sat on every checkup row in
-- the original. Parental height depends on the patient, not on the individual
-- checkup, so repeating it per visit is a partial-dependency violation. It is
-- now one row per patient.

CREATE TABLE pasien_orangtua (
    pasien_id     uuid PRIMARY KEY REFERENCES pasien(pasien_id) ON DELETE CASCADE,
    tinggi_bapak  numeric(5,1) CHECK (tinggi_bapak BETWEEN 120 AND 220),
    tinggi_ibu    numeric(5,1) CHECK (tinggi_ibu   BETWEEN 120 AND 220)
);

-- ----------------------------------------------------------------------------
-- Visit: the event grain
--
-- DECISION (referential integrity): in the original, `laboratorium`,
-- `konsultasi` and `farmasi` had NO pasien_id column at all - the CREATE TABLE
-- omitted it even though every source file supplies one. Lab results could not
-- be traced to a patient, and `fact_checkup` (which required five ids) could
-- never be populated; it sat permanently at 0 rows.
--
-- Introducing `kunjungan` (visit) fixes this properly. Every clinical record
-- hangs off a visit, and a visit belongs to exactly one patient, so the join
-- path is unambiguous.
-- ----------------------------------------------------------------------------

CREATE TABLE kunjungan (
    kunjungan_id  uuid PRIMARY KEY,
    pasien_id     uuid NOT NULL REFERENCES pasien(pasien_id) ON DELETE CASCADE,
    tanggal       date NOT NULL,
    UNIQUE (pasien_id, tanggal)
);

CREATE INDEX idx_kunjungan_pasien ON kunjungan(pasien_id);

-- DECISION (1NF): `tekanan` held blood pressure as the string '120/80', which
-- is two values in one field. Split into two integers so they can be compared,
-- averaged and range-checked.

CREATE TABLE pengkajian (
    pengkajian_id uuid PRIMARY KEY,
    kunjungan_id  uuid NOT NULL UNIQUE REFERENCES kunjungan(kunjungan_id) ON DELETE CASCADE,
    tinggi_cm     numeric(5,1) NOT NULL CHECK (tinggi_cm BETWEEN 30 AND 200),
    berat_kg      numeric(5,2) NOT NULL CHECK (berat_kg  BETWEEN 1 AND 150),
    sistolik      int          CHECK (sistolik  BETWEEN 50 AND 200),
    diastolik     int          CHECK (diastolik BETWEEN 30 AND 140),
    suhu_c        numeric(4,1) CHECK (suhu_c BETWEEN 33 AND 43),
    CHECK (sistolik IS NULL OR diastolik IS NULL OR sistolik > diastolik)
);

CREATE TABLE hasil_lab (
    lab_id        uuid PRIMARY KEY,
    kunjungan_id  uuid NOT NULL REFERENCES kunjungan(kunjungan_id) ON DELETE CASCADE,
    jenis_tes_id  int  NOT NULL REFERENCES dim_jenis_tes(jenis_tes_id),
    nilai         numeric(8,2) NOT NULL
);

CREATE INDEX idx_lab_kunjungan ON hasil_lab(kunjungan_id);

CREATE TABLE konsultasi (
    konsultasi_id uuid PRIMARY KEY,
    kunjungan_id  uuid NOT NULL REFERENCES kunjungan(kunjungan_id) ON DELETE CASCADE,
    dokter_id     int  NOT NULL REFERENCES dim_dokter(dokter_id),
    diagnosis_id  int  NOT NULL REFERENCES dim_diagnosis(diagnosis_id),
    catatan       text
);

CREATE INDEX idx_konsultasi_kunjungan ON konsultasi(kunjungan_id);

-- DECISION (1NF): `dosis` was '2x sehari' and `frekuensi` was '5 hari' - text
-- that has to be parsed before it can be used. Stored as integers instead.

CREATE TABLE resep (
    resep_id       uuid PRIMARY KEY,
    kunjungan_id   uuid NOT NULL REFERENCES kunjungan(kunjungan_id) ON DELETE CASCADE,
    obat_id        int  NOT NULL REFERENCES dim_obat(obat_id),
    dosis_per_hari int  NOT NULL CHECK (dosis_per_hari BETWEEN 1 AND 6),
    durasi_hari    int  NOT NULL CHECK (durasi_hari    BETWEEN 1 AND 30)
);

CREATE INDEX idx_resep_kunjungan ON resep(kunjungan_id);

-- ----------------------------------------------------------------------------
-- Fact table
--
-- DECISION (grain): the original fact_checkup had a five-column composite
-- primary key (pasien_id, pengkajian_id, laboratorium_id, konsultasi_id,
-- farmasi_id). Joining those together per patient is a classic fan trap: with
-- 21 records in each of four tables it would have produced 21^4 = 194,481 rows
-- for a single patient, every one of them double-counting the measures.
--
-- The grain here is ONE ROW PER VISIT. Lab and prescription counts are
-- aggregated to that grain, so additive measures stay additive.
-- ----------------------------------------------------------------------------

CREATE TABLE fact_checkup (
    kunjungan_id    uuid PRIMARY KEY REFERENCES kunjungan(kunjungan_id) ON DELETE CASCADE,
    pasien_id       uuid NOT NULL REFERENCES pasien(pasien_id),
    wilayah_id      int  REFERENCES dim_wilayah(wilayah_id),
    dokter_id       int  REFERENCES dim_dokter(dokter_id),
    diagnosis_id    int  REFERENCES dim_diagnosis(diagnosis_id),
    tanggal         date NOT NULL,
    umur_bulan      int  NOT NULL,            -- derived at load time
    tinggi_cm       numeric(5,1) NOT NULL,
    berat_kg        numeric(5,2) NOT NULL,
    bmi             numeric(5,2) NOT NULL,
    bmi_kategori    varchar(20)  NOT NULL,
    suhu_c          numeric(4,1),
    sistolik        int,
    diastolik       int,
    jumlah_lab      int NOT NULL DEFAULT 0,
    jumlah_resep    int NOT NULL DEFAULT 0,
    total_hari_obat int NOT NULL DEFAULT 0
);

CREATE INDEX idx_fact_pasien    ON fact_checkup(pasien_id);
CREATE INDEX idx_fact_tanggal   ON fact_checkup(tanggal);
CREATE INDEX idx_fact_diagnosis ON fact_checkup(diagnosis_id);
