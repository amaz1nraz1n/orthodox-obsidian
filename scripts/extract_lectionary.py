"""
Lectionary extractor — OCMC orthodox-christian-lectionary → Obsidian notes.

Reads source_files/Lectionary/lectionary.csv (EPL-2.0) and generates:
  output/Lectionary/Menaion/{month_name}/{key}.md   — fixed calendar readings
  output/Lectionary/Movable/{key}.md                — paschal cycle readings
  output/Lectionary/lectionary.json                 — machine-readable lookup

Usage:
    python3 extract_lectionary.py
    python3 extract_lectionary.py --output-root=DIR
"""

import csv
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

CSV_PATH = Path("source_files/Lectionary/lectionary.csv")

# ── Book name mapping ─────────────────────────────────────────────────────────
# OCMC uses "1 Corinthians" style; vault uses "I Corinthians" style.

OCMC_BOOK_TO_CANON: dict[str, str] = {
    "Acts": "Acts",
    "Colossians": "Colossians",
    "Ephesians": "Ephesians",
    "Galatians": "Galatians",
    "Hebrews": "Hebrews",
    "James": "James",
    "John": "John",
    "Jude": "Jude",
    "Luke": "Luke",
    "Mark": "Mark",
    "Matthew": "Matthew",
    "Philemon": "Philemon",
    "Philippians": "Philippians",
    "Romans": "Romans",
    "Titus": "Titus",
    "1 Corinthians": "I Corinthians",
    "2 Corinthians": "II Corinthians",
    "1 John": "I John",
    "2 John": "II John",
    "3 John": "III John",
    "1 Peter": "I Peter",
    "2 Peter": "II Peter",
    "1 Thessalonians": "I Thessalonians",
    "2 Thessalonians": "II Thessalonians",
    "1 Timothy": "I Timothy",
    "2 Timothy": "II Timothy",
}

_MONTH_NAMES = {
    "m01": "January", "m02": "February", "m03": "March",
    "m04": "April",   "m05": "May",      "m06": "June",
    "m07": "July",    "m08": "August",   "m09": "September",
    "m10": "October", "m11": "November", "m12": "December",
}

_READING_TYPE = {"ep": "Epistle", "go": "Gospel"}


# ── Pericope wikilink generation ──────────────────────────────────────────────

def pericope_to_wikilinks(blocks: list[dict]) -> tuple[str, str]:
    """Convert a list of verse-range blocks to (visible_link, hidden_links).

    Each block: {"book": str, "chapter": int, "verse_from": int, "verse_to": int}

    Visible link: anchored at first verse of first block, display shows full range.
    Hidden links: intermediate verses (for Obsidian backlink completeness),
                  wrapped in %% comment markers — caller wraps the whole set.
    """
    if not blocks:
        return "", ""

    first = blocks[0]
    last = blocks[-1]
    book_first = first["book"]
    ch_first = first["chapter"]
    vf_first = first["verse_from"]
    ch_last = last["chapter"]
    vt_last = last["verse_to"]

    # Build visible display text
    if len(blocks) == 1 and vf_first == vt_last:
        visible = f"[[{book_first} {ch_first}#v{vf_first}|{ch_first}:{vf_first}]]"
    elif len(blocks) == 1:
        visible = f"[[{book_first} {ch_first}#v{vf_first}|{ch_first}:{vf_first}-{vt_last}]]"
    else:
        book_last = last["book"]
        if book_first == book_last:
            start_link = f"[[{book_first} {ch_first}#v{vf_first}|{ch_first}:{vf_first}]]"
            end_link = f"[[{book_last} {ch_last}#v{vt_last}|{ch_last}:{vt_last}]]"
        else:
            # Cross-book: include abbreviated book name in display
            start_link = f"[[{book_first} {ch_first}#v{vf_first}|{book_first} {ch_first}:{vf_first}]]"
            end_link = f"[[{book_last} {ch_last}#v{vt_last}|{book_last} {ch_last}:{vt_last}]]"
        visible = f"{start_link}–{end_link}"

    # Build hidden range links for intermediate verses
    hidden_parts: list[str] = []
    for block in blocks:
        book = block["book"]
        ch = block["chapter"]
        vf = block["verse_from"]
        vt = block["verse_to"]
        # Skip the very first verse (already in visible link)
        start = vf + 1 if (block is blocks[0]) else vf
        for v in range(start, vt + 1):
            hidden_parts.append(f"[[{book} {ch}#v{v}]]")

    hidden = "".join(hidden_parts)
    return visible, hidden


# ── CSV parsing ───────────────────────────────────────────────────────────────

