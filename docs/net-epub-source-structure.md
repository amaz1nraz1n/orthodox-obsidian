# NET Bible 2.1 EPUB Source Structure

Audit of the NET Bible 2.1 EPUB source files and HTML structure.
Used to ensure `net_epub.py` handles all content correctly.
See also: `docs/osb-epub-source-structure.md`, `docs/lexham-epub-source-structure.md`, `docs/net-pdf-source-structure.md`, `docs/implementation-architecture.md`

- **Adapter:** `vault_builder/adapters/sources/net_epub.py`
- **Coverage:** Full Bible — canonical verse text AND translator's apparatus (notes)
- **Source file:** `source_files/Full Bible/NET Bible 2_1.epub`
- **Replaces:** `net_pdf.py` (NET Bible First Edition PDF adapter)

---

## File Layout

The EPUB contains paired chapter files. For each book:
- `fileN.xhtml` — book-level TOC page (chapter navigation table). This file's number is taken from the NCX.
- `fileN+1.xhtml` through `fileN+C.xhtml` — one text file per chapter (C = chapter count)
- `fileN+1_notes.xhtml` through `fileN+C_notes.xhtml` — corresponding notes files, each paired 1:1 with its text file

Total: ~2515 xhtml files (1 TOC + 2×chapters per book, across 39 Protestant books).

**Note:** Some duplicate notes files exist (e.g. `file1_notes.xhtml` duplicates `file51_notes.xhtml` for Genesis 50) — these are EPUB artifacts. Always use the file number derived from `TOC_file + chapter` for both text and notes.

---

## NCX-Based Book→File Mapping

The file `OEBPS/toc.ncx` lists each book's TOC file:
```xml
<navPoint id="file1040" playOrder="...">
  <navLabel><text>John</text></navLabel>
  <content src="file1040.xhtml"/>
</navPoint>
```

Key mappings from NCX:
| NCX Book Name | TOC file | Notes |
|---|---|---|
| Genesis | file1 | Chapters 1-50 → file2–file51 |
| Exodus | file52 | |
| Psalms | file497 | Psalm 1 (MT) → file498 |
| John | file1040 | John 1 → file1041 |
| Revelation | file1233 | |

**Chapter file number formula:** `TOC_file_num + chapter_number` (where chapter_number is the MT Psalm number for Psalms, since NET uses MT numbering).

---

## Text File Structure (`fileN.xhtml`)

```html
<h1>John<br />Chapter 1</h1>
<p class="paragraphtitle">The Prologue to the Gospel</p>
<p class="bodytext">
  <span class="verse">1:1</span> In the beginning<sup><a id="n430011" href="file1041_notes.xhtml#n430011">1</a></sup> was the Word...
  <span class="verse">1:2</span> The Word was with God.
</p>
```

**Psalm heading variant** (uses `<h2>` not `<h1>`, "Psalm" singular):
```html
<h2>Psalm 1</h2>
<p class="paragraphtitle"><b>Book 1 (Psalms 1-41)</b></p>
<p class="poetry"><span class="verse">1:1</span> How blessed...</p>
<p class="poetry">or stand in the pathway...</p>
```

### CSS Classes (text files)

| Class | Purpose |
|---|---|
| `bodytext` | Prose paragraph (may contain multiple verses) |
| `poetry` | Poetry stanza line (one `<p>` per line; verse span only at stanza start) |
| `bodyblock` | Block-quoted/indented prose (e.g. Matt 11:18-19); contains verse spans; must be included in verse extraction |
| `otpoetry` | OT quotation rendered in bold italic (e.g. Mark 1:3); contains verse spans; must be included in verse extraction |
| `psasuper` | Psalm superscription (e.g. "A psalm by Asaph.", "For the music director…"); appears between `paragraphtitle` and first verse in Psalms; not verse text |
| `paragraphtitle` | Section/pericope heading — skip for verse extraction |
| `verse` | `<span>` with verse reference in `C:V` format (e.g. `1:1`, `13:4`) |
| `smcaps` | Small-caps rendering of LORD — keep text content, strip tag |

