# NETS — A New English Translation of the Septuagint: Source Structure

**Source key**: `nets`
**File**: `./source_files/Old Testament /A new English translation of the Septuagint.epub`
**Format**: EPUB
**Size**: 6.5 MB
**Spine items**: 858 (42 chapter HTML files + ~800 page HTML files)
**OPF**: `OEBPS/html/volume.opf`
**NCX**: `OEBPS/html/toc.ncx`
**Testament**: OT — full LXX canon including all Deuterocanonical books
**Publisher**: Oxford University Press, 2007
**Editors**: Albert Pietersma and Benjamin G. Wright

---

## Canon Coverage

Full LXX canon — 39+ books including all Deuterocanonical material absent from the MT:

| Section | Books |
|---|---|
| Laws | Genesis, Exodus, Leuitikon, Numbers, Deuteronomion |
| Histories | Iesous, Judges, Routh, 1–4 Reigns, 1–2 Supplements, 1–2 Esdras, Esther, Ioudith, Tobit, 1–4 Makkabees |
| Poetic Books | Psalms, Prayer of Manasses, Proverbs, Ecclesiast, Song of Songs, Iob, Wisdom of Salomon, Wisdom of Iesous son of Sirach, Psalms of Salomon |
| Prophecies | The Twelve Prophets, Esaias, Ieremias, Barouch, Lamentations, Letter of Ieremias, Iezekiel, Sousanna, Daniel, Bel and the Dragon |

**No gaps for Orthodox use.** NETS fills the Deuterocanon slot that no other current vault source covers.

---

## File Structure

Two distinct file types in the spine:

### Chapter files (`chapter01.html` – `chapter42.html`)
Each chapter file contains **one LXX book** (or book group for the Twelve Prophets): translator introduction followed by the full Bible text with inline footnote markers. Some books span two files (`chapter24a`, `chapter31a`, `chapter33a`, `chapter34a`, `chapter35a`).

### Page files (`page_N.html`)
One file per printed page (~800 files). Each contains only **footnote definitions** for that page — no Bible text. The chapter HTML links out to these files for footnote content.

---

## Book → Chapter File Mapping

| Book (canonical name) | NETS name | Chapter file | Anchor |
|---|---|---|---|
| Genesis | Genesis | `chapter01.html` | `#pa01ch01` |
| Exodus | Exodus | `chapter02.html` | `#pa01ch02` |
| Leviticus | Leuitikon | `chapter03.html` | `#pa01ch03` |
| Numbers | Numbers | `chapter04.html` | `#pa01ch04` |
| Deuteronomy | Deuteronomion | `chapter05.html` | `#pa01ch05` |
| Joshua | Iesous | `chapter06.html` | `#pa01ch06` |
| Judges | Judges | `chapter07.html` | `#pa01ch07` |
| Ruth | Routh | `chapter08.html` | `#pa02ch03` |
| 1 Samuel | 1 Reigns | `chapter09.html` | `#pa02ch04` |
| 2 Samuel | 2 Reigns | `chapter10.html` | `#pa02ch05` |
| 1 Kings | 3 Reigns | `chapter11.html` | `#pa02ch06` |
| 2 Kings | 4 Reigns | `chapter12.html` | `#pa02ch07` |
| 1 Chronicles | 1 Supplements | `chapter13.html` | `#pa02ch08` |
| 2 Chronicles | 2 Supplements | `chapter14.html` | `#pa02ch09` |
| 1 Esdras | 1 Esdras | `chapter15.html` | `#pa02ch10` |
| 2 Esdras (Ezra-Nehemiah) | 2 Esdras | `chapter16.html` | `#pa02ch11` |
| Esther | Esther | `chapter17.html` | `#pa02ch12` |
| Judith | Ioudith | `chapter18.html` | `#pa02ch13` |
| Tobit | Tobit | `chapter19.html` | `#pa02ch14` |
| 1 Maccabees | 1 Makkabees | `chapter20.html` | `#pa02ch15` |
| 2 Maccabees | 2 Makkabees | `chapter21.html` | `#pa02ch16` |
| 3 Maccabees | 3 Makkabees | `chapter22.html` | `#pa02ch17` |
| 4 Maccabees | 4 Makkabees | `chapter23.html` | `#pa02ch18` |
| Psalms | Psalms | `chapter24.html` | `#apa03ch01` |
| Prayer of Manasseh | Prayer of Manasses | `chapter24.html` | `#pa03ch01` |
| Proverbs | Proverbs | `chapter25.html` | `#pa03ch02` |
| Ecclesiastes | Ecclesiast | `chapter26.html` | `#pa03ch03` |
| Song of Songs | Song of Songs | `chapter27.html` | `#pa03ch04` |
| Job | Iob | `chapter28.html` | `#pa03ch05` |
| Wisdom of Solomon | Wisdom of Salomon | `chapter29.html` | `#pa03ch06` |
| Sirach | Wisdom of Iesous son of Sirach | `chapter30.html` | `#pa03ch07` |
| Psalms of Solomon | Psalms of Salomon | `chapter31.html` | `#pa03ch08` |
| The Twelve Prophets | The Twelve Prophets | `chapter33.html` / `chapter33a.html` | `#pa04ch01` |
| Isaiah | Esaias | `chapter34.html` | `#pa04ch02` |
| Jeremiah | Ieremias | `chapter35.html` | `#pa04ch03` |
| Baruch | Barouch | `chapter36.html` | `#pa04ch04` |
| Lamentations | Lamentations | `chapter37.html` | `#pa04ch05` |
| Letter of Jeremiah | Letter of Ieremias | `chapter38.html` | `#pa04ch06` |
| Ezekiel | Iezekiel | `chapter39.html` | `#pa04ch07` |
| Susanna | Sousanna | `chapter40.html` | `#pa04ch08` |
| Daniel | Daniel | `chapter41.html` | `#pa04ch09` |
| Bel and the Dragon | Bel and the Dragon | `chapter42.html` | `#pa04ch10` |

