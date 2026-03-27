"""One-off script: inject testament/genre into existing vault hub file frontmatter."""
import os
import re

VAULT = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-jmtharp90@gmail.com/My Drive/Jasper/Jasper"
)
SCRIPTURE_ROOT = os.path.join(VAULT, "Holy Tradition", "Holy Scripture")

BOOK_TESTAMENT = {
    "Genesis": "OT", "Exodus": "OT", "Leviticus": "OT", "Numbers": "OT", "Deuteronomy": "OT",
    "Joshua": "OT", "Judges": "OT", "Ruth": "OT", "1 Kingdoms": "OT", "2 Kingdoms": "OT",
    "3 Kingdoms": "OT", "4 Kingdoms": "OT", "1 Chronicles": "OT", "2 Chronicles": "OT",
    "Ezra": "OT", "Nehemiah": "OT", "Esther": "OT", "Job": "OT", "Psalms": "OT",
    "Proverbs": "OT", "Ecclesiastes": "OT", "Song of Solomon": "OT", "Isaiah": "OT",
    "Jeremiah": "OT", "Lamentations": "OT", "Ezekiel": "OT", "Daniel": "OT",
    "Hosea": "OT", "Joel": "OT", "Amos": "OT", "Obadiah": "OT", "Jonah": "OT",
    "Micah": "OT", "Nahum": "OT", "Habakkuk": "OT", "Zephaniah": "OT",
    "Haggai": "OT", "Zechariah": "OT", "Malachi": "OT",
    "Tobit": "Deuterocanon", "Judith": "Deuterocanon", "1 Esdras": "Deuterocanon",
    "1 Maccabees": "Deuterocanon", "2 Maccabees": "Deuterocanon", "3 Maccabees": "Deuterocanon",
    "Wisdom of Solomon": "Deuterocanon", "Sirach": "Deuterocanon", "Baruch": "Deuterocanon",
    "Epistle of Jeremiah": "Deuterocanon", "Susanna": "Deuterocanon", "Bel and the Dragon": "Deuterocanon",
    "Matthew": "NT", "Mark": "NT", "Luke": "NT", "John": "NT", "Acts": "NT",
    "Romans": "NT", "1 Corinthians": "NT", "2 Corinthians": "NT", "Galatians": "NT",
    "Ephesians": "NT", "Philippians": "NT", "Colossians": "NT", "1 Thessalonians": "NT",
    "2 Thessalonians": "NT", "1 Timothy": "NT", "2 Timothy": "NT", "Titus": "NT",
    "Philemon": "NT", "Hebrews": "NT", "James": "NT", "1 Peter": "NT", "2 Peter": "NT",
    "1 John": "NT", "2 John": "NT", "3 John": "NT", "Jude": "NT", "Revelation": "NT",
}

BOOK_GENRE = {
    "Genesis": "Torah", "Exodus": "Torah", "Leviticus": "Torah",
    "Numbers": "Torah", "Deuteronomy": "Torah",
    "Joshua": "Historical", "Judges": "Historical", "Ruth": "Historical",
    "1 Kingdoms": "Historical", "2 Kingdoms": "Historical",
    "3 Kingdoms": "Historical", "4 Kingdoms": "Historical",
    "1 Chronicles": "Historical", "2 Chronicles": "Historical",
    "1 Esdras": "Historical", "Ezra": "Historical", "Nehemiah": "Historical",
    "Tobit": "Historical", "Judith": "Historical", "Esther": "Historical",
    "1 Maccabees": "Historical", "2 Maccabees": "Historical", "3 Maccabees": "Historical",
    "Job": "Wisdom", "Psalms": "Wisdom", "Proverbs": "Wisdom",
    "Ecclesiastes": "Wisdom", "Song of Solomon": "Wisdom",
    "Wisdom of Solomon": "Wisdom", "Sirach": "Wisdom",
    "Isaiah": "Prophetic", "Jeremiah": "Prophetic", "Lamentations": "Prophetic",
    "Baruch": "Prophetic", "Epistle of Jeremiah": "Prophetic",
    "Ezekiel": "Prophetic", "Daniel": "Prophetic",
    "Susanna": "Prophetic", "Bel and the Dragon": "Prophetic",
    "Hosea": "Prophetic", "Joel": "Prophetic", "Amos": "Prophetic",
    "Obadiah": "Prophetic", "Jonah": "Prophetic", "Micah": "Prophetic",
    "Nahum": "Prophetic", "Habakkuk": "Prophetic", "Zephaniah": "Prophetic",
    "Haggai": "Prophetic", "Zechariah": "Prophetic", "Malachi": "Prophetic",
    "Matthew": "Gospel", "Mark": "Gospel", "Luke": "Gospel", "John": "Gospel",
    "Acts": "Acts",
    "Romans": "Epistle", "1 Corinthians": "Epistle", "2 Corinthians": "Epistle",
    "Galatians": "Epistle", "Ephesians": "Epistle", "Philippians": "Epistle",
    "Colossians": "Epistle", "1 Thessalonians": "Epistle", "2 Thessalonians": "Epistle",
    "1 Timothy": "Epistle", "2 Timothy": "Epistle", "Titus": "Epistle",
    "Philemon": "Epistle", "Hebrews": "Epistle", "James": "Epistle",
    "1 Peter": "Epistle", "2 Peter": "Epistle",
    "1 John": "Epistle", "2 John": "Epistle", "3 John": "Epistle", "Jude": "Epistle",
    "Revelation": "Apocalypse",
}

FRONT_CLOSE = re.compile(r'^---\s*$')

updated = skipped = 0

for dirpath, _, filenames in os.walk(SCRIPTURE_ROOT):
    for fname in filenames:
        if not fname.endswith(".md") or " — " in fname:
            continue  # skip OSB Notes companions
        fpath = os.path.join(dirpath, fname)
        book = os.path.basename(dirpath)
        testament = BOOK_TESTAMENT.get(book)
        genre = BOOK_GENRE.get(book)
        if not testament:
            skipped += 1
            continue

        with open(fpath, encoding="utf-8") as f:
            content = f.read()

        # Already has these fields — skip
        if "testament:" in content and "genre:" in content:
            skipped += 1
            continue

        # Insert after opening ---
        lines = content.split("\n")
        if lines[0].strip() != "---":
            skipped += 1
            continue

        insert_at = 1
        new_lines = lines[:insert_at] + [
            f'testament: "{testament}"',
            f'genre: "{genre}"',
        ] + lines[insert_at:]

        with open(fpath, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines))
        updated += 1

print(f"Updated: {updated}  Skipped: {skipped}")