def _parse_blocks(row: dict) -> list[dict]:
    """Extract up to 6 verse-range blocks from a CSV row."""
    blocks = []
    for n in range(1, 7):
        raw_book = row.get(f"bk{n}", "").strip()
        if not raw_book:
            break
        canon = OCMC_BOOK_TO_CANON.get(raw_book)
        if not canon:
            logging.warning("Unknown book %r in row %s", raw_book, row.get("topic~key", "?"))
            continue
        try:
            chapter = int(row[f"c{n}"])
            vf = int(row[f"vf{n}"])
            vt = int(row[f"vt{n}"])
        except (KeyError, ValueError):
            continue
        blocks.append({"book": canon, "chapter": chapter, "verse_from": vf, "verse_to": vt})
    return blocks


def _parse_key(key: str) -> dict:
    """Parse an OCMC AGES key into structured metadata."""
    parts = key.split(".")
    # le.{type}.{cycle}.{date_parts...}
    reading_type = _READING_TYPE.get(parts[1], parts[1]) if len(parts) > 1 else ""
    cycle = parts[2] if len(parts) > 2 else ""
    date_parts = parts[3:] if len(parts) > 3 else []
    return {"reading_type": reading_type, "cycle": cycle, "date_parts": date_parts}


def load_lectionary(csv_path: Path = CSV_PATH) -> list[dict]:
    """Parse lectionary CSV into a list of reading records."""
    records = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            full_key = row["topic~key"]
            key = full_key.split("~")[0]
            meta = _parse_key(key)
            blocks = _parse_blocks(row)
            if not blocks:
                continue
            visible, hidden = pericope_to_wikilinks(blocks)
            records.append({
                "key": key,
                "cycle": meta["cycle"],
                "reading_type": meta["reading_type"],
                "date_parts": meta["date_parts"],
                "citation": row.get("Citation", "").strip(),
                "blocks": blocks,
                "wikilink": visible,
                "hidden_links": hidden,
            })
    return records


# ── Note rendering ────────────────────────────────────────────────────────────

def _render_note(records_for_day: list[dict], key: str) -> str:
    """Render a liturgical day note with pericope wikilinks."""
    lines = ["---", f'lectionary_key: "{key}"', "---", ""]
    for r in records_for_day:
        link = r["wikilink"]
        hidden = r["hidden_links"]
        reading_label = r["reading_type"]
        citation = r["citation"]
        hidden_block = f"\n%%{hidden}%%" if hidden else ""
        lines.append(f"**{reading_label}:** {link} _{citation}_{hidden_block}")
        lines.append("")
    return "\n".join(lines)


def _month_day_from_parts(date_parts: list[str]) -> tuple[str, str]:
    """Return (month_folder, day_key) for menaion records."""
    if not date_parts:
        return "Unknown", "unknown"
    month_code = date_parts[0] if date_parts[0].startswith("m") else "m00"
    day_part = date_parts[1] if len(date_parts) > 1 else date_parts[0]
    month_name = _MONTH_NAMES.get(month_code, month_code)
    return month_name, day_part


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    output_root_flag = next(
        (a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--output-root=")),
        None,
    )
    output_root = Path(output_root_flag) if output_root_flag else Path("output/Lectionary")

    if not CSV_PATH.exists():
        logging.error("Lectionary CSV not found: %s", CSV_PATH)
        sys.exit(1)

    records = load_lectionary()
    logging.info("Loaded %d lectionary reading records", len(records))

    # Group by key (one note per liturgical slot key)
    by_key: dict[str, list[dict]] = {}
    for r in records:
        by_key.setdefault(r["key"], []).append(r)

    menaion_count = movable_count = other_count = 0

    for key, day_records in sorted(by_key.items()):
        cycle = day_records[0]["cycle"]
        date_parts = day_records[0]["date_parts"]

        if cycle == "me":
            month_name, day_key = _month_day_from_parts(date_parts)
            note_path = output_root / "Menaion" / month_name / f"{key}.md"
            menaion_count += 1
        elif cycle == "mc":
            note_path = output_root / "Movable" / f"{key}.md"
            movable_count += 1
        else:
            note_path = output_root / "Other" / f"{key}.md"
            other_count += 1

        note_path.parent.mkdir(parents=True, exist_ok=True)
        note_path.write_text(_render_note(day_records, key), encoding="utf-8")

    logging.info(
        "Written: %d menaion, %d movable, %d other notes → %s/",
        menaion_count, movable_count, other_count, output_root,
    )

    # Write machine-readable JSON lookup
    json_path = output_root / "lectionary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(by_key, f, ensure_ascii=False, indent=2)
    logging.info("Written: %s", json_path)


if __name__ == "__main__":
    main()
