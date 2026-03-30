"""
Canonical Orthodox Scripture metadata — single source of truth for all extractors.

Book names use Roman numerals for numbered books (I Kingdoms, II Corinthians, etc.)
to match vault folder/file naming conventions.
"""

# Maps book_name -> (top_level_folder, canonical_order_within_folder)
BOOK_FOLDER: dict[str, tuple[str, int]] = {
    # 01 - Old Testament (all 51 books in LXX canonical order)
    "Genesis":             ("01 - Old Testament",  1),
    "Exodus":              ("01 - Old Testament",  2),
    "Leviticus":           ("01 - Old Testament",  3),
    "Numbers":             ("01 - Old Testament",  4),
    "Deuteronomy":         ("01 - Old Testament",  5),
    "Joshua":              ("01 - Old Testament",  6),
    "Judges":              ("01 - Old Testament",  7),
    "Ruth":                ("01 - Old Testament",  8),
    "I Kingdoms":          ("01 - Old Testament",  9),
    "II Kingdoms":         ("01 - Old Testament", 10),
    "III Kingdoms":        ("01 - Old Testament", 11),
    "IV Kingdoms":         ("01 - Old Testament", 12),
    "I Chronicles":        ("01 - Old Testament", 13),
    "II Chronicles":       ("01 - Old Testament", 14),
    "I Esdras":            ("01 - Old Testament", 15),
    "Ezra":                ("01 - Old Testament", 16),
    "Nehemiah":            ("01 - Old Testament", 17),
    "Tobit":               ("01 - Old Testament", 18),
    "Judith":              ("01 - Old Testament", 19),
    "Esther":              ("01 - Old Testament", 20),
    "I Maccabees":         ("01 - Old Testament", 21),
    "II Maccabees":        ("01 - Old Testament", 22),
    "III Maccabees":       ("01 - Old Testament", 23),
    "Psalms":              ("01 - Old Testament", 24),
    "Job":                 ("01 - Old Testament", 25),
    "Proverbs":            ("01 - Old Testament", 26),
    "Ecclesiastes":        ("01 - Old Testament", 27),
    "Song of Solomon":     ("01 - Old Testament", 28),
    "Wisdom of Solomon":   ("01 - Old Testament", 29),
    "Sirach":              ("01 - Old Testament", 30),
    "Isaiah":              ("01 - Old Testament", 31),
    "Jeremiah":            ("01 - Old Testament", 32),
    "Baruch":              ("01 - Old Testament", 33),
    "Lamentations":        ("01 - Old Testament", 34),
    "Epistle of Jeremiah": ("01 - Old Testament", 35),
    "Ezekiel":             ("01 - Old Testament", 36),
    "Daniel":              ("01 - Old Testament", 37),
    "Susanna":             ("01 - Old Testament", 38),
    "Bel and the Dragon":  ("01 - Old Testament", 39),
    "Hosea":               ("01 - Old Testament", 40),
    "Joel":                ("01 - Old Testament", 41),
    "Amos":                ("01 - Old Testament", 42),
    "Obadiah":             ("01 - Old Testament", 43),
    "Jonah":               ("01 - Old Testament", 44),
    "Micah":               ("01 - Old Testament", 45),
    "Nahum":               ("01 - Old Testament", 46),
    "Habakkuk":            ("01 - Old Testament", 47),
    "Zephaniah":           ("01 - Old Testament", 48),
    "Haggai":              ("01 - Old Testament", 49),
    "Zechariah":           ("01 - Old Testament", 50),
    "Malachi":             ("01 - Old Testament", 51),
    # 02 - New Testament (canonical order)
    "Matthew":             ("02 - New Testament",  1),
    "Mark":                ("02 - New Testament",  2),
    "Luke":                ("02 - New Testament",  3),
    "John":                ("02 - New Testament",  4),
    "Acts":                ("02 - New Testament",  5),
    "Romans":              ("02 - New Testament",  6),
    "I Corinthians":       ("02 - New Testament",  7),
    "II Corinthians":      ("02 - New Testament",  8),
    "Galatians":           ("02 - New Testament",  9),
    "Ephesians":           ("02 - New Testament", 10),
    "Philippians":         ("02 - New Testament", 11),
    "Colossians":          ("02 - New Testament", 12),
    "I Thessalonians":     ("02 - New Testament", 13),
    "II Thessalonians":    ("02 - New Testament", 14),
    "I Timothy":           ("02 - New Testament", 15),
    "II Timothy":          ("02 - New Testament", 16),
    "Titus":               ("02 - New Testament", 17),
    "Philemon":            ("02 - New Testament", 18),
    "Hebrews":             ("02 - New Testament", 19),
    "James":               ("02 - New Testament", 20),
    "I Peter":             ("02 - New Testament", 21),
    "II Peter":            ("02 - New Testament", 22),
    "I John":              ("02 - New Testament", 23),
    "II John":             ("02 - New Testament", 24),
    "III John":            ("02 - New Testament", 25),
    "Jude":                ("02 - New Testament", 26),
    "Revelation":          ("02 - New Testament", 27),
}

