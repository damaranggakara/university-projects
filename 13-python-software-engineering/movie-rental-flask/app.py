#Imports
from flask import Flask, render_template, request, redirect, url_for
import csv
import os
app = Flask(__name__)

#Movies
movies = [
    {"title": "Inception", "genre": "Sci-Fi", "year": 2010},
    {"title": "The Dark Knight", "genre": "Action", "year": 2008},
    {"title": "Interstellar", "genre": "Sci-Fi", "year": 2014},
    {"title": "Parasite", "genre": "Thriller", "year": 2019},
    {"title": "Avengers: Endgame", "genre": "Action", "year": 2019},
    {"title": "The Godfather", "genre": "Crime", "year": 1972},
    {"title": "The Shawshank Redemption", "genre": "Drama", "year": 1994},
    {"title": "Spider-Man: Into the Spider-Verse", "genre": "Animation", "year": 2018},
    {"title": "Pulp Fiction", "genre": "Crime", "year": 1994},
    {"title": "The Matrix", "genre": "Sci-Fi", "year": 1999}
]
borrowed_movies = []

#Routes home
@app.route('/')
def home():
    return render_template('home.html')

#Route film yang tersedia
@app.route('/movies')
def list_movies():
    return render_template('movies.html', movies=movies)

#Route peminjaman film
from pathlib import Path
# Resolved relative to this file so the app runs from any checkout.
csv_file_path = Path(__file__).parent / 'borrowed_movies.csv'
@app.route('/borrow', methods=['GET', 'POST'])
def borrow_movie():
    if request.method == 'POST':
        name = request.form['name']
        movie_title = request.form['movie_title']
        borrow_date = request.form['borrow_date']

        borrowed_movie = {
            "name": name,
            "movie_title": movie_title,
            "borrow_date": borrow_date
        }

        #Simpan dalam csv
        file_exists = os.path.isfile(csv_file_path)
        with open(csv_file_path, mode='a', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=["name", "movie_title", "borrow_date"])

            if not file_exists:
                writer.writeheader()

            writer.writerow(borrowed_movie)

        borrowed_movies.append(borrowed_movie)

        return redirect(url_for('home'))

    return render_template('borrow.html', movies=movies)

#Menjalankan aplikasi
if __name__ == '__main__':
    app.run(debug=True)
