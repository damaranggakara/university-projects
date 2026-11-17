"""Fail if a credential or a machine-specific path has been committed.

Run by CI, and worth running before any push. All three of the things it looks
for have leaked from this repository before, so they are enforced rather than
remembered.

Notebooks are parsed structurally rather than scanned as raw text. That matters:
a base64-encoded matplotlib PNG happens to contain the sequence "AIza" followed
by base64 characters, which a naive scan reports as a Google API key. Only cell
sources and textual outputs are examined.

  python scan_secrets.py            # exit 1 on any finding
  python scan_secrets.py --verbose  # also list what was scanned
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent

PATTERNS = {
    "hardcoded password": re.compile(
        r"""(passwd|password)\s*=\s*\\?["'][^"'$<][^"']{2,}["']""", re.I),
    "google api key": re.compile(r"AIza[0-9A-Za-z_\-]{35}"),
    "aws access key": re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"),
    "openai key": re.compile(r"\bsk-(?!toggleable)[A-Za-z0-9]{32,}"),
    "windows home path": re.compile(r"[A-Za-z]:\\{1,2}Users\\{1,2}(?!<)[A-Za-z0-9_.-]+"),
    "db url with password": re.compile(
        r"(postgresql|mysql|mongodb)(\+\w+)?://[^:\s\"']+:(?!\$|\{)[^@\s\"']+@", re.I),
}

# substrings that mark a match as deliberate rather than a leak
ALLOW = (
    "ci_only_not_a_secret", "your_", "INSERT-YOUR", "REDACTED", "example",
    "<python>", "<home>", "<tmp>", "<repo>", "os.environ", "${",
)

TEXT_SUFFIXES = {".py", ".sql", ".md", ".yml", ".yaml", ".txt", ".cfg", ".ini"}

# this file necessarily contains the patterns it searches for
SELF = Path(__file__).name
# the CI workflow embeds the same patterns
SKIP_FILES = {SELF, "checks.yml"}


def notebook_text(path):
    """Cell sources and textual outputs only - never image or binary payloads."""
    try:
        nb = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return [(f"{path}: unreadable notebook: {e}", True)]
    chunks = []
    for cell in nb.get("cells", []):
        chunks.append("".join(cell.get("source", [])))
        for o in cell.get("outputs", []):
            if o.get("output_type") == "stream":
                chunks.append("".join(o.get("text", [])))
            else:
                data = o.get("data", {})
                for mime, payload in data.items():
                    if mime.startswith(("image/", "application/")):
                        continue            # base64 blobs produce false positives
                    chunks.append("".join(payload) if isinstance(payload, list) else str(payload))
            if o.get("output_type") == "error":
                chunks.extend(o.get("traceback", []))
    return [("\n".join(chunks), False)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    findings, scanned = [], 0
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or ".git" in f.parts:
            continue
        if f.name in SKIP_FILES:
            continue
        if f.suffix.lower() == ".ipynb":
            blobs = notebook_text(f)
        elif f.suffix.lower() in TEXT_SUFFIXES:
            blobs = [(f.read_text(encoding="utf-8", errors="replace"), False)]
        else:
            continue
        scanned += 1
        for text, is_error in blobs:
            if is_error:
                findings.append(text)
                continue
            for name, pat in PATTERNS.items():
                for m in pat.finditer(text):
                    s = m.group(0)
                    if any(a in s for a in ALLOW):
                        continue
                    rel = f.relative_to(ROOT)
                    findings.append(f"{rel}: {name}: {s[:60]}")
        if args.verbose:
            print(f"  scanned {f.relative_to(ROOT)}")

    for hit in findings:
        print(f"LEAK  {hit}")
    print(f"\nscanned {scanned} files, {len(findings)} finding(s)")
    if findings:
        print("\nIf a finding is deliberate, add a marker from ALLOW to it rather than")
        print("loosening the pattern.")
        return 1
    print("OK: no credentials or machine-specific paths committed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