# Standard scholarly abbreviations (Arabic numerals, per SBL/academic convention)
BOOK_ABBREVIATIONS: dict[str, str] = {
    "Genesis": "Gen", "Exodus": "Ex", "Leviticus": "Lev", "Numbers": "Num",
    "Deuteronomy": "Deut", "Joshua": "Josh", "Judges": "Judg", "Ruth": "Ruth",
    "I Kingdoms": "1 Sam", "II Kingdoms": "2 Sam",
    "III Kingdoms": "1 Kin", "IV Kingdoms": "2 Kin",
    "I Chronicles": "1 Chr", "II Chronicles": "2 Chr",
    "I Esdras": "1 Esd", "Ezra": "Ezra", "Nehemiah": "Neh",
    "Tobit": "Tob", "Judith": "Jdt", "Esther": "Esth",
    "I Maccabees": "1 Mac", "II Maccabees": "2 Mac", "III Maccabees": "3 Mac",
    "Psalms": "Ps", "Job": "Job", "Proverbs": "Prov", "Ecclesiastes": "Eccl",
    "Song of Solomon": "Song", "Wisdom of Solomon": "Wis", "Sirach": "Sir",
    "Hosea": "Hos", "Amos": "Am", "Micah": "Mic", "Joel": "Joel",
    "Obadiah": "Obad", "Jonah": "Jon", "Nahum": "Nah", "Habakkuk": "Hab",
    "Zephaniah": "Zeph", "Haggai": "Hag", "Zechariah": "Zech", "Malachi": "Mal",
    "Isaiah": "Is", "Jeremiah": "Jer", "Baruch": "Bar", "Lamentations": "Lam",
    "Epistle of Jeremiah": "EpJer", "Ezekiel": "Ezek", "Daniel": "Dan",
    "Susanna": "Sus", "Bel and the Dragon": "Bel",
    "Matthew": "Mt", "Mark": "Mk", "Luke": "Lk", "John": "Jn", "Acts": "Acts",
    "Romans": "Rom", "I Corinthians": "1 Cor", "II Corinthians": "2 Cor",
    "Galatians": "Gal", "Ephesians": "Eph", "Philippians": "Phil",
    "Colossians": "Col", "I Thessalonians": "1 Thess", "II Thessalonians": "2 Thess",
    "I Timothy": "1 Tim", "II Timothy": "2 Tim", "Titus": "Tit", "Philemon": "Phlm",
    "Hebrews": "Heb", "James": "Jas", "I Peter": "1 Pet", "II Peter": "2 Pet",
    "I John": "1 Jn", "II John": "2 Jn", "III John": "3 Jn",
    "Jude": "Jude", "Revelation": "Rev",
}

# Frontmatter testament field values
BOOK_TESTAMENT: dict[str, str] = {
    "Genesis": "OT", "Exodus": "OT", "Leviticus": "OT", "Numbers": "OT",
    "Deuteronomy": "OT", "Joshua": "OT", "Judges": "OT", "Ruth": "OT",
    "I Kingdoms": "OT", "II Kingdoms": "OT", "III Kingdoms": "OT", "IV Kingdoms": "OT",
    "I Chronicles": "OT", "II Chronicles": "OT",
    "Ezra": "OT", "Nehemiah": "OT", "Esther": "OT",
    "Psalms": "OT", "Job": "OT", "Proverbs": "OT", "Ecclesiastes": "OT",
    "Song of Solomon": "OT", "Isaiah": "OT", "Jeremiah": "OT",
    "Lamentations": "OT", "Ezekiel": "OT", "Daniel": "OT",
    "Hosea": "OT", "Joel": "OT", "Amos": "OT", "Obadiah": "OT", "Jonah": "OT",
    "Micah": "OT", "Nahum": "OT", "Habakkuk": "OT", "Zephaniah": "OT",
    "Haggai": "OT", "Zechariah": "OT", "Malachi": "OT",
    "Tobit": "Deuterocanon", "Judith": "Deuterocanon", "I Esdras": "Deuterocanon",
    "I Maccabees": "Deuterocanon", "II Maccabees": "Deuterocanon",
    "III Maccabees": "Deuterocanon", "Wisdom of Solomon": "Deuterocanon",
    "Sirach": "Deuterocanon", "Baruch": "Deuterocanon",
    "Epistle of Jeremiah": "Deuterocanon", "Susanna": "Deuterocanon",
    "Bel and the Dragon": "Deuterocanon",
    "Matthew": "NT", "Mark": "NT", "Luke": "NT", "John": "NT", "Acts": "NT",
    "Romans": "NT", "I Corinthians": "NT", "II Corinthians": "NT",
    "Galatians": "NT", "Ephesians": "NT", "Philippians": "NT", "Colossians": "NT",
    "I Thessalonians": "NT", "II Thessalonians": "NT",
    "I Timothy": "NT", "II Timothy": "NT", "Titus": "NT", "Philemon": "NT",
    "Hebrews": "NT", "James": "NT", "I Peter": "NT", "II Peter": "NT",
    "I John": "NT", "II John": "NT", "III John": "NT", "Jude": "NT", "Revelation": "NT",
}