### Verse Reference Format

`<span class="verse">C:V</span>` where `C` = chapter, `V` = verse number. Both are always the actual chapter's number (no cross-chapter spans within a chapter file).

### Note Reference Anchors (in text file)

```html
<sup><a id="n430011" href="file1041_notes.xhtml#n430011">1</a></sup>
```
- The `<sup>` wraps the `<a>` — decomposing `<sup>` removes the note ref
- The `id` attribute on `<a>` is used to link back from the notes file
- The visible number (e.g. `1`) is the sequential note number within the chapter
- **Planned:** preserve as `<sup class="nt-{type}">[[Book Ch — NET Notes#vN|{symbol}]]</sup>` using primary-type from notes file (see Note Type Distribution below)

---

## Notes File Structure (`fileN_notes.xhtml`)

```html
<h2>Notes for John 1</h2>
<p id="n430011"><a href="file1041.xhtml#n430011">1</a>
  <p><b>tn</b> The Logos concept in Hellenistic philosophy...</p>
  <p><b>sn</b> In the beginning. Parallels Genesis 1:1...</p>
</p>
```

Each `<p id="nXXX">` is one note entry. It can contain **multiple typed sub-notes** as nested `<p>` elements, each prefixed with a `<b>type</b>` bold marker.

### Note ID Pattern

`n{BB}{CCC}{N+}` where:
- `BB` = 2-digit book number (01=Genesis, 19=Psalms, 43=John, ...)
- `CCC` = 3-digit chapter number (001, 050, ...)
- `N+` = variable-length sequential note number within the chapter (1, 10, 100, ...)

Examples: `n010011` = Genesis ch.1 note 1; `n190011` = Psalms ch.1 note 1; `n430011` = John ch.1 note 1.

**Implementation note:** The adapter does NOT decode the note ID — it cross-references note IDs against the text file's `<a id="nXXX">` anchors to determine verse attribution.

### Note Type Distribution

Sampled across John 1 (126 entries), Romans 8 (43), Psalm 22 (74), Genesis 1 (64):

| Type combo | John 1 | Romans 8 | Psalm 22 | Gen 1 |
|---|---|---|---|---|
| `tn` only | 73 | 31 | 59 | 39 |
| `sn` only | 32 | 5 | 11 | 14 |
| `sn+tn` mixed | 14 | 1 | 2 | 10 |
| `tc` only | 5 | 5 | 2 | 1 |
| `tc+tn` mixed | 2 | 1 | 0 | 0 |

- `tn` is dominant (~60-70%); mixed entries are almost always `sn+tn` or `tc+tn` (never all three)
- `tc` notes are rare (~5%) but meaningfully distinct for readers
- **Primary-type precedence for inline markers: `tc > tn > sn`**
  - `sn+tn` → `*` (tn wins); `tc+tn` → `‡` (tc wins)
- The note type is only available in the notes file — text file `<sup>` carries a sequential number only. Requires two-pass: build `note_id → primary_type` from notes file first, then use when emitting markers into text companion.

### Note Type → Domain Slot Mapping

| Bold marker | Note type | `ChapterNotes` slot |
|---|---|---|
| `tn` | Translator's Note | `translator_notes` |
| `tc` | Text-Critical Note | `variants` |
| `sn` | Study Note | `footnotes` |

Note: `map` (Map Note) was documented in earlier versions of this doc but does not appear in the NET 2.1 EPUB (0 occurrences across all notes files). Removed.

### Note Content

Note content may contain HTML formatting (`<i>`, `<span class="hebrew">`, `<span class="translit">`) and Hebrew/Greek characters. The adapter strips all HTML tags and keeps plain text.

---

## Psalm Numbering

NET uses **MT (Masoretic Text) numbering**. The vault uses **LXX numbering** as primary.

