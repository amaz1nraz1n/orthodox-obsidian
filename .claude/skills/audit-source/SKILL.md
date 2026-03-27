---
name: audit-source
description: Raw-inspect any registered Scripture source (EPUB/PDF/CSV/web), document its structure, run user spot-checks, and update the source structure doc. Use when adding a new source or verifying an existing one. Do NOT run the extractor — inspection only.
argument-hint: [source-name]
---

Raw-inspect a Scripture source registered in `sources.yaml`. Never runs extraction scripts. Always reads raw files directly. Produces or updates the source structure doc, then presents all decisions in a single batch at the end.

## Step 1 — Lookup

Read `sources.yaml` from the project root. Resolve the source by short name (e.g., `osb`, `eob`, `lexham`).

If the name is not found:
- List all registered sources with their label and status.
- Exit.

Extract: `path`, `format`, `testament`, `structure_doc`, `adapter`, `status`, `notes`.

## Step 2 — Mode Detection

Check if `structure_doc` exists on disk (e.g., `docs/osb-epub-source-structure.md`).

- **Additive/verify mode**: File exists → read it, then proceed to fill gaps and verify existing claims.
- **Full audit mode**: File does not exist → write a complete new structure doc from scratch.

State the mode clearly at the start before doing anything else.

## Step 3 — Raw Inspection

Inspect the raw source file directly. Never invoke the adapter or extract script.

### EPUB sources
```python
import zipfile, os
z = zipfile.ZipFile(path)
# List all members
names = z.namelist()
# Find OPF (content.opf or package.opf or any *.opf)
opf_name = next(n for n in names if n.endswith('.opf'))
opf = z.read(opf_name).decode('utf-8')
# Parse spine items from OPF to get reading order
# For each spine item: read the HTML/XHTML, parse with BeautifulSoup (lxml parser)
# Identify and document:
#   - verse marker patterns (class names, id patterns, e.g. id="Jn_vchap1-1")
#   - chapter markers
#   - pericope / section headings (class names, element types)
#   - inline footnote markers (<sup>, <a href>, custom classes)
#   - footnote definitions (separate HTML files? <div class="footnotedef">?)
#   - intro / preface material (separate spine items before chapter 1?)
#   - sub-verse markers (any <sup> or inline <a> within verse text — document passively, no decision required)
#   - encoding: UTF-8? polytonic Unicode?
#   - book boundary patterns (how does a new book start within the spine?)
```

### PDF sources
```python
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextBox, LTChar
# Iterate first 5-10 pages
# Classify text boxes by font size and y-position:
#   - running headers (top of page, all-caps)
#   - verse text (body size)
#   - footnotes (small, page bottom)
#   - pericope headings (smaller than body, not footnote)
#   - page numbers
# Note font sizes for each class
# Note column layout (single vs two-column, split point)
# Note GlyphLessFont presence (check font names in LTChar)
# Note OCR quality (stray chars, merged words, non-ASCII artifacts)
```

### CSV/TSV sources
```python
import csv
# Read first 20 rows
# Identify: delimiter, column names, verse/chapter fields, text encoding
# Note any tag patterns in text (e.g., <S>nnnnn</S> morphological tags, <m> tags)
# Note Psalm numbering (LXX vs MT)
```

