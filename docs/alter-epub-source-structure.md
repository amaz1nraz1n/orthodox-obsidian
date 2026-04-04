# Robert Alter — The Hebrew Bible: Source Structure

**Source key**: `alter`
**File**: `./source_files/Old Testament /The Hebrew Bible -- Robert Alter.epub`
**Format**: EPUB (EPUB 3)
**Size**: 31.7 MB
**Spine items**: 1011
**OPF**: `OEBPS/content.opf`
**Testament**: OT — MT canon only (39 books; no Deuterocanonical books)

---

## Canon Coverage

Covers the 39-book Masoretic Text canon. **Deuterocanonical books are absent** (Tobit, Judith, 1–4 Maccabees, Wisdom of Solomon, Sirach, Baruch, 1 Esdras, Prayer of Manasseh). This is a known limitation for Orthodox use. Alter is a Mode 3 literary comparison layer for MT books only; OSB remains the full-canon Mode 1 source.

---

## Volume / Book Structure

The EPUB is a combined 3-volume edition. Books are organized by Volume → Part → Chapter.

### Volume 1 — Torah

| Part | Book     | Chapter file pattern          | Chapter count |
|------|----------|-------------------------------|---------------|
| Pt1  | Genesis  | `Vol1_Pt1Chapter{NN}.xhtml`  | 50            |
| Pt2  | Exodus   | `Vol1_Pt2Chapter{NN}.xhtml`  | 40            |
| Pt3  | Leviticus| `Vol1_Pt3Chapter{NN}.xhtml`  | 27            |
| Pt4  | Numbers  | `Vol1_Pt4Chapter{NN}.xhtml`  | 36            |
| Pt5  | Deuteronomy | `Vol1_Pt5Chapter{NN}.xhtml` | 34           |

### Volume 2 — Prophets

| Part  | Book       | Chapter file pattern               | Chapter count |
|-------|------------|------------------------------------|---------------|
| Pt1   | Joshua     | `Vol2_Pt1Chapter{NN}.xhtml`       | 24            |
| Pt2   | Judges     | `Vol2_Pt2Chapter{NN}.xhtml`       | 21            |
| Pt3   | 1 Samuel   | `Vol2_Pt3Chapter{NN}.xhtml`       | 31            |
| Pt3a  | 2 Samuel   | `Vol2_Pt3aChapter{NN}.xhtml`      | 24            |
| Pt4   | 1 Kings    | `Vol2_Pt4Chapter{NN}.xhtml`       | 22            |
| Pt4a  | 2 Kings    | `Vol2_Pt4aChapter{NN}.xhtml`      | 25            |
| Pt5   | Isaiah     | `Vol2_Pt5Chapter{NN}.xhtml`       | 66            |
| Pt6   | Jeremiah   | `Vol2_Pt6Chapter{NN}.xhtml`       | 52            |
| Pt7   | Ezekiel    | `Vol2_Pt7Chapter{NN}.xhtml`       | 48            |
| Pt8a  | Hosea      | `Vol2_Pt8aChapter{NN}.xhtml`      | 14            |
| Pt8b  | Joel       | `Vol2_Pt8bChapter{NN}.xhtml`      | 4             |
| Pt8c  | Amos       | `Vol2_Pt8cChapter{NN}.xhtml`      | 9             |
| Pt8d  | Obadiah    | `Vol2_Pt8dChapter01.xhtml`        | 1             |
| Pt9a  | Jonah      | `Vol2_Pt9aChapter{NN}.xhtml`      | 4             |
| Pt9b  | Micah      | `Vol2_Pt9bChapter{NN}.xhtml`      | 7             |
| Pt9c  | Nahum      | `Vol2_Pt9cChapter{NN}.xhtml`      | 3             |
| Pt9d  | Habakkuk   | `Vol2_Pt9dChapter{NN}.xhtml`      | 3             |
| Pt9e  | Zephaniah  | `Vol2_Pt9eChapter{NN}.xhtml`      | 3             |
| Pt9f  | Haggai     | `Vol2_Pt9fChapter{NN}.xhtml`      | 2             |
| Pt9g  | Zechariah  | `Vol2_Pt9gChapter{NN}.xhtml`      | 14            |
| Pt9h  | Malachi    | `Vol2_Pt9hChapter{NN}.xhtml`      | 3             |

