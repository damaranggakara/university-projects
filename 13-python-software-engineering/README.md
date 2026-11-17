# Python Software Engineering

Four small systems built for Pemrograman Lanjut (Advanced Programming), Semester 3,
object-oriented design, modular packages, file-based persistence, and two different
generations of Python web programming. Less statistics than the rest of this portfolio and
more software construction.

## Components

### `finance-package/`: modular package design

A reusable `ekonomi` package split into `keuangan` (finance) and `pajak` (tax) modules,
consumed by `main.py`. Demonstrates package layout, imports and separation of concerns
rather than a single flat script.

```
Return on Investment (ROI): 20.0%
Pajak Hasil: 20000.0
```

### `library-system/`: OOP with file persistence

A library management system (`library.py`, 217 lines) with an analysis companion
(`ANALISIS.py`). Books and borrowings persist to pipe-delimited text files, read back on
start, a hand-rolled data layer with no database.

```
1|Harry Potter and the Sorcerer's Stone|J.K. Rowling|Fantasy|1997
2|The Lord of the Rings|J.R.R. Tolkien|Fantasy|1954
```

### `hotel-reservation/`: desktop GUI plus CGI web form

A room-booking system in two halves: a Tkinter desktop interface using `tkcalendar` for
date selection, and a CGI script (`proses_pencarian.py`) serving `pencarian.html` as a
search form. Reservations persist to CSV.

### `movie-rental-flask/`: Flask MVC application

A movie rental app with proper separation: `app.py` for routing, Jinja2 templates
inheriting from a `base.html`, and a `static/` stylesheet.

| Route | Methods | Purpose |
|---|---|---|
| `/` | GET | home |
| `/movies` | GET | catalogue |
| `/borrow` | GET, POST | borrow form and submission |

All three return 200.

## Running it

```bash
pip install -r requirements.txt
python smoke_test.py                  # verifies every component below

cd finance-package     && python main.py
cd movie-rental-flask  && flask run
```

`smoke_test.py` checks each component in turn:

```
  OK    finance package         Return on Investment (ROI): 20.0%
  OK    cgi module              cgi importable
  OK    hotel CGI handler       CGI handler executed
  OK    flask movie rental      routes 200: /, /movies, /borrow
  OK    library data file       10 books loaded
```

## Two things that broke with time

**`cgi` was removed from the standard library in Python 3.13** (PEP 594 scheduled it for
removal after a long deprecation). Both the library system and the hotel CGI handler import
it, so on a current interpreter they fail at import. Two ways round it, and
`requirements.txt` takes the second:

- run on Python 3.12 or earlier, where `cgi` is still present but deprecated
- install the `legacy-cgi` backport, which restores the module unchanged

CGI itself is long superseded; the Flask component in this same project is the modern
answer to the same problem, but the code is kept as written rather than rewritten, since
the point of the exercise was the older interface.

**`tkcalendar` is a third-party dependency**, not part of Tkinter, so the hotel GUI needs it
installed explicitly.

## Notes

Individual coursework. This project replaces an earlier plan to build a "regression from
scratch" project out of `Kelompok prolan/`: on inspection that folder contains four
classmates' individually-named submissions and none of my own work, so it is excluded from
this portfolio entirely.

Sample data contains my own name and one group member's first name as test entries; no
third-party personal data is present.
