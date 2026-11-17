#!/usr/bin/env python3

import cgi

# Kamus berisi data mahasiswa
data_mahasiswa = {
    "210001": {"nama": "Ayu", "jurusan": "Informatika", "angkatan": 2021},
    "210002": {"nama": "Budi", "jurusan": "Sistem Informasi", "angkatan": 2020},
    "210003": {"nama": "Citra", "jurusan": "Teknik Komputer", "angkatan": 2021},
}

# Mengambil data dari form
form = cgi.FieldStorage()
nim = form.getvalue('nim')

# Header untuk halaman HTML
print("Content-type: text/html\n")
print("<html><head><title>Hasil Pencarian</title></head><body>")
print("<h1>Hasil Pencarian</h1>")

# Proses pencarian NIM
if nim in data_mahasiswa:
    mahasiswa = data_mahasiswa[nim]
    print(f"<p>Nama: {mahasiswa['nama']}</p>")
    print(f"<p>Jurusan: {mahasiswa['jurusan']}</p>")
    print(f"<p>Angkatan: {mahasiswa['angkatan']}</p>")
else:
    print("<p>Data mahasiswa tidak ditemukan.</p>")

print("</body></html>")