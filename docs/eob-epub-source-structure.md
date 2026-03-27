# EOB NT EPUB Source Structure

Audit of the Eastern/Greek Orthodox Bible NT EPUB source files.
Used to ensure `eob_epub.py` handles all content correctly.
See also: `docs/osb-epub-source-structure.md`, `docs/eob-pdf-source-structure.md`

Supersedes: `docs/eob-pdf-source-structure.md` for the NT extraction path.

---

## Source File

`source_files/New Testament/EOB NT.epub` (EOB-2 split format, ~925 KB)

- Author: Laurent Cleenewerck
- Title: *EOB: The Eastern Greek Orthodox New Testament Based on the Official Text of the Greek Orthodox Church (Patriarchal Text of 1904)*
- Year: 2015, ASIN B012EBN3MY

---

## EPUB File Layout

| File(s) | Category | Notes |
|---|---|---|
| `text/part0000_split_000.html` – `part0000_split_026.html` | Front matter / introductions | Prefatory essays, manuscript codes, Greek alphabet, Synoptic intro, John intro — no Bible text |
| `text/part0000_split_027.html` – `part0000_split_073.html` | NT Bible text | All 27 books; Revelation (all 22 chapters) is entirely in `split_073` |
| `text/part0000_split_074.html` – `part0000_split_123.html` | Appendices | 7 appendices (A–G) + Abbreviations — no Bible text; `split_074` opens with "APPENDIX A" |
| `text/part0000_split_124.html` – `part0000_split_127.html` | Endnotes | Footnote definitions referenced by inline `<a id="_ednrefN">` anchors |
| `content.opf` | Spine manifest | Defines reading order; `_get_spine()` reads this |
| `toc.ncx` | Navigation | Book-level only — no per-chapter nav points |

**Key structural fact:** The TOC NCX has only book-level nav points, not chapter-level. Chapter boundaries must be detected from content markers (see below).

---

## Book Heading Detection

```html
<h1 class="calibre9" id="calibre_pb_41">
  <a id="_Toc425418819"></a>
  <a id="_Toc425418671"></a>
  <a id="_Toc290636397">
    <span id="...">( ACCORDING TO ) MATTHEW</span>
  </a>
  <span class="calibre62">(ΚΑΤΑ ΜΑΤΘΑΙΟΝ)</span>
</h1>
```

- Every NT book opens with an `<h1>` containing the English title + Greek subtitle in `(…)`
- Gospel titles use the prefix "(ACCORDING TO) " which must be stripped
- **Parsing caveat**: The Greek parenthetical sometimes contains mixed Latin characters (e.g., the O in `ΚΟΛOΣΣΑΕΙΣ` is Latin U+004F, not Greek Omicron U+039F). Detection strips all parenthetical expressions first rather than filtering by Unicode range.

Detection in `_detect_book()`:
1. `re.sub(r"\([^)]*\)", " ", raw)` — remove all `(…)` parentheticals (strips Greek subtitle including any mixed Latin chars)
2. Collapse whitespace, uppercase
3. Strip `^ACCORDING TO\s+` prefix
4. Look up in `_EOB_TITLE_TO_BOOK`

**Appendix guard:** When an `<h1>` is encountered that does not match any NT book after collection has started, `current_book` is reset to `None`. This prevents appendix `<h1>` headings (e.g., "APPENDIX E: …", "ENDNOTES") from allowing content bleed into Revelation's last chapter.

---

## Chapter Marker Detection

```html
<p class="style38ptloweredby2ptlinespacingexactly2445pt">4</p>
```

There is **no single CSS class** for chapter number paragraphs. The following classes have all been observed:

| CSS class | Observed in |
|---|---|
| `style38ptloweredby2ptlinespacingexactly2445pt` | Matthew, Mark, Luke, John, Acts, Romans, Hebrews, … |
| `style375ptloweredby15ptlinespacingexactly2445pt` | Romans, 1 Corinthians, Galatians, … |
| `style345ptloweredby15ptlinespacingexactly2445pt` | Epistle books |
| `style35ptloweredby1ptlinespacingexactly2445pt` | Epistle books |
| `style365ptloweredby1ptlinespacingexactly2445pt` | Various |
| `style375ptbefore0ptloweredby7ptlinespacingexac` | Various (truncated class name) |
| `style37ptbefore0ptloweredby6ptlinespacingexactl` | Various (truncated class name) |
| `chapternumber` | 1 Corinthians 13 (at least) |
| `msonormal1` | Appendix tables (not Bible text) |

**Detection is content-based, not class-based:**

