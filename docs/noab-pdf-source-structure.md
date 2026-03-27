# New Oxford Annotated Bible (NOAB) RSV PDF Source Structure

Structural notes for `vault_builder/adapters/sources/noab_pdf.py`.
See also: `docs/osb-epub-source-structure.md`, `docs/net-epub-source-structure.md`

---

## PDF Metadata

| Property | Value |
|---|---|
| File | `New Oxford Annotated Bible with Apocrypha RSV.pdf` |
| Pages | ~2032 |
| Layout | Two-column, ~367×600 pt pages |
| Column split | x ≈ page_width / 2 (~183 pt) |
| Text extraction | `pdfplumber` (`Page.extract_words` + font metadata) |

---

## Page Box Classification (by font size and position)

| Class | Font size | y_top | Other conditions | Notes |
|---|---|---|---|---|
| `page_num` | > 10.0 pt | any | — | Page numbers in brackets like `[2]` |
| `superscript` | < 6.0 pt | any | — | Inline variant footnote markers (e.g. `b Or wind`) |
| `footnote` | < 8.0 pt | any | — | Footnotes / annotations at page bottom |
| `header` | 8.0–10.5 pt | > 560 | matches `_HEADER_PAT` or `_HEADER_PREFIX_PAT` | Running chapter headers |
| `pericope` | < 8.7 pt | any | text < 70 chars | Pericope / section headings |
| `verse` | ~9.0–9.7 pt | any | (fallthrough) | Canonical verse text |

---

## Running Chapter Headers

### Formats observed

| Format | Example | Notes |
|---|---|---|
| `BOOK N` | `GENESIS 1` | Standard format for most books |
| `1 BOOK N` | `1 CORINTHIANS 13` | NOAB uses Arabic digits, not Roman numerals, for numbered books |
| `PSALM N` | `PSALM 8` | Singular form for full-page Psalms |
| `PSALMS N, M` | `PSALMS 2, 3` | Multiple Psalms on one page |
| `BOOK N, M` | `1 CORINTHIANS 5, 6` | Two chapters sharing a page (rare outside Psalms) |
| Header merged with verse | `JOHN 6 receive. 44 How can...` | Left-column header runs into continuation verse text |

### Header detection regex

```
_HEADER_PAT        = r"^([A-Z0-9][A-Z0-9\s]+?)\s+([\d]+(?:\s*,\s*[\d]+)*)$"
_HEADER_PREFIX_PAT = r"^([A-Z0-9][A-Z0-9\s]+?)\s+([\d]+(?:\s*,\s*[\d]+)*)\s+"
```

- `_HEADER_PAT` matches standalone boxes (no trailing verse text).
- `_HEADER_PREFIX_PAT` matches merged boxes; the header prefix is stripped and the
  remaining text is stored as verse content.

### Book name mapping

NOAB running headers use Arabic digit prefixes for numbered books:

| PDF header | Vault canonical name |
|---|---|
| `1 SAMUEL` / `I SAMUEL` | `I Kingdoms` |
| `2 SAMUEL` / `II SAMUEL` | `II Kingdoms` |
| `1 KINGS` / `I KINGS` | `III Kingdoms` |
| `2 KINGS` / `II KINGS` | `IV Kingdoms` |
| `1 CHRONICLES` | `I Chronicles` |
| `1 CORINTHIANS` | `I Corinthians` |
| `2 CORINTHIANS` | `II Corinthians` |
| `1 THESSALONIANS` | `I Thessalonians` |
| `1 TIMOTHY` | `I Timothy` |
| `1 PETER` | `I Peter` |
| `1 JOHN` / `2 JOHN` / `3 JOHN` | `I John` / `II John` / `III John` |
| `PSALM` (singular) | `Psalms` |
| `PSALMS` (plural) | `Psalms` |

---

## Chapter-to-Page Index Strategy

Running headers appear on pages where a chapter **continues** (not on the chapter's
first page). The adapter infers the start page via:

```
chapter_pages = [first_header_page - 1] + [all header pages]
```

### Gap-fill for short chapters

Chapters short enough to fit on a single page (e.g. Isaiah 53, Matthew 1, Revelation 1)
never get a running header. After the main scan, `_fill_chapter_gaps()` infers their
pages from adjacent detected chapters:

