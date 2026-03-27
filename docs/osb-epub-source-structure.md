# Orthodox Study Bible (OSB) EPUB Source Structure

Audit of all HTML tags and CSS classes in the Orthodox Study Bible EPUB source files.
Used to ensure `osb_epub.py` handles all content correctly.
See also: `docs/lexham-epub-source-structure.md`, `docs/eob-epub-source-structure.md`, `docs/eob-pdf-source-structure.md`, `docs/net-pdf-source-structure.md`

---

## Source File Categories

| File(s) | Category | Notes |
|---|---|---|
| Book/chapter HTML recognized by `HTML_BOOK_MAP` (87 files) | Scripture-bearing main files | Canonical verse text + inline gray-box study articles |
| Additional spine HTML outside `HTML_BOOK_MAP` | Front/back matter | Introductions, TOCs, prayers, indices, glossary, lectionary essays; scanned by the current extractor but ignored by verse/note class filters |
| `study1.html` – `study11.html` | Study notes | Per-verse footnotes (OSB commentary) |
| `variant.html` | Textual variants | 932 notes |
| `crossReference.html` | Cross-references | 355 notes |
| `x-liturgical.html` | Lectionary notes | 365 `footnotedef` + 4 `footnotepara`; **currently processed** into `ChapterNotes.liturgical` |
| `citation.html` | Patristic citations | 229 `footnotedef` + 1 `footnotepara`; **currently processed** into `ChapterNotes.citations` |
| `alternative.html` | Alternative readings | 5 notes — **ingested into `ChapterNotes.variants`** (no distinct model field; provenance folded) |
| `background.html` | Background notes | 2 notes — **ingested into `ChapterNotes.footnotes`** (no distinct model field; provenance folded) |
| `translation.html` | Translation notes | 4 notes — **ingested into `ChapterNotes.variants`** (no distinct model field; provenance folded) |

---

## Main Book HTML — Tag/Class Inventory

### Verse Text Containers (what we parse)

| Class | Tag | Status | Notes |
|---|---|---|---|
| `chapter1` | `<p>` | ✅ handled | Primary prose verse paragraph |
| `rindent` | `<p>` | ✅ handled | Continuation / indented verse paragraph |
| `psalm2` | `<p>` | ✅ handled | Psalm superscription verses (e.g., "A psalm of David") |
| `olstyle` | `<ol>` | ✅ handled | Multi-line verse container. Used for poetic books (Psalms, Sirach) **and** for poetic quotations embedded inside prose books (e.g. Isaiah/Zechariah quotations in John) |

### Inline Formatting Within Verse Text

| Tag / Class | Status | Notes |
|---|---|---|
| `<i>` | ⚠️ plain text only | OSB uses italics for words added for clarity not in original Greek/Hebrew. Currently extracted as plain text — formatting lost. |
| `<span class="chbeg">` | ✅ handled | Drop-cap initial letter; joined directly to continuation without space |
| `<span class="smallcaps">` | ✅ acceptable | Used for "LORD" (L + `<span>ORD</span>`). Plain-text extraction naturally produces "LORD" — no action needed |
| `<sup><a href="study…">†</a></sup>` | ✅ filtered | Footnote dagger marker — skipped via `find_parent(["a","sup"])` |
| `<sup><a href="crossReference…">a</a></sup>` | ✅ filtered | Cross-ref letter marker — same filter |
| `<sup><a href="x-liturgical…">ω</a></sup>` | ✅ filtered | Liturgical marker — same filter |
| `<b>` | ✅ not present | No bold in verse text paragraphs (confirmed by audit) |

### Verse Anchor Patterns

| Pattern | Location | Example |
|---|---|---|
| `id="{PREFIX}_vchap{ch}-1"` on `<span class="chbeg">` inside `<p class="chapter1">` | Prose books, verse 1 of each chapter | `<p class="chapter1"><span class="chbeg" id="John_vchap1-1"><a>1</a></span>text` |
| `id="{PREFIX}_vchap{ch}-{v}"` on `<sup>` (no class) inside `<p class="chapter1">` | Prose books, verse 2+ | `<sup id="John_vchap1-2"><a>2</a></sup>text` — inline within same `<p>` |
| `id="{PREFIX}_vchap{ch}-1"` on `<ol class="olstyle">` | Poetic books (Psalms verse 1 of each psalm) | Anchor on `<ol>` itself; verse text in `<li>` children |
| `id="{PREFIX}_vchap{ch}-{v}"` on `<sup>` inside `<ol>` | Poetic books (Psalms v2+) | `<li><sup id="Ps_vchap1-2">2</sup><span>text</span></li>` |
| `id="{PREFIX}_vchap{ch}-{v}"` on `<sup>` inside `<p class="psalm2">` | Psalm superscriptions | `<p class="psalm2"><sup id="Ps_vchap50-1">1</sup><i>title</i></p>` |