A `<p>` is treated as a chapter marker when:
1. `get_text(strip=True)` is a single integer in range 1–28
2. The paragraph has no `<sup class="calibre31">` descendants (distinguishes from verse paragraphs that open with a verse-number superscript)

This handles all CSS class variants and is robust to future class name drift.

---

## Verse Marker Structure

### Verse 1 — Implicit

There is no superscript for verse 1. Verse 1 is the text in the first `msonormal1` paragraph (and any following poetry paragraphs) after the chapter marker, up to the first `<sup class="calibre31">`.

```html
<p class="style38ptloweredby2ptlinespacingexactly2445pt">1</p>

<p class="msonormal1">The beginning of the Good News of Jesus Christ, the Son of
God. <sup class="calibre31">2</sup>As it is written in the prophets:…</p>
```

### Verses 2+ — Inline Superscript

```html
<sup class="calibre31">9</sup>We know [only] in part…
```

- Class `calibre31` is the verse-number marker
- Verse text follows the `<sup>` directly in the same paragraph (no wrapping `<span>`)

### Nested Span Wrappers

Some paragraphs wrap a block of verse text (including embedded `<sup>` markers) inside a `<span>`:

```html
<p class="msonormal1">
  <span class="calibre27">But as for prophecies, they will come to an end;
  as for tongues, they will cease; as for knowledge, it will pass away.
  <sup class="calibre31">9</sup>We know [only] in part, and we prophesy [only]
  in part; <sup class="calibre31">10</sup>but when that which is complete comes…
  </span>
</p>
```

**Critical:** Using `get_text()` on the `<span>` loses verse boundaries. The adapter uses recursive tree-walk (`_walk()`) to traverse all descendants in document order so `<sup>` markers inside nested spans are processed correctly.

---

## Paragraph Classes That Carry Verse Text

| CSS class | Tag | Status | Notes |
|---|---|---|---|
| `msonormal1` | `<p>` | ✅ handled | Primary prose verse paragraph; may contain multiple verses |
| `poetry1cxspfirst` | `<p>` | ✅ handled | First line of a poetry block |
| `poetry1cxspmiddle` | `<p>` | ✅ handled | Middle lines of a poetry block |
| `poetry1cxsplast` | `<p>` | ✅ handled | Last line of a poetry block |

Poetry paragraphs carry verse text as continuations of the current verse. They do not reset the verse counter — they append to whichever verse was active when the poetry block began.

---

## Paragraph Classes That Do NOT Carry Verse Text

| CSS class | Tag | Notes |
|---|---|---|
| `sectiontopic` | `<p>` | Pericope heading (e.g., "The ministry of John the Baptist") — skipped |
| `style38pt…` / `chapternumber` / etc. | `<p>` | Chapter number markers — handled separately |
| `msonormal` | `<p>` | Intro prose, table cells, appendix text — not a verse-text class |
| `msonormal15` | `<p>` | Endnote section spacers |
| `msoquote` | `<p>` | Block quotations in introductory/appendix sections |
| `colorfulgrid-accent*` | `<p>` | Comparison tables in appendices |
| `insidetable*` | `<p>` | Table cells in appendices/intros |
| `msonormal22` | `<p>` | Appears in `split_038` with text "55" — not a chapter marker (>28 range check excludes it); likely appendix-adjacent section numbering |

---

## Endnote Reference Structure

Inline within verse paragraphs:

```html
<a title="" href="part0000_split_125.html#_edn1003"
   class="pcalibre pcalibre1" id="_ednref1003">
  <span class="msoendnotereference">
    <span class="msoendnotereference">
      <span class="calibre28">[1003]</span>
    </span>
  </span>
</a>
```

- Identified by `id` attribute starting with `_ednref`
- Entire `<a>` element (including all children) is skipped during verse extraction
- Endnote definitions live in `part0000_split_124.html` – `part0000_split_127.html`
- Extracted via two-pass `read_notes()` — see Domain Model Mapping

---

## Inline Formatting

| Element | Status | Notes |
|---|---|---|
| `<sup class="calibre31">N</sup>` | ✅ verse marker | Advances verse counter; not added to text |
| `<a id="_ednrefN">…</a>` | ✅ stripped | Endnote reference; entire element skipped |
| `<span class="calibreN">` | ✅ text extracted | Styling only; text extracted via recursive walk |
| `<i class="calibreN">` | ✅ text extracted | Italics (used for titles, foreign terms) |
| `<b class="calibreN">` | ✅ text extracted | Bold emphasis |
| `{word}` | ✅ preserved as-is | EOB editorial markup for words implied in Greek but not in English — literal curly braces in source text, not a parser artifact |

