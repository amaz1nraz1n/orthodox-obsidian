# Lexham English Septuagint (LES) EPUB Source Structure

Implementation-facing structure notes for the Lexham adapter.
See also: `docs/osb-epub-source-structure.md`, `docs/eob-pdf-source-structure.md`, `docs/net-pdf-source-structure.md`

---

**Adapter:** `vault_builder/adapters/sources/lexham_epub.py`
**Coverage:** OT only (all canonical LXX OT books except Esdras B)
**Source file:** `Lexham English Septuagint.epub`

---

## Spine Layout

| Range | Content |
|---|---|
| f1.xhtml – f7.xhtml | Front matter (skip) |
| f8.xhtml – f79.xhtml | Scripture content |

79 XHTML files total. A single book may span multiple files (e.g. Genesis: f8 + f9). File content is processed in OPF spine order.

---

## Book Detection

```html
<p class="x1F">
  <a id="{CODE}">Book Name</a>
  …
</p>
```

`CODE` maps to canonical vault name via `LEXHAM_CODE_TO_BOOK`. Book detection updates state and skips all visible text.

---

## Chapter and Verse Anchor Structure

```html
<!-- Chapter heading paragraph (class x15) -->
<p class="x15">
  <a id="{CODE}.{N}">                                   <!-- chapter anchor -->
  <a id="{CODE}.{N}_BibleLXX2_{Short}_{N}_1">           <!-- verse 1 anchor -->
  <i>Pericope title text</i>                            <!-- skip text -->
</p>

<!-- Editorial section heading within chapter (class x22) -->
<p class="x22">…may contain verse anchor…</p>           <!-- skip text, process anchors -->
```

**Anchor patterns:**

| Pattern | Regex | Captures |
|---|---|---|
| Chapter anchor | `^[A-Z0-9]+\.(\d+)$` | chapter number |
| Verse anchor | `^[A-Z0-9]+\.(\d+)_BibleLXX2_[\w]+_\d+_(\d+)$` | chapter, verse |

---

## Verse Content Paragraphs

The adapter uses open processing: all paragraphs not in `_HEADING_P_CLASSES` or `_SKIP_P_CLASSES` are treated as verse-bearing. The full set of paragraph classes found in Scripture content:

**Verse-starting paragraphs** (carry a verse anchor `<a id="CODE.N_BibleLXX2_...">` plus verse text):

| Class | Context |
|---|---|
| `x12` | Rare prose verse blocks |
| `x13` | Primary prose verse paragraph |
| `x16` | Verse-starting with drop-cap (chapter/psalm opening) |
| `x17` | Alternate prose verse paragraph |
| `x26`, `x28`, `x29` | Verse-starting poetry lines (Genesis, Psalms, poetic books) |
| `x2D` | Verse-starting poetry (Numbers, Kings, priestly blessings) |
| `x2F` | Verse-starting song/poem (Deuteronomy 32, Proverbs) |
| `x31` | Verse-starting poetry variant |
| `x33`, `x35`, `x36` | Verse-starting poetry in Psalms |

**Poetry continuation paragraphs** (no verse anchor; text appended to preceding verse):

| Class | Context |
|---|---|
| `x23`, `x24`, `x25` | Poetry continuation lines (Genesis, general) |
| `x2B`, `x2E` | Poetry/quoted-speech continuation (rare) |

**Editorial / structural paragraphs** (handled explicitly, not as verse text):

| Class | Content | Action |
|---|---|---|
| `x34` | "Musical interlude" (LXX Diapsalma / Hebrew Selah) | Recorded as `Chapter.after_markers[verse_num]` |
| `x15` | Chapter heading + pericope title + verse 1 anchor | `_HEADING_P_CLASSES` — anchors extracted, text skipped |
| `x22` | Section heading within chapter | `_HEADING_P_CLASSES` — anchors extracted, text skipped |
| `x1F` | Book title | `_SKIP_P_CLASSES` — book code extracted |

**Inline span types:**

| Class | Role | Action |
|---|---|---|
| `x20` | Drop-cap chapter/psalm number | Skip entirely |
| `x21` | Inline verse numbers (most prose books) | Skip entirely |
| `x27` | Inline verse numbers (Psalms poetry variant) | Skip entirely |
| `x2A`, `x30` | Inline verse numbers (poetic variant) | Skip entirely |
| `x37`, `x38` | Inline verse numbers (Psalms 100+, poetic variant) | Skip entirely |
| `Space`, `Space1`, `Space2` | Spacing glyphs | Skip entirely |
| `x2C` | Alternate inline footnote marker (4 occurrences; bare letter/digit) | Skip entirely |
| `x1B` (on `<a>`) | Footnote marker (standard, 1,141 occurrences) | Skip entire `<a>` tag; **planned:** preserve as `<sup class="nt-tn">[[Book Ch — Lexham Notes#vN|*]]</sup>` (all Lexham notes are translation notes → `*` symbol) |
| `x18` | Transliterated names / acrostic letters (Lam, Ps 119) | Recurse for text |
| `x32` | Psalm superscription text (within x16 paragraph) | Recurse for text — IS canonical v1 content |
| `xD` | Small-caps drop-cap formatting | Recurse for text |
| `SpaceN` | Spacing glyphs in f79.xhtml only | Harmless in footnote context |
| others | Inline formatting | Recurse for text |

---

## Domain Mapping

