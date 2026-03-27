# GOArch Online Chapel — Greek NT Source Structure

Audit of `https://onlinechapel.goarch.org/biblegreek/`
(1904 Antoniades Patriarchal Text — canonical liturgical Greek NT of Eastern Orthodoxy)

---

## Why This Source

The vault uses the **1904 Ecumenical Patriarchate (Antoniades) text** — not the Byzantine Majority Text
(Robinson-Pierpont 2018) used in the original adapter — because:

- It is the actual text chanted at GOArch/OCA/Antiochian/ROCOR services
- The local `byztxt/greektext-antoniades` GitHub repo has the same text but **unaccented monotonic**
  (`εν αρχη ην` instead of `Ἐν ἀρχῇ ἦν`) — unusable for study
- The GOArch site is the only freely accessible source with **full polytonic Unicode accents**
- The 1904 text is public domain; no copyright is asserted on the site pages

Previous source: `byztxt/byzantine-majority-text` CSV (Robinson-Pierpont 2018). Close to Antoniades
but a scholarly reconstruction, not the liturgical text. Retained at `source_files/Greek/byzantine-majority-text/`.

---

## URL Patterns

```
# Full book (single request — preferred)
https://onlinechapel.goarch.org/biblegreek/?id={N}&book={abbr}&chapter=full

# Single chapter
https://onlinechapel.goarch.org/biblegreek/?id={N}&book={abbr}&chapter={ch}
```

The `id` parameter is a 0-based index that must match `book`. Both are required.
Extraction uses `chapter=full` — one request per book (27 total for the full NT).

### Book Manifest

| id | param | Vault canonical name | Chapters |
|----|-------|---------------------|---------|
| 0  | Matt  | Matthew             | 28 |
| 1  | Mark  | Mark                | 16 |
| 2  | Luke  | Luke                | 24 |
| 3  | John  | John                | 21 |
| 4  | Acts  | Acts                | 28 |
| 5  | Rom   | Romans              | 16 |
| 6  | 1Cor  | I Corinthians       | 16 |
| 7  | 2Cor  | II Corinthians      | 13 |
| 8  | Gal   | Galatians           | 6  |
| 9  | Eph   | Ephesians           | 6  |
| 10 | Phil  | Philippians         | 4  |
| 11 | Col   | Colossians          | 4  |
| 12 | 1Thess | I Thessalonians   | 5  |
| 13 | 2Thess | II Thessalonians  | 3  |
| 14 | 1Tim  | I Timothy           | 6  |
| 15 | 2Tim  | II Timothy          | 4  |
| 16 | Titus | Titus               | 3  |
| 17 | Phlm  | Philemon            | 1  |
| 18 | Heb   | Hebrews             | 13 |
| 19 | Jas   | James               | 5  |
| 20 | 1Pet  | I Peter             | 5  |
| 21 | 2Pet  | II Peter            | 3  |
| 22 | 1John | I John              | 5  |
| 23 | 2John | II John             | 1  |
| 24 | 3John | III John            | 1  |
| 25 | Jude  | Jude                | 1  |
| 26 | Rev   | Revelation          | 22 |

---

## HTML Structure

### Chapter wrapper

```html
<div type="chapter" osisID="John.1" n="Α">
  <!-- verses -->
</div>
```

`osisID` is `{BookParam}.{ChapterNum}` and is the canonical chapter locator.
The `n` attribute is the Greek ordinal numeral (Α, Β, Γ…) — not used in extraction.

### Verse Pattern A — Linegroup (poetic / multi-line)

Verse number in its own `<p>`, followed immediately by a sibling `<div class='linegroup'>`:

```html
<p>
  <span class="verse">[1]</span>
</p>
<div class='linegroup'>
  <div class='lineitem'>Ἐν ἀρχῇ ἦν ὁ Λόγος,</div>
  <div class='lineitem'>καὶ ὁ Λόγος ἦν πρὸς τὸν Θεόν,</div>
  <div class='lineitem'>καὶ Θεὸς ἦν ὁ Λόγος.</div>
</div>
```

`lineitem` texts are joined with a single space to form the verse text.

### Verse Pattern B — Inline prose

Multiple verses flow inside a single `<p>`, each preceded by its `<span class="verse">`:

```html
<p>
  <span class="verse">[6]</span>᾿Εγένετο ἄνθρωπος ἀπεσταλμένος παρὰ Θεοῦ, ὄνομα αὐτῷ ᾿Ιωάννης·
  <span class="verse">[7]</span>οὗτος ἦλθεν εἰς μαρτυρίαν, ἵνα μαρτυρήσῃ περὶ τοῦ φωτός.
  <span class="verse">[8]</span>οὐκ ἦν ἐκεῖνος τὸ φῶς, ἀλλ᾽ ἵνα μαρτυρήσῃ περὶ τοῦ φωτός.
</p>
```

Text between consecutive spans (NavigableStrings) is the verse body.

### Verse number span

```html
<span class="verse">[N]</span>
```

`[N]` text is stripped; the integer `N` is the verse number.
The page JavaScript `toggleVerses()` shows/hides these spans — irrelevant for extraction.

---

## Parsing Algorithm

1. Fetch `?id={N}&book={abbr}&chapter=full` — returns all chapters concatenated
2. Parse with `lxml` via BeautifulSoup
3. For each `<div type="chapter" osisID="...">`:
   - Extract chapter number from `osisID` (e.g. `John.3` → `3`)
4. Iterate **direct children** of the chapter div:
   - `<p>` containing `.verse` spans → iterate `<p>` children:
     - `<span class="verse">` → flush current buffer; parse new verse number
     - NavigableString / other element → append text to buffer
     - Flush final buffer at end of `<p>`; track `last_verse`
   - `<div class='linegroup'>` → belongs to `last_verse`; collect all `<div class='lineitem'>` texts
5. Normalize whitespace with `re.sub(r'\s+', ' ', text).strip()`
6. Yield `(Chapter, ChapterNotes)` — notes always empty (source has no footnotes)

---

## Output

- Source label: `"Greek NT"` (unchanged from previous adapter — vault links stay valid)
- File name: `{Book} {Ch} — Greek NT.md` (same as before)
- Frontmatter: `source: "Greek NT"`, `edition: "Antoniades 1904"` (new field)
- Rate limit: 1.5 s between book fetches; User-Agent header set to avoid bot detection

---

## Scope

- NT only (27 books). LXX/OT is handled separately by `GreekLxxCsvSource` (Rahlfs 1935).
- No footnotes or study notes in this source.
- No `notes_suffix` link in nav callout (same policy as previous Greek NT adapter).

---

## Extractor

- Adapter: `vault_builder/adapters/sources/goarch_greek_nt.py` (`GoArchGreekNtSource`)
- Extract script: `extract_greek_nt_goarch.py`
- Replaces: `vault_builder/adapters/sources/greek_nt_csv.py` (`GreekNtCsvSource`)