BOOK_GENRE: dict[str, str] = {
    "Genesis": "Torah", "Exodus": "Torah", "Leviticus": "Torah",
    "Numbers": "Torah", "Deuteronomy": "Torah",
    "Joshua": "Historical", "Judges": "Historical", "Ruth": "Historical",
    "I Kingdoms": "Historical", "II Kingdoms": "Historical",
    "III Kingdoms": "Historical", "IV Kingdoms": "Historical",
    "I Chronicles": "Historical", "II Chronicles": "Historical",
    "I Esdras": "Historical", "Ezra": "Historical", "Nehemiah": "Historical",
    "Tobit": "Historical", "Judith": "Historical", "Esther": "Historical",
    "I Maccabees": "Historical", "II Maccabees": "Historical", "III Maccabees": "Historical",
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
    "Romans": "Epistle", "I Corinthians": "Epistle", "II Corinthians": "Epistle",
    "Galatians": "Epistle", "Ephesians": "Epistle", "Philippians": "Epistle",
    "Colossians": "Epistle", "I Thessalonians": "Epistle", "II Thessalonians": "Epistle",
    "I Timothy": "Epistle", "II Timothy": "Epistle", "Titus": "Epistle",
    "Philemon": "Epistle", "Hebrews": "Epistle", "James": "Epistle",
    "I Peter": "Epistle", "II Peter": "Epistle",
    "I John": "Epistle", "II John": "Epistle", "III John": "Epistle", "Jude": "Epistle",
    "Revelation": "Apocalypse",
}


BOOK_CHAPTER_COUNT: dict[str, int] = {
    "Genesis": 50, "Exodus": 40, "Leviticus": 27, "Numbers": 36, "Deuteronomy": 34,
    "Joshua": 24, "Judges": 21, "Ruth": 4,
    "I Kingdoms": 31, "II Kingdoms": 24, "III Kingdoms": 22, "IV Kingdoms": 25,
    "I Chronicles": 29, "II Chronicles": 36,
    "I Esdras": 9, "Ezra": 10, "Nehemiah": 13,
    "Tobit": 14, "Judith": 16, "Esther": 10,  # OSB EPUB has MT chs 1-10 only; Greek additions (A-F) not in source
    "I Maccabees": 16, "II Maccabees": 15, "III Maccabees": 7,
    "Psalms": 151, "Job": 42, "Proverbs": 31, "Ecclesiastes": 12, "Song of Solomon": 8,
    "Wisdom of Solomon": 19, "Sirach": 51,
    "Isaiah": 66, "Jeremiah": 52, "Baruch": 5, "Lamentations": 5,
    "Epistle of Jeremiah": 1,
    "Ezekiel": 48, "Daniel": 12, "Susanna": 1, "Bel and the Dragon": 1,
    "Hosea": 14, "Joel": 3, "Amos": 9, "Obadiah": 1, "Jonah": 4,
    "Micah": 7, "Nahum": 3, "Habakkuk": 3, "Zephaniah": 3,
    "Haggai": 2, "Zechariah": 14, "Malachi": 3,  # OSB EPUB follows LXX (3 chs); MT has 4
    "Matthew": 28, "Mark": 16, "Luke": 24, "John": 21, "Acts": 28,
    "Romans": 16, "I Corinthians": 16, "II Corinthians": 13,
    "Galatians": 6, "Ephesians": 6, "Philippians": 4, "Colossians": 4,
    "I Thessalonians": 5, "II Thessalonians": 3,
    "I Timothy": 6, "II Timothy": 4, "Titus": 3, "Philemon": 1,
    "Hebrews": 13, "James": 5, "I Peter": 5, "II Peter": 3,
    "I John": 5, "II John": 1, "III John": 1, "Jude": 1, "Revelation": 22,
}