### Volume 3 — Writings

| Part  | Book                  | Chapter file pattern                        | Notes                        |
|-------|-----------------------|---------------------------------------------|------------------------------|
| Pt1   | Psalms                | `Vol3_Psalm_{N}.xhtml`                      | One file per Psalm (150 files) |
| Pt2   | Proverbs              | `Vol3_Pt2_Chapter_{N}.xhtml`               |                              |
| Pt3   | Job                   | `Vol3_Pt3_Chapter_{N}.xhtml`               |                              |
| Pt4   | Song of Songs         | `Vol3_Pt4_Chapter_{N}.xhtml`               |                              |
| Pt5   | Ruth                  | `Vol3_Pt5_Chapter_{N}.xhtml`               |                              |
| Pt6   | Lamentations          | `Vol3_Pt6_Chapter_{N}.xhtml`               |                              |
| Pt7   | Qohelet (Ecclesiastes)| `Vol3_Pt7_Chapter_{N}.xhtml`               |                              |
| Pt8   | Esther                | `Vol3_Pt8_Chapter_{N}.xhtml`               |                              |
| Pt9   | Daniel                | `Vol3_Pt9_Chapter_{N}.xhtml`               |                              |
| Pt10  | Ezra                  | `Vol3_Pt10_Ezra_ch{N}.xhtml`               | Ezra/Nehemiah split by name  |
| Pt10  | Nehemiah              | `Vol3_Pt10_Nehemiah_ch{N}.xhtml`           | Ezra/Nehemiah split by name  |
| Pt11  | 1 Chronicles          | `Vol3_Pt11_Chronicles1_ch{N}.xhtml`        |                              |
| Pt11  | 2 Chronicles          | `Vol3_Pt11_Chronicles2_ch{N}.xhtml`        |                              |

---

## Book Boundary Detection

Book boundaries are signaled by `<h2 class="ct">` (chapter title = book name) appearing in the first chapter file of each book. Chapter numbers within a book use `<h2 class="cn">` or `<h2 class="cn1">`.

```html
<!-- Book title (first chapter file of each book) -->
<h2 class="ct" id="pt3ch1">
  <a href="Vol2_Contents.xhtml#rpt3ch1">
    <span class="black">1 Samuel</span>
  </a>
</h2>

<!-- Chapter number (every chapter file) -->
<h2 class="cn" id="rpt1ch1">CHAPTER 1</h2>
```

The `<h2 class="ct">` appears only in the first chapter file of a book; subsequent chapters have `<h2 class="cn">` only.

---

## Verse Marker Patterns

### Prose books (Torah, Prophets, Writings)

Verse numbers are bare `<sup>` inline within prose paragraphs. **Multiple verses share one paragraph** (literary flow — Alter does not break paragraphs at verse boundaries).

```html
<!-- Verse without footnote — bare <sup> -->
<sup>3</sup>God said, "Let there be light." And there was light.

<!-- Verse with footnote — superscript wraps an <a> link -->
<sup><a href="#fn2" id="rfn2">2</a></sup>and the earth then was welter and waste
```

There are **no ID attributes on verse `<sup>` elements** — verses are identified by their numeric content and position within the paragraph.

### Psalms (Vol3)

Each Psalm has its own file. Each poem colon is its own `<p>` element. Verse numbers appear as hyperlinks when the verse has a footnote, or as bare `<sup>` when it does not.

