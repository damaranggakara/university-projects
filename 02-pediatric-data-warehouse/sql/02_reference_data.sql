-- ============================================================================
-- Reference / dimension data
--
-- Values are taken from the original coursework files where they existed
-- (jenis_tes, nama_obat, diagnosis, Dr. Andi) and extended so the dimensions
-- are wide enough for the generated visits to be varied.
-- ============================================================================

INSERT INTO dim_wilayah (kota, provinsi) VALUES
    ('Malang',        'Jawa Timur'),
    ('Surabaya',      'Jawa Timur'),
    ('Sidoarjo',      'Jawa Timur'),
    ('Kediri',        'Jawa Timur'),
    ('Jakarta Pusat', 'DKI Jakarta'),
    ('Bandung',       'Jawa Barat'),
    ('Semarang',      'Jawa Tengah'),
    ('Denpasar',      'Bali');

INSERT INTO dim_dokter (nama, spesialisasi) VALUES
    ('Dr. Andi',    'Anak'),                  -- the only doctor in the source data
    ('Dr. Sari',    'Anak'),
    ('Dr. Budi',    'Anak'),
    ('Dr. Maya',    'Gizi Klinik'),
    ('Dr. Hendra',  'Anak');

-- Reference ranges are typical paediatric values, kept deliberately simple.
INSERT INTO dim_jenis_tes (nama, satuan, ref_bawah, ref_atas) VALUES
    ('Hemoglobin',    'g/dL',   11.5, 15.5),
    ('Gula Darah',    'mg/dL',  70.0, 140.0),
    ('Kolesterol',    'mg/dL',  0.0,  170.0),
    ('Darah Lengkap', '10^3/uL', 4.5, 13.5);

INSERT INTO dim_obat (nama, bentuk, kekuatan) VALUES
    ('Paracetamol', 'Sirup',   '120 mg/5 mL'),
    ('Amoxicillin', 'Sirup',   '250 mg/5 mL'),
    ('Cetirizine',  'Tablet',  '10 mg'),
    ('Ibuprofen',   'Sirup',   '100 mg/5 mL'),
    ('Vitamin C',   'Tablet',  '500 mg');

INSERT INTO dim_diagnosis (kode_icd10, nama) VALUES
    ('Z00.1', 'Sehat'),
    ('J00',   'Flu'),
    ('R05',   'Batuk'),
    ('R50.9', 'Demam'),
    ('T78.4', 'Alergi'),
    ('E44.0', 'Gizi Kurang');
