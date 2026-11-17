"""Check that each component still loads and runs on the current interpreter.

These are small programs with no test suite of their own; this verifies the parts that
break silently when the environment moves underneath them.

Run:  python smoke_test.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
failures = []


def check(name, fn):
    try:
        detail = fn()
        print(f"  OK    {name:<32} {detail or ''}")
    except Exception as e:
        print(f"  FAIL  {name:<32} {type(e).__name__}: {e}")
        failures.append(name)


def finance():
    r = subprocess.run([sys.executable, "main.py"], cwd=ROOT / "finance-package",
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr.strip()[:200]
    assert "ROI" in r.stdout, "expected ROI in output"
    return r.stdout.strip().splitlines()[0]


def cgi_available():
    import cgi  # noqa: F401  (stdlib <=3.12, else the legacy-cgi backport)
    return "cgi importable"


def hotel_cgi():
    r = subprocess.run([sys.executable, "proses_pencarian.py"], cwd=ROOT / "hotel-reservation",
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr.strip()[:200]
    return "CGI handler executed"


def flask_app():
    """Run in its own process from the app directory: Flask resolves templates
    relative to the app module, so cwd matters."""
    # GET status alone is not enough: the borrow log path was once an absolute
    # path to a folder that no longer exists, and every GET still returned 200
    # because only the POST branch writes. So this exercises the write too.
    code = (
        "import app, json;"
        "c = app.app.test_client();"
        "out = {p: c.get(p).status_code for p in ('/', '/movies', '/borrow')};"
        "r = c.post('/borrow', data={'name': 'smoke test',"
        " 'movie_title': 'Inception', 'borrow_date': '2026-01-01'},"
        " follow_redirects=True);"
        "out['POST /borrow'] = r.status_code;"
        "out['_movies_listed'] = 'Inception' in c.get('/movies').get_data(as_text=True);"
        "print(json.dumps(out))"
    )
    # The POST appends to a committed demo file, so snapshot and restore it:
    # running the tests should not leave the repository dirty.
    log = ROOT / "movie-rental-flask" / "borrowed_movies.csv"
    before = log.read_text(encoding="utf-8", errors="replace") if log.exists() else None
    try:
        r = subprocess.run([sys.executable, "-c", code], cwd=ROOT / "movie-rental-flask",
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, r.stderr.strip().splitlines()[-1][:200]
        import json
        out = json.loads(r.stdout.strip().splitlines()[-1])
        listed = out.pop("_movies_listed")
        assert all(c == 200 for c in out.values()), out
        assert listed, "/movies rendered but did not contain the catalogue"
        assert log.exists(), "POST /borrow succeeded but wrote no log file"
        assert "smoke test" in log.read_text(encoding="utf-8", errors="replace"), \
            "borrow log does not contain the submitted record"
    finally:
        if before is not None:
            log.write_text(before, encoding="utf-8")
    return f"{len(out)} routes 200, catalogue rendered, borrow write verified"


def library_data():
    books = (ROOT / "library-system" / "books.txt").read_text(encoding="utf-8").strip().splitlines()
    assert books and all("|" in b for b in books), "books.txt is not pipe-delimited"
    return f"{len(books)} books loaded"


print("component checks\n")
check("finance package", finance)
check("cgi module", cgi_available)
check("hotel CGI handler", hotel_cgi)
check("flask movie rental", flask_app)
check("library data file", library_data)

print()
if failures:
    print(f"FAILED: {', '.join(failures)}")
    sys.exit(1)
print("OK: all components load and run.")