```html
<!-- Psalm verse WITH footnote — <a> wraps <sup> -->
<p class="poem2"><span class="hide">    </span>
  <a href="#v3ps1fn1" id="v3rps1fn1"><sup>1</sup></a>
  Happy the man who has not <a id="v3rps1n1"/>walked in the wicked's counsel,
</p>

<!-- Psalm verse WITHOUT footnote — bare <sup> -->
<p class="poem2"><span class="hide">    </span><sup>4</sup>Not so the wicked,</p>
```

---

## Chapter Heading Pattern

```html
<section epub:type="chapter" role="doc-chapter" title="Chapter 1">
  <header>
    <h2 class="cn" id="rpt1ch1">CHAPTER 1</h2>
  </header>
```

Psalm heading:
```html
<h2 class="cn" id="v3ps1">PSALM 1</h2>
```

---

## Footnote / Annotation Patterns

### Inline marker (prose)
The footnote-linked verse's `<sup>` wraps an `<a>` tag:
```html
<sup><a href="#fn26" id="rfn26">26</a></sup>a human. The term ʾadam…
```

### Inline marker (Psalms)
The verse number `<sup>` itself is wrapped in `<a>`:
```html
<a href="#v3ps1fn1" id="v3rps1fn1"><sup>1</sup></a>
```

### Footnote definition (same file)
Definitions appear at the bottom of the same `.xhtml` file as the text, after `<hr class="footnote_divider"/>`:

```html
<hr class="footnote_divider"/>
<p class="footnoteh">PSALM 1 NOTES</p>
<p class="footnote" id="v3ps1fn1">
  <a href="#v3rps1fn1">1</a>. 
  <a href="#v3rps1n1"><i>walked / . . . stood / . . . sat.</i></a>
  It is easy to understand why the ancient editors set this brief…
</p>
```

Prose pattern:
```html
<p class="footnote" id="fn2">
  2. welter and waste. The Hebrew tohu wabohu occurs only here…
</p>
```

**Note type**: All footnotes are `NoteType.TRANSLATOR`. Alter's notes blend translator rationale (Hebrew word explanations, translation alternatives) with literary-scholarly commentary; they are inseparable from his translation choices.

---

## Word-Level Inline Anchors (sub-verse markers)

`<a id="renN"/>` (prose) and `<a id="v3rpsNnN"/>` (Psalms) mark specific Hebrew words in the running text that are cross-referenced from footnote definitions. These are **not** verse markers.

```html
<!-- Prose: word anchor between footnote marker and the referenced word -->
<sup><a href="#fn26" id="rfn26">26</a></sup><a id="ren12"/>a human.

<!-- Psalms: word anchor inline at target word -->
Happy the man who has not <a id="v3rps1n1"/>walked in the wicked's counsel,
```

**Extraction decision**: Preserve as invisible block IDs (`^renN`) adjacent to the target word. No vault consumer exists yet, but they enable future word-level citation linking. See **PER-66** for implementation.

---

## Text Paragraph Classes

### Prose paragraph classes
| Class | Role |
|---|---|
| `noindentpb` | First paragraph of chapter opening (no indent, drop-cap letter) |
| `noindentp` | First paragraph after section break |
| `noindent` / `noindent1` / `noindent2b` | Prose paragraphs (varying indent levels) |
| `indent` | Indented continuation paragraph |
| `center` / `centerb` | Centered text (headings, titles) |

### Poetry paragraph classes
| Class | Role |
|---|---|
| `poem2` | First colon of a line (shallow indent) |
| `poem3` | Second colon / continuation (deeper indent) |
| `poem4s` | Third colon / closing verset (deepest indent) |
| `poem8` / `poem9` | Additional indentation levels |

### Footnote classes
| Class | Role |
|---|---|
| `footnote` | Footnote body paragraph |
| `footnoteh` | Footnote section header ("PSALM 1 NOTES") / navigation link |
| `footnotei` | Footnote continuation (italic-heavy note continuation) |
| `footnote_divider` | `<hr>` separator between text and footnotes |

---

## Page Break Markers (strip)

```html
<span class="right_1" epub:type="pagebreak" id="page_11" role="doc-pagebreak" title="11"/>
```

Strip entirely — physical page numbers carry no vault value.