Conversion when looking up file numbers:
- Vault canonical chapter number (LXX) → MT chapter number → file lookup
- Uses `LXX_TO_MT` from `vault_builder.domain.canon`
- Key range: LXX 10–112 → MT 11–113 (offset +1); LXX 1–8 identical; LXX 9 = MT 9

The returned `ChapterNotes` and `Chapter` objects always carry the **LXX chapter number** (the vault canonical form).

---

## Book Name Mapping

NCX uses Protestant book names. Mapping to vault canonical names:

| NCX Name | Vault Canonical |
|---|---|
| 1 Samuel | I Kingdoms |
| 2 Samuel | II Kingdoms |
| 1 Kings | III Kingdoms |
| 2 Kings | IV Kingdoms |
| 1 Chronicles | I Chronicles |
| 2 Chronicles | II Chronicles |
| Song of Solomon | Song of Solomon |
| 1 Corinthians | I Corinthians |
| ... | ... |

Full mapping defined in `_NET_EPUB_TITLE_TO_VAULT` in `net_epub.py`.

NET does not contain Deuterocanonical books. The adapter raises `KeyError` for any book not in its mapping.

---

## Verse Text Extraction Algorithm

1. Parse the chapter text file with BeautifulSoup
2. For each `<p class="bodytext">` or `<p class="poetry">`:
   - Decompose all `<sup>` elements (removes note reference anchors)
   - Replace each `<span class="verse">C:V</span>` with a sentinel marker `__VERSE_V__`
   - Collect paragraph text
3. Join all paragraph texts; split on sentinels
4. Result: `{verse_num: clean_text_string}`

Multiple poetry `<p>` elements for the same verse are naturally joined in step 3.

---

## Note→Verse Attribution Algorithm

1. Parse the chapter text file (without destroying `<sup>` elements)
2. Walk `<p class="bodytext">` and `<p class="poetry">` in document order
3. Track current verse via `<span class="verse">` markers
4. For each `<sup><a id="nXXX">`, record `{note_id: current_verse}`
5. Parse `<p id="nXXX">` entries in the notes file
6. Look up each note's verse from the map built in step 4
7. Notes with no verse mapping (e.g. psalm-level intro notes) are skipped

---

## Known Gaps / Caveats

| Issue | Detail |
|---|---|
| HTML content stripped | ~~Hebrew/Greek scripts, italics, and transliteration spans are reduced to plain text.~~ **Resolved:** `_html_to_markdown()` now converts `<i>` → `_text_`, `<b>` → `**text**`, and unwraps `greek`/`hebrew`/`translit` spans. |
| Psalm-level intro notes | ~~Skipped.~~ **Resolved:** `paragraphtitle` note anchors now mapped to verse 0; rendered under `### Introduction` heading with `ref_str = "intro"`. |
| Psalm superscription notes | ~~Skipped.~~ **Resolved:** `psasuper` note anchors now mapped to verse 0; rendered under `### Introduction` heading alongside paragraphtitle notes. |
| Psalm MT heading in pericope title | ~~"Psalm 51" appeared as pericope heading in Psalm 50 LXX companion.~~ **Resolved:** `_parse_chapter` suppresses bare `Psalm N` paragraphtitle entries. |
| No Deuterocanon | NET Bible is Protestant canon only. Any request for Deuterocanonical books raises `KeyError`. |
| Duplicate notes files | Some `_notes` files appear under two file numbers (EPUB artifact). Always use `TOC + chapter` formula for the authoritative notes file. |

---

## Sample Chapter Coverage

Same scope as existing `extract_net.py` sample set, plus now includes verse text output alongside notes.

---

## Related Docs

| Doc | What it covers |
|---|---|
| `docs/net-pdf-source-structure.md` | Old PDF adapter — superseded for new work |
| `docs/osb-epub-source-structure.md` | OSB EPUB — model for this doc's structure |
| `docs/lexham-epub-source-structure.md` | Lexham EPUB — another EPUB adapter reference |
| `docs/implementation-architecture.md` | Ports & Adapters design, domain model |
| `docs/source-roadmap.md` | Source status and phase roadmap |