- **Missing chapter N** between detected N-1 and N+1: pages = last page of (N-1) ∪ first page of (N+1).
- **Missing chapter 1**: pages = first page of chapter 2's range (the prepended start page).

---

## ⚠ Extraction Quality Status (2026-03-23)

**This source is not ready for full runs.** The adapter exists and sample output has been generated, but extraction quality has known failures that must be resolved before NOAB RSV is included in a complete vault build.

| Issue | Severity | Status |
|-------|----------|--------|
| OCR artifacts in verse text (stray characters, merged words) | High | Open |
| Multi-verse merging (genealogies, poetry stanzas collapsed into one block) | High | Open |
| GlyphLessFont encoding: verse numbers render as non-digit chars, silently drop verse boundaries | High | Open — see § GlyphLessFont below |
| Psalms: verse contamination from adjacent short Psalms on shared pages | High | Open — Psalms excluded from sample |
| RSV Notes companion: desirable, but blocked on text stability and note anchoring | Medium | Deferred |

**Gate for full-run inclusion:** clean per-verse text with no merge artifacts and ≥ 95% verse boundary detection across representative sample chapters (Torah, Psalm, Gospel, Epistle).

---

## Psalms — Known Limitation

The NOAB PDF often places multiple short Psalms on a single page (e.g. `PSALMS 2, 3`).
Because each Psalm (chapter) shares the same page as adjacent Psalms, verse text from
adjacent Psalms contaminates the verse stream when parsing.

**Current behavior**: Psalms chapters are indexed, but verse contamination means the
extracted text may mix content from adjacent Psalms. **Psalms are excluded from the
default `extract_noab.py` sample.** A dedicated Psalter source (Rahlfs LXX, Brenton)
should be preferred for Psalms.

---

## GlyphLessFont Encoding

Some fonts in this PDF use `GlyphLessFont`, which maps certain glyphs to non-digit
Unicode characters. Verse numbers extracted from these pages may render as non-digit
strings (e.g. verse 10 → `1°`, verse 22 → `7?`). The `parse_verse_stream` regex
`\b(\d{1,3})\s+` cannot match these, so those verse boundaries are silently dropped.

**Effect**: Genesis 1 typically yields 15–20 detected verses out of 31. Tests assert
`>= 10` rather than the canonical total.

---

## Annotation Layers / Note Families (audit 2026-03-25)

Raw PDF inspection confirms that NOAB carries **two distinct annotation layers**. They should not be conflated during extraction.

| Layer | Marker / key form | Placement | Typical content | Planned `ChapterNotes` mapping |
|---|---|---|---|---|
| Inline apparatus | Parenthesized superscript letters such as `(a)` in verse text | Tiny-font blocks at page bottom | Alternative renderings, manuscript / omission notes, short translation clarifications | `alternatives`, `variants`, or `translator_notes`, depending on note body |
| Study notes | Verse or pericope keys such as `1.1-18`, `15.16-47`, `7.53-8.11` | Larger bottom-page commentary blocks beneath the text columns | Pericope commentary, historical framing, interpretive discussion | `footnotes` by default; `background_notes` when the content is clearly contextual / historical |

### Confirmed raw examples

- John 1 uses a parenthesized superscript marker in the verse text: `In him was life,(a)`.
- John apparatus note example: `Or was not anything made. That which has been made was life in him`.
- John study-note example: `1.1-18: The Prologue...`
- Later NT pages show manuscript / omission notes such as `The most ancient authorities omit 7.53-8.11...`

### Extraction implications

- Apparatus notes and study notes are both page-local. They cannot be recovered reliably from one chapter-wide concatenated text stream.
- The verse-text parser must suppress bottom-page note blocks before verse assembly; otherwise note prose bleeds into canonical text.
- A future NOAB notes layer should be emitted as its own companion file, `{Book} {Ch} — NOAB RSV Notes.md`, parallel to Lexham / EOB / NET notes companions.
- That notes layer should stay deferred until the text layer has trustworthy verse anchors and chapter locality.

---

## Verse Parsing

```
parse_verse_stream(text) -> {verse_num: clean_text}
```

