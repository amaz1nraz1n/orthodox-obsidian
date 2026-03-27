# NET Bible First Edition PDF Source Structure

Implementation-facing structure notes for the NET adapter.
See also: `docs/osb-epub-source-structure.md`, `docs/lexham-epub-source-structure.md`, `docs/eob-pdf-source-structure.md`

---

**Adapter:** `vault_builder/adapters/sources/net_pdf.py`
**Coverage:** Full Bible translator's apparatus (notes layer — not canonical verse text)
**Source file:** `The NET Bible, First Edition.pdf`

---

## Physical Layout

| Property | Value |
|---|---|
| Layout | Two-column |
| Left column x | ≈ 29 pt |
| Right column x | ≈ 219 pt |
| Column boundary | x < 215 = left, x ≥ 215 = right |
| Page header y threshold | y > 620 = running header (skip) |

Text boxes are sorted top-to-bottom, left-to-right (`(-y, x)`) within each page.

---

## Text Box Classification Order

Each text box is classified in this order (first match wins):

1. **Running page header** — y > 620 → skip
2. **Book title** — raw (normalized) text matches a key in `_NET_TITLE_TO_BOOK` exactly → update book state, reset cursors
3. **Note box** — raw text matches `_IS_NOTE_RE` (contains `\xa0tn\xa0`, `\xa0sn\xa0`, `\xa0tc\xa0`, or `\xa0map\xa0`) → parse notes for current column's cursor
4. **Verse text box** — normalized text starts with `\d{1,3}:\d{1,3}\s+` → update this column's chapter/verse cursor

---

## Font Encoding Artifact

The digit `2` is encoded as `chr(24)` (`\x18`) throughout the PDF. `_normalize()` replaces `\x18` → `'2'` before any pattern matching. This affects verse references (`"1:\x182"` → `"1:2"`) and note content alike.

---

## Verse Reference Format

Prose pages use two spaces after the reference:

```
1:3  All things were created through Him…
```

Poetry pages (Psalms) use one space:

```
1:1 Blessed is the man who does not walk…
```

Regex `(\d{1,3}):(\d{1,3})\s+` handles both.

---

## Per-Column Verse Cursor Tracking

Two independent cursors track position within each column:

```
col_chapter[0], col_verse[0]  — left column  (x < 215)
col_chapter[1], col_verse[1]  — right column (x ≥ 215)
```

Note boxes use the cursor for their own column. This prevents right-column verse text (which may reference later verses) from corrupting the cursor used by left-column note boxes.

**Critical gate:** Only text boxes whose normalized text _starts_ with a verse reference update the cursor (`_VERSE_REF_RE.match(text.lstrip())`). Note continuation boxes and prose text with embedded cross-references (e.g., "cf. Ps 1:7") do not start with a verse ref and must not corrupt the column cursor.

**Sample-mode scope reset:** When a cursor advances to an out-of-scope chapter in sample mode, the cursor is immediately cleared to `None`. This prevents note boxes that follow from being attributed to in-scope chapters via a stale cursor.

---

## Note Box Structure

A note box contains one or more notes separated by `chr(4)` (`\x04`):

```
\xa0tn\xa0 Translator's note text\x04\xa0sn\xa0 Study note text\x04…
```

Each segment starts with: optional whitespace + `\xa0?(tn|tc|sn|map)[\xa0\s]+` + content.

Non-breaking spaces (`\xa0`) in content are converted to regular spaces after parsing.

Detection regex (`_IS_NOTE_RE`):
```
\x04\s*\xa0?(tn|tc|sn|map)\xa0  |  ^(tn|tc|sn|map)\xa0
```

---

## Note Family → Domain Slot Mapping

| PDF marker | Note type | `ChapterNotes` slot |
|---|---|---|
| `tn` | Translator's Note | `footnotes` |
| `tc` | Text-Critical Note | `variants` |
| `sn` | Study Note | `citations` |
| `map` | Map Note | `cross_references` |

