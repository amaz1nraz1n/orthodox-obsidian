"""One-off: inject book_id into existing vault hub frontmatter."""
import os, re

VAULT = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-jmtharp90@gmail.com/My Drive/Jasper/Jasper"
)
SCRIPTURE_ROOT = os.path.join(VAULT, "Holy Tradition", "Holy Scripture")

BOOK_ABBREVIATIONS = {
    "Genesis": "Gen", "Exodus": "Ex", "Leviticus": "Lev", "Numbers": "Num", "Deuteronomy": "Deut",
    "Joshua": "Josh", "Judges": "Judg", "Ruth": "Ruth", "1 Kingdoms": "1 Sam", "2 Kingdoms": "2 Sam",
    "3 Kingdoms": "1 Kin", "4 Kingdoms": "2 Kin", "1 Chronicles": "1 Chr", "2 Chronicles": "2 Chr",
    "1 Esdras": "1 Esd", "Ezra": "Ezra", "Nehemiah": "Neh", "Tobit": "Tob", "Judith": "Jdt",
    "Esther": "Esth", "1 Maccabees": "1 Mac", "2 Maccabees": "2 Mac", "3 Maccabees": "3 Mac",
    "Psalms": "Ps", "Job": "Job", "Proverbs": "Prov", "Ecclesiastes": "Eccl",
    "Song of Solomon": "Song", "Wisdom of Solomon": "Wis", "Sirach": "Sir",
    "Hosea": "Hos", "Amos": "Am", "Micah": "Mic", "Joel": "Joel", "Obadiah": "Obad",
    "Jonah": "Jon", "Nahum": "Nah", "Habakkuk": "Hab", "Zephaniah": "Zeph", "Haggai": "Hag",
    "Zechariah": "Zech", "Malachi": "Mal", "Isaiah": "Is", "Jeremiah": "Jer", "Baruch": "Bar",
    "Lamentations": "Lam", "Epistle of Jeremiah": "EpJer", "Ezekiel": "Ezek", "Daniel": "Dan",
    "Susanna": "Sus", "Bel and the Dragon": "Bel",
    "Matthew": "Mt", "Mark": "Mk", "Luke": "Lk", "John": "Jn", "Acts": "Acts",
    "Romans": "Rom", "1 Corinthians": "1 Cor", "2 Corinthians": "2 Cor", "Galatians": "Gal",
    "Ephesians": "Eph", "Philippians": "Phil", "Colossians": "Col",
    "1 Thessalonians": "1 Thess", "2 Thessalonians": "2 Thess",
    "1 Timothy": "1 Tim", "2 Timothy": "2 Tim", "Titus": "Tit", "Philemon": "Phlm",
    "Hebrews": "Heb", "James": "Jas", "1 Peter": "1 Pet", "2 Peter": "2 Pet",
    "1 John": "1 Jn", "2 John": "2 Jn", "3 John": "3 Jn", "Jude": "Jude", "Revelation": "Rev",
}

updated = skipped = 0

for dirpath, _, filenames in os.walk(SCRIPTURE_ROOT):
    book = os.path.basename(dirpath)
    abbr = BOOK_ABBREVIATIONS.get(book)
    if not abbr:
        continue
    for fname in filenames:
        if not fname.endswith(".md") or " — " in fname:
            continue
        fpath = os.path.join(dirpath, fname)
        with open(fpath, encoding="utf-8") as f:
            content = f.read()
        if "book_id:" in content:
            skipped += 1
            continue
        # Insert book_id after genre: line
        new_content = re.sub(
            r'(genre: "[^"]*")',
            rf'\1\nbook_id: "{abbr}"',
            content, count=1
        )
        if new_content == content:
            skipped += 1
            continue
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(new_content)
        updated += 1

print(f"Updated: {updated}  Skipped: {skipped}")
