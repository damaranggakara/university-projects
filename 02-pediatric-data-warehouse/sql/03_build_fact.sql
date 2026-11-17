-- ============================================================================
-- Populate fact_checkup at one-row-per-visit grain.
--
-- Lab results and prescriptions are many-per-visit, so they are aggregated in
-- subqueries BEFORE joining. Joining them directly would multiply the rows and
-- double-count tinggi/berat - the fan trap the original schema fell into.
-- ============================================================================

TRUNCATE fact_checkup;

INSERT INTO fact_checkup (
    kunjungan_id, pasien_id, wilayah_id, dokter_id, diagnosis_id, tanggal,
    umur_bulan, tinggi_cm, berat_kg, bmi, bmi_kategori,
    suhu_c, sistolik, diastolik, jumlah_lab, jumlah_resep, total_hari_obat
)
SELECT
    k.kunjungan_id,
    k.pasien_id,
    p.wilayah_id,
    ks.dokter_id,
    ks.diagnosis_id,
    k.tanggal,

    -- age in months at the time of the visit, derived rather than stored
    (EXTRACT(YEAR  FROM age(k.tanggal, p.tanggal_lahir)) * 12
   + EXTRACT(MONTH FROM age(k.tanggal, p.tanggal_lahir)))::int        AS umur_bulan,

    pg.tinggi_cm,
    pg.berat_kg,

    -- BMI = kg / m^2
    ROUND(pg.berat_kg / POWER(pg.tinggi_cm / 100.0, 2), 2)            AS bmi,

    -- Simplified BMI banding. Real paediatric practice uses BMI-for-age
    -- z-scores against WHO growth standards, which vary by age and sex; these
    -- fixed cut-offs are a readable approximation, not a clinical instrument.
    CASE
        WHEN pg.berat_kg / POWER(pg.tinggi_cm / 100.0, 2) < 14 THEN 'Gizi Kurang'
        WHEN pg.berat_kg / POWER(pg.tinggi_cm / 100.0, 2) < 18 THEN 'Normal'
        WHEN pg.berat_kg / POWER(pg.tinggi_cm / 100.0, 2) < 21 THEN 'Gizi Lebih'
        ELSE 'Obesitas'
    END                                                              AS bmi_kategori,

    pg.suhu_c,
    pg.sistolik,
    pg.diastolik,

    COALESCE(lab.n, 0)                                               AS jumlah_lab,
    COALESCE(rx.n, 0)                                                AS jumlah_resep,
    COALESCE(rx.hari, 0)                                             AS total_hari_obat

FROM kunjungan k
JOIN pasien      p  ON p.pasien_id    = k.pasien_id
JOIN pengkajian  pg ON pg.kunjungan_id = k.kunjungan_id

-- a visit has at most one consultation, so this join is safe
LEFT JOIN konsultasi ks ON ks.kunjungan_id = k.kunjungan_id

-- these two are many-per-visit: aggregate first
LEFT JOIN (
    SELECT kunjungan_id, COUNT(*) AS n
    FROM hasil_lab GROUP BY kunjungan_id
) lab ON lab.kunjungan_id = k.kunjungan_id

LEFT JOIN (
    SELECT kunjungan_id,
           COUNT(*)                        AS n,
           SUM(durasi_hari)                AS hari
    FROM resep GROUP BY kunjungan_id
) rx ON rx.kunjungan_id = k.kunjungan_id;


-- ----------------------------------------------------------------------------
-- Analysis views
-- ----------------------------------------------------------------------------

CREATE OR REPLACE VIEW v_nutrition_status AS
SELECT bmi_kategori,
       COUNT(*)                                     AS kunjungan,
       COUNT(DISTINCT pasien_id)                    AS pasien,
       ROUND(AVG(bmi), 2)                           AS bmi_rata2,
       ROUND(AVG(umur_bulan) / 12.0, 1)             AS umur_rata2_tahun
FROM fact_checkup
GROUP BY bmi_kategori
ORDER BY bmi_rata2;

CREATE OR REPLACE VIEW v_diagnosis_frequency AS
SELECT d.nama                                       AS diagnosis,
       d.kode_icd10,
       COUNT(*)                                     AS kunjungan,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS persen
FROM fact_checkup f
JOIN dim_diagnosis d ON d.diagnosis_id = f.diagnosis_id
GROUP BY d.nama, d.kode_icd10
ORDER BY kunjungan DESC;

CREATE OR REPLACE VIEW v_growth_by_region AS
SELECT w.kota,
       w.provinsi,
       COUNT(DISTINCT f.pasien_id)                  AS pasien,
       COUNT(*)                                     AS kunjungan,
       ROUND(AVG(f.tinggi_cm), 1)                   AS tinggi_rata2,
       ROUND(AVG(f.berat_kg), 2)                    AS berat_rata2,
       ROUND(AVG(f.bmi), 2)                         AS bmi_rata2
FROM fact_checkup f
JOIN dim_wilayah w ON w.wilayah_id = f.wilayah_id
GROUP BY w.kota, w.provinsi
ORDER BY pasien DESC;

-- Lab results outside their reference range: the kind of query the original
-- schema made impossible, because lab rows had no link to a patient.
CREATE OR REPLACE VIEW v_abnormal_labs AS
SELECT p.nama                                       AS pasien,
       t.nama                                       AS tes,
       l.nilai,
       t.satuan,
       t.ref_bawah,
       t.ref_atas,
       CASE WHEN l.nilai < t.ref_bawah THEN 'Rendah' ELSE 'Tinggi' END AS arah,
       k.tanggal
FROM hasil_lab l
JOIN dim_jenis_tes t ON t.jenis_tes_id = l.jenis_tes_id
JOIN kunjungan    k  ON k.kunjungan_id = l.kunjungan_id
JOIN pasien       p  ON p.pasien_id    = k.pasien_id
WHERE l.nilai < t.ref_bawah OR l.nilai > t.ref_atas
ORDER BY k.tanggal DESC;