**Multi-verse paragraphs:** A single `<p class="chapter1">` frequently contains multiple verse anchors. Verses 2+ within the same paragraph use `<sup>` anchors inline in the text flow. The adapter correctly uses BS4 `find(id=…)` which is tag-agnostic and resolves anchors regardless of host element type.

### Section Headings and Non-Verse Content (NOT parsed as verse text)

| Class | Tag | Count | Content |
|---|---|---|---|
| `sub1` | `<p>` | 2852 | Section headings (e.g., "From Adam to Abraham") |
| `sub2` | `<p>` | 303 | Parallel passage references (e.g., "(Mt 3:1–6; Mk 1:1–6)") |
| `bookstarttxt` | `<p>` | 311 | Book introductions (author, date, themes) |
| `bookstarttxtind` | `<p>` | ~7 | Indented continuation paragraphs within book introductions; found in 1Kingdoms, 1Timothy, 2John, Philemon, Revelation |
| `title` | `<h1>`, `<p>` | ~2/book | Book title headings (e.g., "John", "The Book of John"); present in most/all book HTML files |
| `psalm` | `<p>` | 151 | Psalm navigation titles ("Psalm 1", "Psalm 2") |
| `center` | `<p>` | 82 | Centered headings |
| `bookstart` | `<p>` | 75 | Book title decorative text |
| `tx` | `<p>` | 395 | Inline study article body text (inside gray boxes) |
| `tx1` | `<p>` | 48 | Inline study article quoted text |
| `tx3` | `<p>` | 362 | Mostly front/back matter and lectionary essay content, not canonical verse text |
| `miniTOC` | `<p>`, `<span>` | 33633+ | Mini table-of-contents navigation |
| `Lev` | `<div>` | 76 | Book name / running header containers |

### Inline Study Articles (gray boxes)

| Class | Tag | Status | Notes |
|---|---|---|---|
| `div[style*="background-color: gray"]` | `<div>` | ✅ handled | Inline study article container |
| `ct` | `<p>` | ✅ handled | Article title (bold heading) |
| `tx`, `tx1` | `<p>` | ✅ handled | Article body text |
| `ext` | `<p>` | ⚠️ flattened | Quoted/excerpt paragraph inside article; currently rendered as ordinary body text, not a distinct blockquote/citation type |
| `ul2` | `<p>` | ⚠️ flattened | List-like article items; currently rendered as plain paragraphs |
| `sub1` | `<p>` | ⚠️ flattened | Article subheading text sometimes appears inside gray boxes and is currently treated as ordinary body text |

---

## Study Note Files — Tag/Class Inventory

### Note Container Variants

| Class | Tag | Count | Status | Notes |
|---|---|---|---|---|
| `footnotedef` | `<div>` | ~6290 in study files | ✅ handled | Standard per-verse footnote |
| `footnotedef` | `<div>` | 932 in variant.html | ✅ handled | Textual variant note |
| `footnotedef` | `<div>` | 355 in crossReference.html | ✅ handled | Cross-reference note |
| `footnotedef` | `<div>` | 365 in x-liturgical.html | ✅ handled | Lectionary reading notes (Pass E) |
| `footnotedef` | `<div>` | 229 in citation.html | ✅ handled | Patristic citation notes (Pass F) |
| `footnotedefpara` | `<div>` | 4 in study11.html | ✅ handled | Multi-paragraph footnote variant |
| `footnotepara` | `<div>` | 4 in x-liturgical + 1 in citation | ✅ handled | Multi-paragraph note |

### Note Structure (standard `footnotedef`)