---

## Domain Mapping

NET yields `ChapterNotes` objects (notes layer only — no canonical verse text).

Book names in the PDF title-map to Orthodox canonical names via `_NET_TITLE_TO_BOOK` (e.g. `"1 Samuel"` → `"I Kingdoms"`, `"1 Corinthians"` → `"I Corinthians"`).

---

## Known Gaps / Caveats

| Issue | Detail |
|---|---|
| Multi-box note truncation | Note content spanning more than one text box is truncated; only the first box (which always carries the substantive text) is captured. Continuations are silently dropped. Phase 1 limitation. |
| Book title exact match required | `_NET_TITLE_TO_BOOK.get(text)` requires the normalized text to match exactly. Boxes with trailing punctuation or mixed-font glyphs will be missed. Song of Songs appears in the PDF as "The Song of Songs" — both forms are in the mapping. |
| Section headings silently ignored | Title-Case prose boxes without a leading verse ref are discarded. This is correct behavior but means any section-level structure in the PDF is not preserved. |

---

## Sample Chapter Coverage

Chapters exercised by the current sample set in `extract_net.py` (aligned to the OSB sample envelope; deuterocanon excluded — NET is a Protestant translation):

| Chapter | Testament | Genre | Notes |
|---|---|---|---|
| Genesis 1 | OT | Torah | |
| Exodus 20 | OT | Torah | Ten Commandments |
| Leviticus 1 | OT | Torah / Priestly | |
| I Kingdoms 1 | OT | Historical | Mapped from NET "1 Samuel" |
| Psalms 1 | OT | Wisdom / Poetry | |
| Psalms 50 | OT | Wisdom / Poetry | Mapped from NET Psalm 51 (MT numbering) |
| Job 3 | OT | Wisdom / Drama | |
| Proverbs 8 | OT | Wisdom / Poetry | |
| Isaiah 7 | OT | Prophecy | |
| Song of Solomon 1 | OT | Wisdom / Poetry | Mapped from NET "Song of Songs" |
| Lamentations 1 | OT | Poetry / Acrostic | |
| Isaiah 7 | OT | Prophecy | |
| Isaiah 53 | OT | Prophecy | |
| Jeremiah 1 | OT | Prophecy | |
| Ezekiel 1 | OT | Prophecy / Vision | |
| Matthew 1 | NT | Gospel | |
| Matthew 5 | NT | Gospel | Beatitudes |
| John 1 | NT | Gospel / Prologue | |
| Acts 15 | NT | Narrative | Council of Jerusalem |
| Romans 8 | NT | Epistle | |
| I Corinthians 13 | NT | Epistle / Hymn | |
| James 1 | NT | Epistle | |
| Revelation 1 | NT | Apocalyptic | |

**Note:** NET does not contain deuterocanonical books (Sirach, I Maccabees, Tobit, Wisdom, etc.). "Song of Songs" and "1 Samuel" / "2 Samuel" / "1–2 Kings" are remapped to vault canonical names via `_NET_TITLE_TO_BOOK`. Psalms numbering follows MT (Psalm 51 = vault Psalm 50 in LXX/OSB numbering).

---

## Related Docs

| Doc | What it covers |
|---|---|
| `docs/osb-epub-source-structure.md` | OSB EPUB — full tag/class inventory, note file structure, known gaps |
| `docs/lexham-epub-source-structure.md` | Lexham LES EPUB — spine layout, anchor patterns, span taxonomy |
| `docs/eob-pdf-source-structure.md` | EOB NT PDF — page range, box classification, chapter heading patterns |
| `docs/implementation-architecture.md` | Ports & Adapters design, domain model, renderer contracts |
| `docs/source-roadmap.md` | Source status, phase roadmap, acquisition notes |
| `docs/validation-plan.md` | Validator rules, fixture strategy, test execution policy |
