# DBH NT — Source Structure

*David Bentley Hart, The New Testament: A Translation (Yale University Press, 2017/2023)*

## File Metadata

- **Path:** `source_files/New Testament/The New Testament_ A Translation -- David Bentley Hart.epub`
- **Format:** EPUB (Calibre-converted)
- **Testament:** NT only (27 books)
- **Total spine items:** 39 HTML files + titlepage.xhtml
- **Total footnotes:** 400 across the NT
- **Encoding:** UTF-8, polytonic Greek Unicode in footnotes (`<span class="greek">`)

## Spine Structure

| Spine file | Content |
|-----------|---------|
| `titlepage.xhtml` | Title page |
| `text/part0000.html` | Cover |
| `text/part0001.html` | Series title |
| `text/part0002.html` | Title page (interior) |
| `text/part0003.html` | Copyright |
| `text/part0004.html` | Dedication |
| `text/part0005.html` | Epigraph (Greek text) |
| `text/part0006.html` | Contents |
| `text/part0007.html` | Acknowledgments |
| `text/part0008.html` | A Note on Transliteration |
| `text/part0009.html` | **Introduction** ← extract to `100-References/DBH NT — Introduction.md` |
| `text/part0010.html` | Section divider ("THE NEW TESTAMENT") |
| `text/part0011.html` | Matthew (24 fn) |
| `text/part0012.html` | Mark (20 fn) |
| `text/part0013.html` | Luke (16 fn) |
| `text/part0014.html` | John (34 fn) |
| `text/part0015.html` | Acts (47 fn) |
| `text/part0016.html` | Romans (45 fn) |
| `text/part0017.html` | 1 Corinthians (31 fn) |
| `text/part0018.html` | 2 Corinthians (5 fn) |
| `text/part0019.html` | Galatians (15 fn) |
| `text/part0020.html` | Ephesians (3 fn) |
| `text/part0021.html` | Philippians (7 fn) |
| `text/part0022.html` | Colossians (7 fn) |
| `text/part0023.html` | 1 Thessalonians (4 fn) |
| `text/part0024.html` | 2 Thessalonians (4 fn) |
| `text/part0025.html` | 1 Timothy (8 fn) |
| `text/part0026.html` | 2 Timothy (2 fn) |
| `text/part0027.html` | Titus (3 fn) |
| `text/part0028.html` | Philemon (1 fn) — single-chapter, no `<h3>` heading |
| `text/part0029.html` | Hebrews (16 fn) |
| `text/part0030.html` | James (8 fn) |
| `text/part0031.html` | 1 Peter (9 fn) |
| `text/part0032.html` | 2 Peter (9 fn) |
| `text/part0033.html` | 1 John (13 fn) |
| `text/part0034.html` | 2 John (2 fn) — single-chapter |
| `text/part0035.html` | 3 John (0 fn) — single-chapter |
| `text/part0036.html` | Jude (12 fn) — single-chapter; Hart calls it "The Letter of Judas" |
| `text/part0037.html` | Revelation (55 fn) |
| `text/part0038.html` | **Postscript** ← extract to `100-References/DBH NT — Postscript.md` |

## Verse Marker Pattern

Verse numbers are inline `<span class="superscript">` within `<p class="indent">` paragraphs. Multiple verses share a paragraph — Hart uses literary paragraphing, not verse-per-line layout.

```html
<p class="indent">
  <span class="superscript">1</span>In the origin there was the Logos, and the Logos was present with G<span class="smallcaps">OD</span>,<span class="superscript"><a id="footnote-339-backlink" href="part0014.html#footnote-339" class="calibre6">a</a></span> and the Logos was god;
  <span class="superscript">2</span>This one was present with G<span class="smallcaps">OD</span> in the origin.
  ...
</p>
```

**Parsing approach:** Split each `<p class="indent">` at `<span class="superscript">` markers. Collect text from verse N's marker up to (but not including) verse N+1's marker. Strip footnote anchor elements from the verse text body; record footnote letter + target ID for the notes companion.

## Chapter Heading Pattern

```html
<h3 class="h2"><span class="smallcaps1">CHAPTER ONE</span></h3>
```

Chapter names are spelled out in full ("CHAPTER ONE", "CHAPTER TWO", ..., "CHAPTER TWENTY-ONE"). Parse by position in spine order, not by text parsing.

## Book Heading Pattern

Multi-chapter books:
```html
<h2 class="h1" id="ch04">The Gospel According to John</h2>
```

Single-chapter books (Philemon, 2 John, 3 John, Jude):
```html
<h2 class="h2a" id="ch18">The Letter to Philemon</h2>
```

`class="h2a"` signals single-chapter books — no `<h3>` chapter heading follows. Treat as implicit chapter 1.

## Pericope / Section Headings