def _build_psalm_kathisma() -> Dict[int, tuple]:
    """Return {lxx_psalm: (kathisma, stasis)} for Pss 1-150.

    Stasis is 1/2/3 per the OCA division.  Ps 118 is all of Kathisma XVII
    but stasis depends on verse range, so stasis=0 (omit from frontmatter).
    Ps 151 is outside the 20-kathisma cycle.
    Source: OCA, 'The Division of the Psalter into Kathismas' (LXX numbering).
    """
    data: list[tuple[int, int, int, int]] = [
        # kathisma, stasis, first_psalm, last_psalm
        (1,  1,   1,   3), (1,  2,   4,   6), (1,  3,   7,   8),
        (2,  1,   9,  10), (2,  2,  11,  13), (2,  3,  14,  16),
        (3,  1,  17,  17), (3,  2,  18,  20), (3,  3,  21,  23),
        (4,  1,  24,  26), (4,  2,  27,  29), (4,  3,  30,  31),
        (5,  1,  32,  33), (5,  2,  34,  35), (5,  3,  36,  36),
        (6,  1,  37,  39), (6,  2,  40,  42), (6,  3,  43,  45),
        (7,  1,  46,  48), (7,  2,  49,  50), (7,  3,  51,  54),
        (8,  1,  55,  57), (8,  2,  58,  60), (8,  3,  61,  63),
        (9,  1,  64,  66), (9,  2,  67,  67), (9,  3,  68,  69),
        (10, 1,  70,  71), (10, 2,  72,  73), (10, 3,  74,  76),
        (11, 1,  77,  77), (11, 2,  78,  80), (11, 3,  81,  84),
        (12, 1,  85,  87), (12, 2,  88,  88), (12, 3,  89,  90),
        (13, 1,  91,  93), (13, 2,  94,  96), (13, 3,  97, 100),
        (14, 1, 101, 102), (14, 2, 103, 103), (14, 3, 104, 104),
        (15, 1, 105, 105), (15, 2, 106, 106), (15, 3, 107, 108),
        (16, 1, 109, 111), (16, 2, 112, 114), (16, 3, 115, 117),
        (18, 1, 119, 123), (18, 2, 124, 128), (18, 3, 129, 133),
        (19, 1, 134, 136), (19, 2, 137, 139), (19, 3, 140, 142),
        (20, 1, 143, 144), (20, 2, 145, 147), (20, 3, 148, 150),
    ]
    m: dict[int, tuple[int, int]] = {}
    for kath, stasis, first, last in data:
        for ps in range(first, last + 1):
            m[ps] = (kath, stasis)
    m[118] = (17, 0)
    return m


PSALM_KATHISMA: dict[int, tuple[int, int]] = _build_psalm_kathisma()


def _build_lxx_to_mt() -> dict[int, int | None]:
    m: dict[int, int | None] = {}
    for i in range(1, 9):    m[i] = i        # 1–8: identical
    m[9] = 9                                  # LXX 9 = MT 9 (LXX merges MT 9+10)
    for i in range(10, 113): m[i] = i + 1   # 10–112: offset +1
    m[113] = 114                              # LXX 113 = MT 114 (merges MT 114+115)
    m[114] = 116                              # LXX 114 = MT 116:1-9
    m[115] = 116                              # LXX 115 = MT 116:10-19
    for i in range(116, 146): m[i] = i + 1  # 116–145: offset +1
    m[146] = 147                              # LXX 146 = MT 147:1-11
    m[147] = 147                              # LXX 147 = MT 147:12-20
    for i in range(148, 151): m[i] = i      # 148–150: identical
    m[151] = None                             # LXX 151: no MT equivalent
    return m

LXX_TO_MT: dict[int, int | None] = _build_lxx_to_mt()


def book_folder_path(book: str) -> str:
    """Return the relative folder path for a book's chapter files.

    Example: 'John' -> '02 - New Testament/04 - John'
    """
    folder, order = BOOK_FOLDER.get(book, ("01 - Old Testament", 99))
    return f"{folder}/{order:02d} - {book}"


# Books where the chapter file/link prefix differs from the canonical book name.
_BOOK_FILE_PREFIX: dict[str, str] = {
    "Psalms": "Psalm",
}
_FILE_PREFIX_TO_CANONICAL: dict[str, str] = {v: k for k, v in _BOOK_FILE_PREFIX.items()}


def book_file_prefix(book: str) -> str:
    """Return the prefix used in file names and wikilinks for individual chapters.

    For most books this equals the book name (e.g. 'Genesis', 'John').
    Psalms uses 'Psalm' (singular) so files are 'Psalm 50.md', not 'Psalms 50.md'.
    The book index page itself (e.g. [[Psalms]]) retains the canonical plural name.
    """
    return _BOOK_FILE_PREFIX.get(book, book)


def canonical_book_name(prefix: str) -> str:
    """Return the canonical book name from a file prefix.

    Inverse of book_file_prefix: 'Psalm' → 'Psalms'; all others unchanged.
    Use when parsing file names or wikilinks back to canonical book names.
    """
    return _FILE_PREFIX_TO_CANONICAL.get(prefix, prefix)