| Source structure | Extractor pass | Domain target | Status |
|---|---|---|---|
| Verse-bearing paragraphs (`x12`, `x13`, `x16`, `x17`, `x31`) | `read_text()` | `Book` → `Chapter` → `Verse` | ✅ implemented |
| Footnote markers (`x1B`) in verse paragraphs | `read_text()` | — | ✅ stripped; anchor captured for note attribution |
| Footnote definitions (`f79.xhtml`) | `read_notes()` | `ChapterNotes.footnotes` | ✅ implemented — all 1,150 notes parsed; notes companions not yet wired in `extract_lexham.py` |

Book codes map to Orthodox canonical names (e.g. `"KI1"` → `"I Kingdoms"`). See `LEXHAM_CODE_TO_BOOK` in the adapter.

---

## Skipped / Out-of-Canon Codes

| Code | Reason |
|---|---|
| ES2 (Esdras B) | Lexham treats it as one book (ch 1–23); vault canon splits into Ezra (1–10) and Nehemiah (1–13). Chapter-offset split out of Phase 1 scope. |
| DAA | Alternate Daniel |
| EN | Enoch |
| TOBA | Alternate Tobit |
| ODE | Odes |
| PSSOL | Psalms of Solomon |
| MAC4 | IV Maccabees |
| INTRO | Front matter code |

---

## Sample Chapter Coverage

Chapters exercised by the current sample set in `extract_lexham.py` (aligned to the OSB OT sample envelope; Lexham is OT-only):

| Chapter | Genre | Notes |
|---|---|---|
| Genesis 1 | Torah | |
| Exodus 20 | Torah | Ten Commandments |
| Leviticus 1 | Torah / Priestly | |
| I Kingdoms 1 | Historical | Mapped from Lexham code `KI1` |
| Psalms 1 | Wisdom / Poetry | |
| Psalms 50 | Wisdom / Poetry | LXX Ps 50 = MT Ps 51 |
| Job 3 | Wisdom / Drama | |
| Proverbs 8 | Wisdom / Poetry | |
| Song of Solomon 1 | Wisdom / Poetry | |
| Sirach 1 | Deuterocanon / Wisdom | |
| I Maccabees 1 | Deuterocanon / Historical | |
| Lamentations 1 | Poetry / Acrostic | |
| Ezekiel 1 | Prophecy / Vision | |

**Note:** Lexham LES is OT-only; NT chapters are not covered. The current sample set exercises 15 OT chapters from the OSB sample envelope.

---

## Known Gaps / Caveats

| Issue | Detail |
|---|---|
| Esdras B split pending | See skipped codes above. Will require a chapter-offset mapping to split ch 1–10 → Ezra, ch 11–23 → Nehemiah. |
| Notes companions wired ✓ | `read_notes()` parses all 1,150 footnotes; `extract_lexham.py` calls it and writes `{Book} {Ch} — Lexham Notes.md` companions. Resolved 2026-03-23. |
| Italic / formatting lost | Inline `<i>` and `<b>` within verse text are extracted as plain text only. |

---

## Footnote Definitions (f79.xhtml)

All footnotes for the entire LES are collected in a single back-of-book file: `OEBPS/f79.xhtml`.

### File structure

- `<p class="BM1">` — book heading separator (e.g. `Genesis`, `Exodus`, `Psalms`)
- `<p class="List1">` — one footnote entry per paragraph

### Footnote anchor ID format

```
FN.{global_chapter_number}.{letter}_c0_e0
```

`global_chapter_number` is a running integer across the entire EPUB spine (including
front-matter intro pages numbered I–XII). Genesis chapter 1 = `FN.1.A`, Exodus chapter 1 =
`FN.63.A`, Psalms chapter 1 ≈ `FN.591.A`. The anchor ID is globally unique (verified:
each ID appears exactly once in f79.xhtml).

### Footnote text format

Paragraph text: `{letter}{note_content}`, e.g. `aLit. "of the water and of the water"`.
Strip the leading letter sigil when extracting note content.

### Inline footnote marker format (main XHTML)

```html
<a class="x1B" href="f79.xhtml#FN.1.A_c0_e0"><i>a</i></a>
```

The `href` attribute carries the anchor ID directly — extract after `#`.

### Verse attribution

The inline `x1B` marker appears in a verse-bearing paragraph (classes `x12`, `x13`,
`x16`, `x17`, `x31`). Since verse anchors (`<a id="CODE.chapter_BibleLXX2_...">`)
appear before their verse content in DOM order, the footnote belongs to the verse whose
anchor most recently preceded the `x1B` marker in the paragraph's children walk.

### Note families

Lexham footnotes are uniformly translation notes (literal renderings, alternate readings,
textual comparanda). All notes map to the `footnotes` family in `ChapterNotes` and render
with the `[!tn]` callout in the Obsidian companion.

### Total footnotes

1,150 entries in f79.xhtml (includes ~9 intro footnotes with Roman numeral chapter codes
such as `FN.XII.1` — these will never match a verse chapter reference and are harmlessly
present in the lookup dict).

---

## Related Docs

| Doc | What it covers |
|---|---|
| `docs/osb-epub-source-structure.md` | OSB EPUB — full tag/class inventory, note file structure, known gaps |
| `docs/eob-pdf-source-structure.md` | EOB NT PDF — page range, box classification, chapter patterns |
| `docs/net-pdf-source-structure.md` | NET Bible PDF — two-column layout, note box parsing, column cursors |
| `docs/implementation-architecture.md` | Ports & Adapters design, domain model, renderer contracts |
| `docs/source-roadmap.md` | Source status, phase roadmap, acquisition notes |
| `docs/validation-plan.md` | Validator rules, fixture strategy, test execution policy |