### Web sources
- Fetch one sample chapter URL (e.g., the source's known URL pattern for John 1).
- Inspect HTML structure: verse element tags, class names, verse number patterns, Unicode encoding, any inline markers.

## Step 4 — Example Extraction

Pull 3 real verse samples by reading the raw file:
1. Chapter 1, verse 1 of the first book (e.g., Genesis 1:1 for OT, Matthew 1:1 for NT)
2. A middle chapter verse (e.g., John 3:16 for NT, Psalm 50:1 for Psalter)
3. A known reference verse: John 1:1 for NT sources, Genesis 1:1 for OT Torah, Psalm 50:1 LXX for Psalter sources

Show the raw extracted text exactly as it appears — before any cleaning.

## Step 5 — Spot-Check Questions

Present the extracted samples as targeted yes/no questions the user should verify by opening the source file directly.

Format each question as:
> "Does [Book Chapter:Verse] read: '[extracted text]'?"
> "Do you see a [pericope/section] heading '[heading text]' before verse [N]?"
> "Do you see inline markers like '[marker]' in the verse text?"

Wait for user answers before continuing. These confirm or correct your raw extraction findings.

## Step 6 — Collect All Decisions (Batch)

After spot-checks are complete, do NOT present decisions one at a time. Collect all open decisions and present them together in a single block.

For each decision, state:
- What was found in the raw source
- Options available
- Your recommendation

Example decisions to surface (as applicable):
- **Inline footnote markers**: `<sup>a</sup>` with href links found. Preserve word-position + link, or strip?
- **Sub-verse markers**: Any inline `<sup>` markers found mid-verse that are not footnote links? (Document passively — no decision required for these)
- **Pericope headings**: Found before verses. Extract and include in companion? Or skip?
- **Intro material**: Separate spine items found before chapter 1. Extract as `{Book} — {Source} Intro.md`?
- **Footnote definitions**: Found in separate file(s). Pair with verse anchors in companion?
- **Column layout** (PDF): Two-column detected. Confirmed column split point?
- **Book boundary** (multi-book source): How does the spine signal a new book? Class? ID prefix?
- **Note type taxonomy**: For each annotation type found, confirm the correct `ChapterNotes` slot:

  | Content type | Target slot |
  |---|---|
  | Study/commentary notes | `footnotes` |
  | Translator rationale ("Lit.", "Or:", "Heb.") | `translator_notes` |
  | Translation alternatives ("Or: *word*") | `alternatives` |
  | Historical/geographical background | `background_notes` |
  | Parallel passage refs ("(Mt 3:1–6)") | `parallel_passages` |
  | Textual variant readings | `variants` |
  | Patristic citations | `citations` |
  | Lectionary/liturgical notes | `liturgical` |

  Surface any ambiguous cases — e.g., are this source's "footnotes" translator rationale or commentary?

Wait for user to answer all decisions before updating any files.

## Step 7 — Update Structure Doc

Based on inspection findings and user decisions:

**Additive/verify mode:**
- Add gap sections that are missing from the existing doc.
- Annotate existing claims with `✓ verified` or `✗ needs update` based on spot-check results.
- Do NOT overwrite sections that were already correctly documented.

**Full audit mode:**
- Write the complete structure doc to `docs/{source-name}-source-structure.md`.
- Sections to include (as applicable to format):
  - File metadata (path, size, page count or spine item count)
  - EPUB: spine structure, OPF details, HTML file naming, encoding
  - PDF: page dimensions, column layout, font size classification table
  - Verse marker patterns (with concrete examples from the raw file)
  - Chapter marker patterns
  - Pericope / section heading patterns
  - Footnote / annotation patterns (inline markers + definition location)
  - Sub-verse markers (if found — passive documentation only)
  - Book boundary signals
  - Intro / preface material
  - Known limitations or quality issues
  - Example verse output (raw)

## Step 8 — Approval Gate

Ask: "Is this source approved for extraction? (yes/no)"

If **yes**:
1. Update `sources.yaml`: set `status: approved` for this source.
2. Update the CLAUDE.md source table (if one exists in the project CLAUDE.md) to reflect the approved status.
3. Note any deferred items (e.g., RSV Notes not yet implemented) for follow-up.

If **no**:
- Note what is blocking approval (quality issues, incomplete structure, etc.).
- Leave `status` unchanged (or update to `incomplete` if appropriate).

## Step 9 — Beads

- **On start**: `bd create --title "audit-source: {name}" --type=task` then claim it.
- **After spot-checks**: Update bead notes with findings summary.
- **On close**: Close bead with decision summary and structure doc path.

## Behavior

- Never run adapter or extract scripts. Inspection only.
- Always read raw files directly (zipfile for EPUB, pdfminer for PDF, csv module for CSV).
- Mode detection is automatic — state it explicitly, don't ask.
- Spot-check questions use real extracted text, not hypothetical examples.
- Sub-verse markers: document passively, no interactive decision point.
- All decisions presented in one batch after spot-checks complete.
- Do not update structure doc or sources.yaml until user has answered both spot-checks and decisions.
- If the source path in sources.yaml does not resolve on disk, say so and exit — do not guess an alternate path.
