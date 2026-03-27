# Eastern/Greek Orthodox Bible (EOB) NT PDF Source Structure

Implementation-facing structure notes for the EOB adapter.
See also: `docs/osb-epub-source-structure.md`, `docs/lexham-epub-source-structure.md`, `docs/net-pdf-source-structure.md`

---

**Adapter:** `vault_builder/adapters/sources/eob_pdf.py`
**Coverage:** NT only (all 27 books)
**Source file:** `The Orthodox Bible: New Testament (Eastern/Greek Orthodox Bible).pdf`

---

## Page Range

| Range (1-indexed) | Content |
|---|---|
| 1–47 | Front matter, OT intro — skip |
| 48–626 | NT text — parse |
| 627+ | Appendices — stop |

0-indexed equivalents in code: `_NT_FIRST_PAGE = 47`, `_APPENDIX_FIRST_PAGE = 626`.

---

## Text Box Classification Order

Each text box is classified in this order (first match wins):

1. **Footnote marker** — matches `^(\[\d+\])+$` → skip
2. **Book title** — matches `"BOOKNAME  \n(GREEK TEXT)"` at y≈676 → update book state
3. **Section intro header** — ALL-ASCII-uppercase, length > 4, no Greek → reset chapter state
4. **Chapter heading** — one of four patterns (see below) → update chapter, capture verse 1 text
5. **Verse text** — everything else in scope → parse inline verse numbers

---

## Book Title Box Pattern

```
MATTHEW
(ΚΑΤΑ ΜΑΤΘΑΙΟΝ)
```

First line: all-uppercase English book name. Gospel titles may have an `(ACCORDING TO)` prefix — stripped before lookup.
Second line: Greek title in parentheses (`[\u0370-\u03FF\w\s]+`).

---

## Chapter Heading Patterns

| Pattern | Example | Notes |
|---|---|---|
| 1: Standalone integer | `3` | Bare chapter number |
| 2: Pericope + integer | `The Birth of Jesus\n18` | Chapter number on last line |
| 3: Pericope + integer + verse 1 text | `The visit of the magi\n2\nWhen Jesus was born…` | Verse 1 text in same box |
| 4: Integer + verse 1 text | `1\nJames, a bondservant of God…` | Verse 1 text on next line |

Verse 1 is **always implicit** — it is either in the chapter heading box (patterns 3, 4) or begins at the first text box after the heading.

---

## Verse Text Parsing

Verse numbers are inline digits immediately preceding a letter, with no separator:

```
2Abraham was the father of Isaac, 3and Isaac…
```

Regex: `(?<!\d)(\d+)(?=[A-Za-z])` — matches digit not preceded by digit, followed by any letter.

Mid-chapter pericope heading lines are stripped before verse parsing:

```
The Birth of Jesus
18Now when Jesus was born…
```

Prefix regex: `^([A-Z][^0-9\n]+(?:\n[A-Z][^0-9\n]+)*)\n(?=\d)` — skips all Title-Case lines before the first verse-starting digit.

---

## Section Intro Header Detection

Between-book intro prose pages use ALL-ASCII-uppercase headers (e.g. `THE PAULINE LETTERS`). These reset chapter and verse state to prevent bleed from the previous book's last chapter.

Detection: length > 4, no Greek characters, matches `^[A-Z0-9\s\-:,/()\[\].!?"\'—]+$`, and is not a standalone integer.

---

## Domain Mapping

EOB yields `Book` → `Chapter` → `Verse` (canonical text only, no notes layer). The EOB PDF contains footnotes but they are not extracted in Phase 1.

---

## Known Gaps / Caveats

| Issue | Detail |
|---|---|
| Intro prose bleed (full-run only) | Inter-book intro prose pages (e.g. Pauline intro before Romans) may emit a few words into the prior book's last chapter in full mode. Benign in sample-only mode. Section intro header detection mitigates this but does not eliminate it entirely. |
| Footnote content not accessible | EOB footnotes use running `[N]` reference markers throughout the entire NT (numbers reach 2700+ by Revelation). The footnote *text* does not appear in any parseable text box in the PDF — not in the NT pages (48–626) and not in the appendix essays (627–944). A full scan of all 944 pages for `[N] text...` boxes found zero matches. The EOB Notes layer is therefore not buildable from this PDF. |
| Italic / formatting lost | Inline markup extracted as plain text. |
| OT not covered | EOB is NT-only in this adapter. Lexham covers the OT. |

---

## Related Docs

| Doc | What it covers |
|---|---|
| `docs/osb-epub-source-structure.md` | OSB EPUB — full tag/class inventory, note file structure, known gaps |
| `docs/lexham-epub-source-structure.md` | Lexham LES EPUB — spine layout, anchor patterns, span taxonomy |
| `docs/net-pdf-source-structure.md` | NET Bible PDF — two-column layout, note box parsing, column cursors |
| `docs/implementation-architecture.md` | Ports & Adapters design, domain model, renderer contracts |
| `docs/source-roadmap.md` | Source status, phase roadmap, acquisition notes |
| `docs/validation-plan.md` | Validator rules, fixture strategy, test execution policy |