**Extraction rule**: Map NETS names to canonical English vault names at the extraction boundary. Do NOT use NETS names in output filenames.

---

## Book Boundary Detection

Each chapter file begins with the translator's scholarly introduction, then transitions to the Bible text. The Bible text starts after a `<p class="attribute">` element (the translator's byline):

```html
<p class="attribute">R<small>OBERT</small> J. V. H<small>IEBERT</small></p>
<p class="noindent"><strong>1</strong> In the beginning God made the sky…
```

The `<p class="attribute">` is the reliable signal that Bible text follows immediately.

---

## Verse Marker Patterns

**Three patterns coexist** — all must be handled:

### Pattern 1: Chapter-opening verse (`<strong>`)
Verse 1 of any chapter (or book section) uses bold:
```html
<p class="noindent"><strong>1</strong> In the beginning God made the sky and the earth.
<sup>2</sup>Yet the earth was invisible and unformed…</p>
```

### Pattern 2: Mid-paragraph verse (`<sup>`)
Subsequent verse numbers within the same paragraph use superscript:
```html
<sup>7</sup>And God made the firmament… <sup>8</sup>And God called the firmament Sky.
```

### Pattern 3: New-paragraph verse (plain text)
When a verse begins a new paragraph, the number appears as plain text with no wrapper tag:
```html
<p class="indent">6 And God said, "Let a firmament come into being…
<sup>7</sup>And God made the firmament…</p>
```

**Extraction strategy**: Walk the paragraph DOM; detect bare numeric text nodes at paragraph start (Pattern 3), `<strong>` numeric content (Pattern 1), and `<sup>` numeric content (Pattern 2) as verse boundaries. No verse ID attributes exist — verse identity is derived from content.

---

## Chapter Heading Pattern

Bible chapter headings within a book file use centered bold:
```html
<p class="center"><strong>1</strong></p>
```
or for Psalms:
```html
<p class="center"><strong>Psalm 50(51)</strong></p>
```

---

## Psalm Numbering

**LXX numbering is primary** — NETS displays LXX number first with MT in parentheses:
- Psalm heading: `<p class="center"><strong>Psalm 50(51)</strong></p>`
- Verse numbers with dual offset: `<sup>3(1)</sup>` (LXX verse 3 = MT verse 1, because LXX includes a 2-verse superscription)

**This matches the vault's LXX-primary convention exactly.** No mapping table required — use the LXX number directly. This is a significant structural advantage over Alter.

---

## Section Headings

**No pericope or section headings** in the Bible text body. The only headings are:
- `<h2 class="h2">` — book title (in translator intro section)
- `<h4 class="h4">`, `<h5 class="h5">` — intro subsections
- `<p class="center"><strong>N</strong></p>` — chapter number markers within Bible text

---

## Footnote / Annotation Patterns