---

## Drop Cap (strip)

```html
<span class="dropcap1">W</span>hen God began…
```

Strip — decorative only; retain the letter as plain text.

---

## Indentation Simulation (strip)

```html
<span class="hide">    </span>
```

Strip — used in Psalms to simulate visual indentation; meaningless in Markdown.

---

## Divine Name Rendering

The Tetragrammaton is rendered with small-caps HTML:
```html
L<small>ORD</small>         → LORD
L<small>ORD</small>'<small>S</small>  → LORD'S
```

**Extraction decision**: Render as plain `LORD` (all-caps). Obsidian inline HTML is fragile; clean Markdown text is preferred.

---

## Psalm Numbering

Alter uses **MT (Masoretic Text) numbering** throughout. The vault uses **LXX numbering as primary**.

Key offsets:
- Psalms 1–8: MT = LXX (no offset)
- Psalms 9–10 (MT) = Psalm 9 (LXX) — MT splits LXX Ps 9 into two
- Psalms 11–113 (MT) = Psalms 10–112 (LXX) — offset of -1
- Psalm 114–115 (MT) = Psalm 113 (LXX) — MT splits LXX Ps 113 into two
- Psalms 116 (MT) = Psalms 114–115 (LXX) — reverse
- Psalms 117–146 (MT) = Psalms 116–145 (LXX) — offset of -1
- Psalm 147 (MT) = Psalms 146–147 (LXX)
- Psalms 148–150 (MT) = Psalms 148–150 (LXX) (no offset)

**Extraction is blocked for Psalms** until `psalter-concordance.json` (MT↔LXX verse-level mapping) is built. Extract non-Psalm books first.

---

## Book Intro Material

Each book has a dedicated introduction file:
- `Vol1_Pt1Introduction.xhtml` — Genesis intro
- `Vol2_Pt5Introduction.xhtml` — Isaiah intro
- etc.

**Extraction decision**: Extract each intro as `{Book} — Alter Intro.md` to `100-References/Alter/` (parallel to OSB intro pattern). Intros are a distinctive feature of Alter's scholarly edition.

---

## Output Targets

- **Text companion**: `{Book} {Chapter} — Alter.md` — Alter's literary translation
- **Notes companion**: `{Book} {Chapter} — Alter Notes.md` — Alter's scholarly footnotes
- **Book intros**: `{Book} — Alter Intro.md` → `100-References/Alter/`

---

## Example Verse Output (raw)

### Genesis 1:1–3 (prose, multiple verses per paragraph)
```
¹When God began to create heaven and earth, [fn]²and the earth then was welter and waste
and darkness over the deep and God's breath [anchor] hovering over the waters,
³God said, "Let there be light." And there was light.
```

### Psalm 51:3 (MT) = Psalm 50:3 (LXX) — first content verse
```
³Grant me grace, God, as befits Your kindness,
    with Your great mercy wipe away my crimes.
```

### Isaiah 7:14
```
[fn]¹⁴Therefore the Master Himself shall give you a sign:
[anchor]the young woman is about to conceive and bear a son,
and she shall call his name Immanuel.
```

---

## Known Limitations

1. **No Deuterocanon**: 39 MT books only. Tobit, Judith, Maccabees, Wisdom, Sirach, Baruch, 1 Esdras, and Prayer of Manasseh are absent.
2. **Psalm numbering requires mapping**: MT numbers throughout; vault uses LXX primary. Psalms extraction blocked until `psalter-concordance.json` is built.
3. **No verse ID attributes**: Verse `<sup>` elements carry no `id` — verse extraction must walk the DOM and track verse numbers by content.
4. **Multiple verses per paragraph**: Literary prose layout — verse boundary detection requires parsing inline `<sup>` markers within paragraphs, not paragraph breaks.
5. **Minor Prophets sub-lettering**: Adapter must decode `Pt8a`–`Pt8d` and `Pt9a`–`Pt9h` into canonical book names using the mapping table above.