**None.** No pericope or section headings exist within chapters. The only structural elements below the book level are chapter headings (`<h3>`). The `<h4 class="h3">Notes</h4>` heading marks the footnote section at the bottom of each book file.

## Footnote Pattern

**Inline marker** (in verse text):
```html
<span class="superscript"><a id="footnote-339-backlink" href="part0014.html#footnote-339" class="calibre6">a</a></span>
```

**Definition** (at bottom of same HTML file):
```html
<p class="notes" id="footnote-339">
  <a class="calibre4" href="part0014.html#footnote-339-backlink">a</a>.
  [footnote text with optional <span class="greek">ὁ θεός</span> and <em class="calibre5">italic</em>]
</p>
```

- Letter-indexed (a, b, c…) per book file, resetting at each book
- IDs count **downward** within each file (first footnote in file has highest ID number)
- Footnotes are self-contained per book file — no cross-file footnote references
- Content: translator rationale, Greek word studies, theological commentary → `NoteType.TRANSLATOR`

## Special Typography

### GOD / god distinction

Hart marks the Greek article distinction typographically:

| Rendering | HTML | Greek | Meaning |
|-----------|------|-------|---------|
| `G`**od** (small caps OD) | `G<span class="smallcaps">OD</span>` | ὁ θεός (with article) | God the Father in fullest sense |
| `god` (lowercase) | plain text | θεός (without article) | divine predicate, articular ambiguity |

**Vault rendering: plain `GOD` / `god`.** Preserves Hart's theological distinction without requiring CSS.

### Greek spans

`<span class="greek">ὁ θεός</span>` — appears in footnotes only, not in main verse text. Preserve as-is (UTF-8 polytonic Unicode).

### Smallcaps in chapter headings

`<span class="smallcaps1">CHAPTER ONE</span>` — structural marker only; render as plain text chapter number.

### Italics in footnotes

`<em class="calibre5">word</em>` — transliteration of Greek terms. Preserve as Markdown `*word*`.

### Hart's non-standard bylines

These appear between book heading and first chapter heading as plain paragraphs (e.g., "BY PAUL", "ATTRIBUTED TO PAUL", "AUTHOR UNKNOWN"). Strip from verse extraction; preserve in structure doc only.

## Hart's Non-Standard Book Names

Vault file naming uses canonical vault names, not Hart's:

| Hart's name | Vault name |
|-------------|-----------|
| The First Letter to the Thessalonikans | 1 Thessalonians |
| The Second Letter to the Thessalonikans | 2 Thessalonians |
| The Letter of Judas | Jude |
| The Letter to the Hebrews | Hebrews |
| The Acts of the Apostles | Acts |

Hart's exact titles should be preserved in frontmatter (`source_title:` field) but do not affect file naming.

## Output Plan

### Text companions
- Pattern: `{Book} {Ch} — DBH.md`
- Vault slot: Mode 2 NT (second NT comparison text, alongside EOB)
- Hub nav label: `DBH`
- Frontmatter: `hub`, `source: "DBH"`, `layer_type: text`, `book`, `chapter`

### Notes companions
- Pattern: `{Book} {Ch} — DBH Notes.md`
- Content: NoteType.TRANSLATOR footnotes (400 total across NT)
- Same pattern as EOB Notes — per-verse sections linking back to hub verse anchors

### Reference extractions
- `100-References/DBH NT — Introduction.md` — Hart's translation philosophy (part0009)
- `100-References/DBH NT — Postscript.md` — Note on John's prologue + irregular glossary (part0038)

## Example Verse Output (Raw)

**Matthew 1:1**
> The record of the lineage of Jesus the Anointed, son of David, son of Abraham:

**John 1:1** (with footnote marker `a`)
> In the origin there was the Logos, and the Logos was present with GOD,^a and the Logos was god;

**John 3:16**
> For God so loved the cosmos as to give the Son, the only one, so that everyone having faith in him might not perish, but have the life of the Age.

## Known Characteristics

- **No verse IDs in HTML** — verse identity is derived solely from inline `<span class="superscript">` position within paragraphs. Parser must walk the paragraph node tree to split verses.
- **Paragraph groupings are literary** — Hart groups verses into prose paragraphs. A single `<p class="indent">` may span an entire pericope (e.g., John 1:1–18 is one paragraph, John 3:1–21 is one paragraph).
- **Footnote IDs count downward** — ID numbers decrease as you read forward in each file. This is a Calibre artifact; do not rely on numeric ordering for footnote sequencing. Use DOM order instead.
- **Heavy footnote density in theology-dense books** — Romans (45), Revelation (55), John (34), Acts (47) carry the most notes. Galatians (15), Hebrews (16), Jude (12) are also significant.
- **Single-chapter books** lack `<h3>` chapter headings; identified by `class="h2a"` on the book `<h2>`.
