#!/usr/bin/env python3
#imports
import cgi
import cgitb
import os
cgitb.enable()

#Struktur file
books_file = "books.txt"
borrowings_file = "borrowings.txt"

#Buku terdaftar
def read_books():
    with open(books_file, "r") as file:
        books = []
        for line in file:
            data = line.strip().split('|')
            if len(data) == 5:
                books.append({
                    'id': data[0],
                    'title': data[1],
                    'author': data[2],
                    'genre': data[3],
                    'year': data[4]
                })
        return books

#Peminjaman buku
def read_borrowings():
    if os.path.exists(borrowings_file):
        with open(borrowings_file, "r") as file:
            return [line.strip().split("|") for line in file.readlines()]
    return []

#Masukin data kedalam file txt
def write_borrowing(name, book_id, book_title):
    with open(borrowings_file, "a") as file:
        file.write(f"{name}|{book_id}|{book_title}\n")

#Reset data peminjaman
def reset_borrowings():
    if os.path.exists(borrowings_file):
        os.remove(borrowings_file)

#CGI halaman utama
def main():
    form = cgi.FieldStorage()

    #HTML headers
    print("Content-type: text/html\n")

    #Aksi URL
    action = form.getvalue("action", "")

    #Sytyle header
    print("""
    <html>
    <head>
    <title>Perpustakaan Online</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f4f4f4;
        }
        .container {
            width: 80%;
            margin: 0 auto;
            padding: 20px;
        }
        h1 {
            text-align: center;
            color: #333;
        }
        a {
            text-decoration: none;
            color: white;
            background-color: #007BFF;
            padding: 10px 20px;
            border-radius: 5px;
            margin: 10px 0;
            display: inline-block;
        }
        a:hover {
            background-color: #0056b3;
        }
        .btn-container {
            text-align: center;
            margin: 20px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        table, th, td {
            border: 1px solid #ddd;
        }
        th, td {
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #007BFF;
            color: white;
        }
        tr:hover {
            background-color: #f1f1f1;
        }
        .center-btn {
            display: flex;
            justify-content: center;
            margin-top: 20px;
        }
        .center-text {
            text-align: center;
            font-size: 1.2em;
            color: #333;
        }
    </style>
    </head>
    <body>
    <div class="container">
    """)

    #Halaman utama
    if action == "":
        print("""
        <h1>Selamat Datang di Perpustakaan Online</h1>
        <div class='btn-container'>
            <a href='?action=list_books'>Lihat Daftar Buku</a>
            <a href='?action=borrow'>Pinjam Buku</a>
            <a href='?action=show_borrowings'>Lihat Data Peminjaman</a>
            <a href='?action=reset_borrowings'>Reset Data Peminjaman</a>
        </div>
        <p class="center-text">Akses perpustakaan kapan saja, di mana saja. Klik tombol di atas untuk melihat katalog buku, meminjam buku, atau melihat data peminjaman.</p>
        """)

    #Penampilan buku yang tersedia dalam tabel
    elif action == "list_books":
        books = read_books()
        print("<h1>Daftar Buku Tersedia</h1>")
        print("<table>")
        print("<tr><th>ID</th><th>Judul Buku</th><th>Penulis</th><th>Genre</th><th>Tahun</th></tr>")
        for book in books:
            print(f"<tr><td>{book['id']}</td><td>{book['title']}</td><td>{book['author']}</td><td>{book['genre']}</td><td>{book['year']}</td></tr>")
        print("</table>")
        print("<div class='btn-container'><a href='?'>Kembali ke Halaman Utama</a></div>")

    #Formulir peminjaman dan tabel
    elif action == "borrow":
        books = read_books()
        print("<h1>Formulir Peminjaman Buku</h1>")
        print("<form method='get' action='library.py'>")
        print("<input type='hidden' name='action' value='submit_borrowing'>")
        print("Nama Peminjam: <input type='text' name='name' required><br><br>")

        print("<h2>Pilih Buku untuk Dipinjam</h2>")
        print("<table>")
        print("<tr><th>Pilih</th><th>ID</th><th>Judul Buku</th><th>Penulis</th><th>Genre</th><th>Tahun</th></tr>")
        for book in books:
            print(f"<tr><td><input type='radio' name='book_id' value='{book['id']}' required></td>")
            print(f"<td>{book['id']}</td><td>{book['title']}</td><td>{book['author']}</td><td>{book['genre']}</td><td>{book['year']}</td></tr>")
        print("</table>")
        
        #Tmobol peminjaman
        print("<div class='center-btn'><input type='submit' value='Pinjam Buku'></div>")
        print("</form>")
        print("<div class='btn-container'><a href='?'>Kembali ke Halaman Utama</a></div>")

    #Menyimpan data peminjaman
    elif action == "submit_borrowing":
        name = form.getvalue("name")
        book_id = form.getvalue("book_id")
        books = read_books()

        #Ngambil buku berdasarkan nama
        book_title = next((book['title'] for book in books if book['id'] == book_id), None)
        if name and book_title:
            write_borrowing(name, book_id, book_title)
            print("<div class='center-text'>")
            print("<h1>Peminjaman Berhasil</h1>")
            print(f"<p>{name} meminjam buku <strong>'{book_title}'</strong></p>")
            print("</div>")
        else:
            print("<h1>Error: Harap mengisi semua kolom dengan benar.</h1>")
        print("<div class='btn-container'><a href='?'>Kembali ke Halaman Utama</a></div>")

    #Penampilan buku yang dipinjam
    elif action == "show_borrowings":
        borrowings = read_borrowings()
        print("<h1>Data Peminjaman</h1>")
        if borrowings:
            print("<table>")
            print("<tr><th>Nama Peminjam</th><th>ID Buku</th><th>Judul Buku</th></tr>")
            for borrowing in borrowings:
                print(f"<tr><td>{borrowing[0]}</td><td>{borrowing[1]}</td><td>{borrowing[2]}</td></tr>")
            print("</table>")
        else:
            print("<p class='center-text'>Belum ada data peminjaman.</p>")
        print("<div class='btn-container'><a href='?'>Kembali ke Halaman Utama</a></div>")

    #Reset data peminjaman
    elif action == "reset_borrowings":
        reset_borrowings()
        print("<div class='center-text'>")
        print("<h1>Data Peminjaman Telah Direset</h1>")
        print("<p>Semua data peminjaman telah dihapus.</p>")
        print("</div>")
        print("<div class='btn-container'><a href='?'>Kembali ke Halaman Utama</a></div>")

    #HTML footer
    print("</div></body></html>")

#Run fungsi
if __name__ == "__main__":
    main()