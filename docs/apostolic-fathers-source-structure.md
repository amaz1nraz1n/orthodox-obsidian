# Apostolic Fathers Source Structure

Audit of `source_files/Commentary/Apostolic Fathers/The Apostolic Fathers.epub`
(Holmes, *The Apostolic Fathers*, 3rd ed., Baker Academic, 2007 — 1.1 MB EPUB)

---

## EPUB Layout

37 HTML files (`text/part0000.html` – `text/part0036.html`).

| Files | Content |
|-------|---------|
| `part0000`–`part0006` | Title page, copyright, contents, prefaces, intro |
| `part0007`–`part0033` | Documents (Introduction + Translation pairs) |
| `part0034` | Index of Ancient Sources |
| `part0035` | Maps |
| `part0036` | Back Notes (scholarly endnotes for introductions — **not useful for extraction**) |

---

## Document Inventory

| Document | HTML file(s) | Chapters | Notes |
|----------|-------------|---------|-------|
| 1 Clement | `part0008.html` | 65 | Inline |
| 2 Clement | `part0010.html` | 20 | Inline |
| Ignatius — To the Ephesians | `part0012.html` | 21 | Inline |
| Ignatius — To the Magnesians | `part0013.html` | 15 | Inline |
| Ignatius — To the Trallians | `part0014.html` | 13 | Inline |
| Ignatius — To the Romans | `part0015.html` | 10 | Inline |
| Ignatius — To the Philadelphians | `part0016.html` | 11 | Inline |
| Ignatius — To the Smyrnaeans | `part0017.html` | 13 | Inline |
| Ignatius — To Polycarp | `part0018.html` | 8 | Inline |
| Polycarp — To the Philippians | `part0020.html` | 14 | Inline |
| Martyrdom of Polycarp | `part0022.html` | 22 | Inline |
| Didache | `part0024.html` | 16 | Inline |
| Epistle of Barnabas | `part0026.html` | 21 | Inline |
| Shepherd of Hermas (Vis/Com/Par) | `part0028.html` | ~120 | Inline |
| Epistle to Diognetus | `part0030.html` | 12 | Inline |
| Papias Fragments | `part0032.html`–`part0033.html` | ~6 frags | Inline |

---

## HTML Paragraph Classes

All translation files share the same class vocabulary:

| Class | Role |
|-------|------|
| `chapnum` | Book title heading — one per file |
| `centera` | Section heading (prose label, no verse content) |
| `noindent` | Address/salutation paragraph (no dropcap) |
| `noindent1` | Main text paragraph — dropcap = chapter number |
| `noindenta` | Inline footnote paragraph — follows the chapter it annotates |

---

## Chapter and Verse Markers

**Chapter number:** `<span class="dropcap">N</span>` is the **first** span inside a `<p class="noindent1">` paragraph. Its text content is the chapter number.

**Verse number:** `<span class="sup">N</span>` appears inline within a text paragraph. The implicit verse 1 is the text before the first `<sup>` in a chapter paragraph.

**Example (1 Clement 5):**
```html
<p class="noindent1">
  <span class="dropcap">5</span>
  But to pass from the examples of ancient times…
  <span class="sup">2</span> Peter, …
  <span class="sup">7</span> He traveled to the farthest limits of the west…
</p>
```
→ Chapter 5, verses 1 (implicit), 2, 7.

---

## Inline Footnotes

Footnote paragraphs appear as `<p class="noindenta">` (or sometimes `<p class="noindent1">` without a dropcap) directly after the chapter paragraph they annotate.

**Format:** `{chapter}.{verse} {keyword} {note text}`

```
1.1 brothers  Gk adelphoi, often rendered "dear friends" or "brothers and sisters"…
1.3 reverent  Some ancient authorities omit this word.
4.1–6  Gen. 4:3–8.  4.8  Cf. Gen. 27:41–28:5.
```

Notes contain:
- Textual variants (`Some ancient authorities…`)
- Translation alternatives
- Scripture cross-references (`Cf. Acts 20:35`, `Gen. 4:3–8`)
- Greek term glosses

The back notes section (`part0036.html`) is scholarly endnotes for the prefaces and introduction — **not** additional textual notes. Ignore for extraction purposes.

---

## Vault Modeling Decision

### Extraction model: standalone document companions

The Apostolic Fathers are not commentary ON Scripture — they are primary texts. They belong outside `Scripture/`, in `100-References/Apostolic Fathers/`.

**Proposed vault path:**
```
100-References/Apostolic Fathers/
  1 Clement/
    1 Clement 1.md      ← chapter hub with verse anchors
    1 Clement 2.md
    ...
  Ignatius — To the Ephesians/
    Ignatius — To the Ephesians 1.md
    ...
  Didache/
    Didache 1.md
    ...
```

**Each chapter file format** (mirrors Scripture hub format):
```markdown
---
cssclasses: [patristic-hub]
document: "1 Clement"
chapter: 1
---

###### 1.1
<span class="vn">1</span> Because of the sudden and repeated misfortunes… ^1-1

###### 1.2
<span class="vn">2</span> For who sojourned among you as a stranger… ^1-2
```

Block IDs use `^{chapter}-{verse}` to avoid collisions with Scripture block IDs.

**Notes:** The inline footnotes (`noindenta`) are dense enough to justify a companion notes file per chapter (`1 Clement 1 — Notes.md`) using the same callout pattern as OSB/Lexham notes.

**Scripture citations:** The notes contain extensive Scripture references in loose format (`Cf. Acts 20:35`, `Gen. 4:3–8`). A future linking pass could convert these to vault wikilinks `[[Acts 20#v35]]`, but this is NOT the first extraction goal.

### What to build first

1. **Phase 1**: Extract chapter text with verse anchors to `100-References/Apostolic Fathers/`
2. **Phase 2**: Extract inline footnotes as `— Notes.md` companions
3. **Phase 3** (optional): Scripture citation → wikilink conversion in footnotes

### Follow-on Source Plan

- **Didache (`PER-60`)**: compare the physical edition against the Holmes EPUB before expanding extraction. Keep one primary Didache output, use the other edition as comparison/reference material, and normalize Scripture links to the main hub / OSB verse anchors.
- **Shepherd of Hermas (`PER-61`)**: revisit the skipped material as a special-case structure. Extract the three internal books, `Visions`, `Mandates`, and `Similitudes`, as separate top-level units rather than forcing the flat chapter model used by the rest of the corpus.

### What to skip

- The introductions per document (scholarly, not primary text)
- The Index of Ancient Sources (`part0034.html`)
- The back notes section (`part0036.html`)
- Maps

---

## Parser Notes

- Parser target: the **translation** HTML file for each document (not the Introduction file)
- Chapter detection: `<p class="noindent1">` with a `<span class="dropcap">` child
- Verse detection: `<span class="sup">` children within chapter paragraphs; verse 1 is implicit
- Footnote detection: `<p class="noindenta">` paragraphs following a chapter paragraph; also `<p class="noindent1">` paragraphs that start with `X.Y ` (chapter.verse ref) but have no dropcap
- Section headings (`<p class="centera">`): skip text, keep as section context metadata
- Shepherd of Hermas: structured differently (Visions / Commandments / Parables as three "books" within one file); needs special handling for the book-level prefix