```html
<div class="footnotedef">
  <a href="{book}.html#{anchor}">       <!-- backlink to verse (SKIP) -->
  <b>1:14</b>                            <!-- verse ref (chapter:verse) -->
  <span>note text with <b>bold</b></span>
  <span>continuation text</span>
</div>
```

### Note Structure (`footnotedefpara` — multi-paragraph)

```html
<div class="footnotedefpara">
  <a href="{book}.html#{anchor}">       <!-- backlink (SKIP) -->
  <b>5:12</b>
  <span>paragraph 1 text</span>
  <span>paragraph 2 text</span>
  …
</div>
```

### Kobo Segmentation Spans

All text content in the EPUB is wrapped in `<span id="kobo.N.N">` elements — Kobo e-reader segmentation markers. They are pervasive: inside verse paragraphs, `<li>` elements, `footnotedef` spans, headings, and everywhere else. Example from Gen 1:1 footnotedef:

```html
<b><span id="kobo.4.1">1:1</span></b>
<span id="kobo.4.2">\xa0\xa0\xa0 God the Father made heaven and earth.</span>
```

These are purely a reader artifact and carry no semantic meaning. `get_text()` strips them naturally; no adapter changes needed. Do not mistake them for structural markers.

### `\xa0\xa0\xa0` Whitespace Separator in Note Text

All `footnotedef` note body text begins with three non-breaking spaces (`\xa0\xa0\xa0`) between the bold verse ref and the note content. These must be stripped during text extraction. The adapter handles this.

### Inline Formatting in Notes

| Element | Status | Notes |
|---|---|---|
| `<b>` | ✅ handled | Renders as `**bold**` |
| `<i>` | ✅ handled | Renders as `*italic*` |
| `<br>` | ✅ handled | Renders as `\n\n` |
| `<span class="smallcaps">` | ✅ acceptable | "LORD" splits as L + `<span>ORD</span>` — plain text is fine |
| `<a href="{book}.html#anchor">` | ✅ handled | Converts to `[[Book Ch#vN|display]]` wikilink |

### Ref String Patterns in Notes

| Pattern | Example | Notes |
|---|---|---|
| `chapter:verse` | `1:14` | Standard single verse |
| `chapter:verse-verse` | `1:14-16` | Verse range (em/en/hyphen) |
| malformed / noisy refs | `1:24-3`, `.:1Pet.2:25" a`, `Prologue` | Present in auxiliary files; these are the main source of current regex/extractor edge cases |

---

## Verse Anchor Prefix → Book Mapping

See `PREFIX_TO_BOOK` dict in `vault_builder/adapters/sources/osb_epub.py`.

---

## Current Domain-Model Mapping

This is the current structural mapping from source HTML into the domain layer.

| Source structure | Extractor pass | Domain target | Current status |
|---|---|---|---|
| Verse containers in scripture-bearing book HTML (`chapter1`, `rindent`, `psalm2`, anchored `olstyle`) | `read_text()` | `Book` → `Chapter` → `Verse` | ✅ implemented |
| Gray-box inline study articles | Pass A | `ChapterNotes.articles` via `StudyArticle` | ✅ implemented |
| `study1.html` – `study11.html` footnotes | Pass B | `ChapterNotes.footnotes` via `StudyNote` | ✅ implemented |
| `variant.html` | Pass C | `ChapterNotes.variants` | ✅ implemented |
| `crossReference.html` | Pass D | `ChapterNotes.cross_references` | ✅ implemented |
| `x-liturgical.html` | Pass E | `ChapterNotes.liturgical` | ✅ implemented |
| `citation.html` | Pass F | `ChapterNotes.citations` | ✅ implemented |
| `alternative.html` | Pass G → `variants` | `ChapterNotes.variants` (provenance folded) | ✅ implemented — no distinct domain field by design |
| `background.html` | Pass H → `footnotes` | `ChapterNotes.footnotes` (provenance folded) | ✅ implemented — no distinct domain field by design |
| `translation.html` | Pass I → `variants` | `ChapterNotes.variants` (provenance folded) | ✅ implemented — no distinct domain field by design |

### Auxiliary Family Mapping Decision

The three small aux files are now ingested. By explicit decision, no new domain fields were added:

- `alternative.html` (alt readings like "Or *spirit*") → `variants`
- `background.html` (geographic/historical context) → `footnotes`
- `translation.html` (original-language notes like "Greek *anathema*") → `variants`