1. Rejoin hyphenated line-breaks: `r"-\s*\n\s*"` → `""`
2. Normalize whitespace: `r"\s+"` → `" "`
3. Split on verse markers: `r"\b(\d{1,3})\s+"` — produces (number, text) pairs
4. Pre-number text → verse 1 (if non-empty)
5. Double-spaces and leading verse-number artifacts cleaned automatically by step 2

---

## Reading Order

Within each page, text boxes are sorted:
1. Left column first (x < page_width / 2), top-to-bottom (descending y_top)
2. Right column second, top-to-bottom

---

## Visual layout confirmations (screenshots + user verification, 2026-03-26)

- **Reading order is truly column-major.** The left text column is read fully before the right text column on the same page.
- **Every book has an intro section.** Intro prose sits above the Scripture text region and should never be assigned to chapter verse text.
- **Horizontal separator rules matter.** Scripture text and bottom-page notes are visually separated by full-width horizontal rules. The upper rule is a strong practical boundary between intro/front matter and canonical text; the lower rule is a strong boundary between canonical text and annotation blocks.
- **Book openings do not show a verse-1 marker.** The first verse of a book begins with a stylized decorative initial and no explicit `1` marker. Example: Genesis begins with a large stylized `I` in `IN THE BEGINNING`.
- **Chapter openings also omit verse-1 markers.** New chapters begin with a large stylized chapter number (for example the Genesis 2 opener), followed by verse text with no explicit `1` marker.
- **The stylized chapter number may extract badly.** User verification confirms the Genesis 2 opener can paste as `Z`, which aligns with observed extraction artifacts where the large opener is misread rather than recognized as a normal digit.
- **Main-text page numbering differs from front matter.** First canonical text pages use bracketed Arabic page numbers like `[1]`, while intro / front matter pages use bracketed Roman numerals. This is a useful additional signal when distinguishing front matter from book text starts.

---

## Source Accuracy Notes

- RSV text, suitable for comparison alongside OSB (also RSV-based).
- Academic study Bible: footnote and pericope density is high.
- Not suitable for liturgical use (uses MT numbering for Psalms, Protestant chapter
  order for some books).
- Deuterocanonical books present (NOAB Expanded Edition).

---

## Recommended Staged Plan

1. **Stabilize the text layer first.**
   - Strengthen NOAB verification beyond `>= 10` verses.
   - Add checks for impossible verse jumps, cross-chapter contamination, and representative chapter-shape sanity.
2. **Refine bounded verse recovery.**
   - Parse chapter pages with stronger suppression of note blocks, headers, and page furniture before verse assembly.
   - Enforce monotonic verse progression and reject outlier verse numbers beyond canonical chapter maxima.
3. **Then implement note extraction.**
   - Add a `read_notes()` path for NOAB once verse anchors are trustworthy.
   - Map inline apparatus and study-note families into normalized `ChapterNotes` slots.
4. **Only then expose `NOAB RSV Notes` in nav.**
   - The planned notes companion is a good fit for the architecture, but it should remain gated until the source clears the text-quality bar.

### Current extraction findings (2026-03-26)

- **Targeted marker OCR is better than page-wide OCR.** Narrow token crops and short line-context crops recover corrupted verse markers more reliably than a full-page OCR overlay. Representative observed recoveries on Genesis boundary pages include `1° -> 15`, `1® -> 16`, `*1 -> 21`, `3° -> 30`, `7? -> 22`, and `73 -> 23`.
- **Line-aware parsing is materially better than flattened page streams.** Parsing ordered body lines directly, with bounded sequence-aware marker repair, is what finally recovered Genesis 1 verses `3`, `4`, `7`, `8`, and `26` instead of losing them to `364`, `*`, and `3` OCR artifacts.
- **Genesis 1 is now a real exact-count regression, not just a target.** The current adapter can recover all 31 verses of Genesis 1 and suppress the earlier bogus `v73` jump.
- **Shared-page chapter starts are still the next blocker.** Genesis 2 now starts in the right place, but it still misses internal verse markers. John 1 and Romans 8 also still show the same broader family of problem: unnumbered verse-1 starts on shared pages remain harder than numbered verse boundaries.
- **Current practical bar:** NOAB is improved enough to justify stricter regression coverage and further chapter-start work, but it is still not good enough for source promotion, validator cleanup, or notes-companion work.
