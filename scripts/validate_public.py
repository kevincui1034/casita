"""Public-release validation checks for Casita.

This is intentionally lightweight: it catches private operational strings and
fixture leaks without turning the interview repo into a fully tested project.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = [
    ROOT / "fixtures" / "demo.sqlite",
    ROOT / "src" / "casita" / "fixtures" / "demo.sqlite",
]

PRIVATE_PATTERNS = {
    "selected home": re.compile(r"Blithedale", re.IGNORECASE),
    "dog names": re.compile(r"Limoncello|Pancetta", re.IGNORECASE),
    "private infra": re.compile(r"casita-mb|openclaw-mb-state", re.IGNORECASE),
    "api key": re.compile(r"AIza[0-9A-Za-z_-]+"),
    "private email": re.compile(r"(matin@|mtamizi@|@imperfect\.)", re.IGNORECASE),
    "phone number": re.compile(
        r"(?<![\d.-])(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]\d{3}[\s.-]\d{4}(?![\d.-])"
    ),
    "private prompt detail": re.compile(r"Creative Director|MX plates", re.IGNORECASE),
}

PERSONAL_NAME_PATTERN = re.compile(r"\b(Matin|Bibiana|matin|bibiana)\b")

PUBLIC_PROJECT_REFERENCES = (
    "https://github.com/matin/casita",
    "https://matin.github.io/casita/",
    "https://matin.github.io/casita",
    "matin/casita",
)

TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".example",
    ".envrc",
    ".gitignore",
    ".gitattributes",
    ".yml",
    ".yaml",
    ".json",
    ".ts",
    ".tsx",
    ".mjs",
    ".css",
}

# Machine-generated files where the private-string regexes only produce noise.
SKIPPED_FILENAMES = {"package-lock.json"}

def _is_text_path(path: Path) -> bool:
    if path.name in SKIPPED_FILENAMES:
        return False
    return path.name in {"Makefile", "LICENSE"} or path.suffix in TEXT_SUFFIXES


def _iter_project_text() -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    ignored_dirs = {".git", ".venv", ".cache", "site", "tmp",
                    "node_modules", ".next", "out"}
    for path in ROOT.rglob("*"):
        if path == Path(__file__).resolve():
            continue
        if any(part in ignored_dirs for part in path.relative_to(ROOT).parts):
            continue
        if not path.is_file() or not _is_text_path(path):
            continue
        out.append((path, path.read_text(encoding="utf-8")))
    return out


def _fixture_text(fixture: Path) -> str:
    if not fixture.exists():
        raise SystemExit(f"Missing fixture: {fixture}")
    chunks: list[str] = []
    with sqlite3.connect(fixture) as conn:
        conn.row_factory = sqlite3.Row
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            if not row["name"].startswith("sqlite_")
        ]
        for table in tables:
            columns = [
                row["name"]
                for row in conn.execute(f"PRAGMA table_info({table})")
                if row["type"].upper() in {"TEXT", "TIMESTAMP"} or not row["type"]
            ]
            if not columns:
                continue
            quoted = ", ".join(f'"{col}"' for col in columns)
            for row in conn.execute(f'SELECT {quoted} FROM "{table}"'):
                chunks.extend(str(value) for value in row if value is not None)
    return "\n".join(chunks)


def _without_public_project_references(text: str) -> str:
    for value in PUBLIC_PROJECT_REFERENCES:
        text = text.replace(value, "")
    return text


# ---------------------------------------------------------------------------
# Web-export checks — web/public/data is a second egress path to a PUBLIC
# site, so it gets a structural allowlist check on top of the string scans.

EXPORT_DIR = ROOT / "web" / "public" / "data"

# Mirrors the record built in src/casita/export.py. A new field must be added
# in BOTH places — that friction is the point.
EXPORT_ALLOWED_KEYS = frozenset({
    # listing record
    "key", "source", "url", "title", "address", "hood", "price", "beds",
    "baths", "sqft", "dog_policy", "parking", "laundry", "has_yard",
    "yard_note", "lat", "lng", "is_marin", "severity", "rank", "score",
    "blurb", "quality", "photos", "first_seen", "walk", "livability",
    # nested: quality
    "light", "view", "condition",
    # nested: walk
    "mode", "trail", "beach", "bakery", "sf", "name", "min",
    # nested: livability
    "verdict", "points", "cats", "nearest_m", "n800",
    # livability categories
    "supermarket", "grocery", "convenience", "cafe", "restaurant", "park",
    "dog_park", "transit", "pharmacy", "school",
})

EXPORT_FORBIDDEN_KEYS = frozenset({
    "contact_name", "contact_phone", "contact_email", "contact_url",
    "contact_note", "description", "raw_json", "share_token",
    "address_verified", "status", "voter", "direction", "reason", "body",
    "sender", "extracted_json",
})


def _collect_keys(obj, into: set[str]) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            into.add(k)
            _collect_keys(v, into)
    elif isinstance(obj, list):
        for v in obj:
            _collect_keys(v, into)


def check_export_dir(failures: list[str]) -> None:
    listings_path = EXPORT_DIR / "listings.json"
    if not listings_path.exists():
        return  # nothing exported yet — nothing to leak
    import json

    records = json.loads(listings_path.read_text(encoding="utf-8"))
    keys: set[str] = set()
    _collect_keys(records, keys)

    forbidden = keys & EXPORT_FORBIDDEN_KEYS
    if forbidden:
        failures.append(
            f"web export: forbidden keys in listings.json: {sorted(forbidden)}"
        )
    unknown = keys - EXPORT_ALLOWED_KEYS
    if unknown:
        failures.append(
            f"web export: keys not in EXPORT_ALLOWED_KEYS: {sorted(unknown)} "
            "(add to the allowlist in BOTH export.py and validate_public.py "
            "only after confirming they are safe to publish)"
        )
    for rec in records:
        for url in [rec.get("url"), *(rec.get("photos") or [])]:
            if url and not str(url).startswith("http"):
                failures.append(
                    f"web export: non-http URL in {rec.get('key')}: {url!r} "
                    "(local photo mirrors must never be published)"
                )


def main() -> None:
    failures: list[str] = []
    check_export_dir(failures)
    for path, text in _iter_project_text():
        text = _without_public_project_references(text)
        patterns = PRIVATE_PATTERNS.copy()
        patterns["personal names"] = PERSONAL_NAME_PATTERN
        for label, pattern in patterns.items():
            if pattern.search(text):
                rel = path.relative_to(ROOT)
                failures.append(f"{rel}: matched {label}")

    for fixture in FIXTURES:
        fixture_text = _without_public_project_references(_fixture_text(fixture))
        for label, pattern in {**PRIVATE_PATTERNS, "personal names": PERSONAL_NAME_PATTERN}.items():
            if pattern.search(fixture_text):
                failures.append(f"{fixture.relative_to(ROOT)}: matched {label}")

    if failures:
        raise SystemExit("Public validation failed:\n- " + "\n- ".join(failures))
    print("public validation passed")


if __name__ == "__main__":
    main()