---

## Known Quirks

### `{word}` curly-bracket notation

The EOB uses `{word}` in the translation to mark words that are implied in the Greek but not explicitly present. Example:

```
John 1:1 — "the Word was {what} God {was}"
```

These literal curly braces are in the EPUB source text. They are preserved in extracted verse text and will appear in output companions.

### Mark 1:3 — verse number absent

The OT quotation in Mark 1:3 ("The voice of one crying in the wilderness…") has no `<sup>3</sup>` marker. The EOB folded vv. 2–3 into a single verse block. Mark 1 will therefore have no v3; the text appears in v2. This is an editorial choice in the source, not a parsing error.

### Verse number inside nested `<span>` with non-standard styling

Some verse `<sup>` elements have their number wrapped inside an additional span for styling:

```html
<sup class="calibre31"><span class="calibre70">12</span></sup>
```

The `get_text(strip=True)` call on the `<sup>` correctly extracts "12" regardless.

---

## Domain Model Mapping

| Source structure | Extractor pass | Domain target | Status |
|---|---|---|---|
| `msonormal1` / `poetry1*` paragraphs after chapter marker | `read_text()` | `Book` → `Chapter` → `Verse` | ✅ implemented |
| `sectiontopic` paragraphs | `read_text()` | — | ✅ skipped (not in `_VERSE_P_CLASSES`) |
| Endnote `<a id="_ednrefN">` anchors | `read_text()` | — | ✅ stripped from verse text; **planned:** preserve as `<sup class="nt-fn">[[Book Ch — EOB Notes#vN|†]]</sup>` in EOB text companion (word-level nav marker, study/commentary type) |
| Endnote definition files (`split_124`–`split_127`) | `read_notes()` | `ChapterNotes.footnotes` | ✅ implemented — two-pass: `_walk()` records `ednref_num→(book,ch,verse)`; second pass parses `div[id^=edn]` definitions and yields `ChapterNotes` |
| Appendix content (`split_074`–`split_123`) | `read_text()` | — | ✅ guarded — collection stops at first non-NT `<h1>` (Appendix A at `split_074`) |

---

## Sample Chapter Coverage

Chapters exercised by the current sample set in `extract_eob.py` (aligned to the OSB NT sample envelope):

| Chapter | Genre | Verse count | Notes |
|---|---|---|---|
| Matthew 1 | Gospel / Genealogy | 25 | Genealogy block, verse 1 implicit |
| Matthew 5 | Gospel / Sermon | 48 | Beatitudes, poetry-adjacent prose |
| John 1 | Gospel / Prologue | 51 | `{what}` curly-bracket notation at v1 |
| Acts 15 | Narrative | 35 | Council of Jerusalem |
| Romans 8 | Epistle | 39 | `style375pt` chapter class variant |
| I Corinthians 13 | Epistle / Hymn | 13 | Nested `<span class="calibre27">` wrapping vv. 8–13 |
| James 1 | Epistle | 27 | |
| Revelation 1 | Apocalyptic | 20 | |

Additional chapters validated during initial development but not in the current sample set: Mark 1 (OT quotation / merged vv.2–3), Luke 1 (Magnificat / poetry blocks), Luke 24, John 3, Acts 1, Galatians 5, Ephesians 1, Philippians 4, Colossians 1 (mixed-Latin Greek heading), Hebrews 11, 1 Peter 1, 1 John 1.

---

## Nav Notes

- **NOAB RSV dead link**: `renderer.py`'s `_nav_callout()` always includes `[[Book Ch — NOAB RSV|RSV]]` (via `show_noab_rsv=True` default). Since NOAB status is `incomplete` and gated from full runs, this link will be a broken wikilink in production vault builds. This is a cross-cutting renderer issue, not EOB-specific. See renderer for fix.

---

## Known Gaps / TODO

| Priority | Gap | Notes |
|---|---|---|
| ✅ Resolved | Endnote layer (was P2) | Two-pass extraction implemented in `read_notes()`: first pass maps `_ednrefN → (book, ch, verse)`, second pass parses `div[id^=edn]` definitions in `split_124`–`split_127`. EOB Notes companions verified generating correctly. |
| P3 | `{word}` notation not transformed | Curly brackets pass through as-is; a future renderer pass could italicize or otherwise style implied words |
| P3 | Italic/bold formatting lost | `<i>` and `<b>` text is extracted as plain text — formatting is lost in the companion output |
| P3 | Poetry lines not distinguished from prose | Poetry paragraphs (`poetry1*`) are collected as verse text continuations without any Markdown line-break or indentation treatment |