If provenance-aware rendering is needed in the future, options remain:
- add explicit `ChapterNotes.alternatives`, `.background`, `.translation_notes` lists
- add a generic keyed auxiliary-note collection with source provenance tags

### Source Taxonomy vs. Semantic Meaning

The OSB auxiliary files are not a perfect semantic taxonomy. The source file family is still important and should be preserved, but it is not always identical to the note's meaning.

- Example: `Romans 8:26a` comes from `variant.html` and is clearly a textual variant note.
- Example: `Romans 8:1a` comes from `crossReference.html` but its content is also variant-like: "NU-Text omits the rest of this verse."

This means future extraction should distinguish at least two layers:

- **source bucket**: where the note came from in the EPUB (`variants`, `cross_references`, `liturgical`, `citations`, `alternative`, `background`, `translation`)
- **semantic kind**: what the note functionally is in the vault (`textual_variant`, `cross_reference`, `lectionary`, `patristic_citation`, `background_note`, `translation_note`, etc.)

Preserve the OSB source bucket as provenance. Use semantic kind for rendering, callout/CSS treatment, and future normalized grouping.

---

## Known Gaps / TODO

| Priority | Gap | Files Affected |
|---|---|---|
| P2 | Italic markers lost in verse text (`<i>` → plain text) | All books (words added for clarity) |
| ~~P1~~ ✅ | `_REF_STR_PAT` cross-chapter collapse — **fixed**: when end < start, `verse_end` is cleared and original `ref_str` (e.g. `1:24-3`) is preserved for the callout body; renderer strips the range from the heading wikilink to avoid CMP004 | chiefly `x-liturgical.html` |
| P2 | OCR/noisy reference labels exist in auxiliary files and some study notes | `variant.html`, `translation.html`, `study11.html` |
| P3 | `alternative.html`, `background.html`, `translation.html` are ingested but provenance is folded into `variants`/`footnotes` — no distinct domain field or renderer callout distinction | ~11 notes total |
| P2 | OSB source buckets are not semantically pure; some notes in `crossReference.html` are variant-like and should not force a one-to-one renderer category decision | especially `variant.html` vs `crossReference.html` |
| P3 | Gray-box article subtypes (`ext`, `ul2`, internal `sub1`) are flattened rather than modeled distinctly | inline study articles in main book files |
| P3 | Extractor still iterates over all spine HTML, including non-scripture front/back matter, even though filters prevent most of it from contributing output | whole EPUB spine |

---

## Sample Chapter Coverage

Current sample set in `extract_osb.py`:

| Chapter | Genre | Covers |
|---|---|---|
| Genesis 1 | Torah / Narrative | Prose verse paragraphs, chapter opening |
| Psalms 1 | Wisdom / Poetry | `olstyle` poetic list, Psalms formatting |
| Psalms 50 | Wisdom / Poetry | `psalm2` superscription, poetic verses |
| Isaiah 53 | Prophecy | Prose verse paragraphs |
| Sirach 1 | Deuterocanon / Wisdom | `olstyle` poetic list |
| John 1 | NT / Gospel | Prose verse, cross-ref markers |
| Romans 8 | NT / Epistle | Prose verse, variants, cross-refs |
| Revelation 1 | NT / Apocalyptic | Prose verse |

### Planned Additions for Genre Coverage

| Chapter | Genre | Reason |
|---|---|---|
| Exodus 20 | Torah / Law | Ten Commandments — numbered list structure |
| Leviticus 1 | Torah / Priestly | Repetitive formulaic structure |
| Proverbs 8 | Wisdom / Poetry | Mixed prose/poetry |
| Job 3 | Wisdom / Drama | Long poetic speech |
| Song of Songs 1 | Wisdom / Poetry | Dialogue formatting |
| Lamentations 1 | Poetry / Acrostic | Structured poetry |
| Jeremiah 1 | Prophecy | Narrative + oracle mix |
| Ezekiel 1 | Prophecy / Vision | Complex imagery |
| I Maccabees 1 | Deuterocanon / Historical | Narrative prose |
| Matthew 5 | NT / Gospel | Beatitudes — poetic list structure |
| I Corinthians 13 | NT / Epistle | Mixed prose/poetry |