### Inline marker (in chapter file)
```html
<sup><a id="pg830en_e"/><a class="nounder" href="page_830.html#pg830ene">e</a></sup>
```
Two `<a>` elements: one anchor ID (`pg830en_e`) for back-linking, one hyperlink to the page file.

### Footnote definition (in page file)
```html
<!-- page_830.html -->
<p class="endnote"><a id="pg830ene"/>
  <sup><a class="nounder" href="chapter34.html#pg830en_e">e</a></sup>
  Or <em>great and very strong</em>
</p>
```

Resolution: parse `href="page_N.html#pgNenX"` from inline marker → load `page_N.html` → find `<p class="endnote">` with matching `id`.

### Note type classification
| Pattern | Note type | `NoteType` slot |
|---|---|---|
| `Om = We^ed`, `= We^N`, MT divergence | Textual omission/variant | `VARIANTS` |
| `Or …`, `Lit. …` | Translation alternative | `TRANSLATOR` |
| Scholarly commentary, bibliographic refs | Translator commentary | `TRANSLATOR` |

Detect `VARIANTS` by presence of `Om`, `= We`, `MT` at start of note text. All others → `TRANSLATOR`.

---

## GBS Inline Anchors (strip)

`<a id="GBS.XXXX.XX"/>` appears every ~5 verses throughout the text. These are Göttingen Bible Society cross-reference IDs used by the NETS editorial apparatus.

**Strip entirely** — no in-vault consumer; opaque to readers.

```html
<a id="GBS.0047.04"/>   ← strip
```

---

## Translator Introductions

Each chapter file begins with a scholarly translator introduction (varies from ~2 pages for short books to 42+ pages for Genesis) before the Bible text. The intro covers: Greek text edition used, translation profile, editorial decisions, bibliographic note.

**Extract each intro** as `{Book} — NETS Intro.md` → `100-References/NETS/`. Use the `<p class="attribute">` byline as the delimiter — everything before it is intro, everything after is Bible text.

---

## Text Paragraph Classes

| Class | Role |
|---|---|
| `noindent` | First paragraph of chapter / paragraph with no indent |
| `indent` | Standard prose paragraph |
| `indenthanging1` | Poetry: hanging indent, level 1 |
| `indenthanging1a` | Poetry: hanging indent with psalm superscription |
| `indenthanging1c` / `1d` | Poetry: hanging indent variants |
| `indenthanging11` | Poetry: double-hanging indent |
| `indenthanging31` | Poetry: triple-hanging indent |
| `blockquote1` / `blockquote2` | Block quotation |
| `center` | Chapter number / Psalm heading |
| `attribute` | Translator byline (signals end of intro, start of text) |
| `endnote` / `endnote1` | Footnote definition (in page files only) |

---

## Output Targets

- **Text companion**: `{Book} {Chapter} — NETS.md`
- **Notes companion**: `{Book} {Chapter} — NETS Notes.md`
- **Book intros**: `{Book} — NETS Intro.md` → `100-References/NETS/`

---

## Example Verse Output (raw)

### Genesis 1:1–2
```
In the beginning God made the sky and the earth. Yet the earth was invisible and
unformed, and darkness was over the abyss, and a divine wind was being carried
along over the water.
```

### Psalm 50 (LXX) / Psalm 51 (MT) — verse 3(1)
*(Heading: `Psalm 50(51)` · Verse: `3(1)`)*
```
Have mercy on me, O God, according to your great mercy,
and according to the abundance of your compassion
blot out my lawless deed.
```

### Isaiah 7:14
```
Therefore the Lord himself will give you a sign. Look, the virgin shall be with
child and bear a son, and you shall name him Emmanouel.
```
*(NETS reads "the virgin" — LXX παρθένος — unlike Alter's "the young woman.")*

---

## Known Limitations

1. **Three verse marker patterns**: Plain-text paragraph-start verse numbers have no wrapper tag — DOM walking required; regex on raw text is unreliable.
2. **Footnotes in separate page files**: Each footnote definition must be resolved by following the `href` from the chapter file to the correct `page_N.html`. ~800 page files must be parsed on demand.
3. **Translator intro mixed into chapter file**: The `<p class="attribute">` delimiter must reliably identify the intro/text boundary for each of the 42 chapter files.
4. **Twelve Prophets split**: Hosea–Micah in `chapter33.html`, Obadiah–Malachi in `chapter33a.html` — both must be parsed for the Minor Prophets.
5. **Images in intros**: Some intro pages contain images of Greek/Hebrew text (`<img src="images/..."/>`). Strip during intro extraction; note presence in structure doc.
