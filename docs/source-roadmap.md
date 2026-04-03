# Orthodox Vault Source Roadmap

This document captures the implementation-facing roadmap for source acquisition, source prioritization, build order, and later-phase expansion.

`Orthodox-Vault-Goals.md` remains the north-star document.
This file answers:

- which sources are local
- which sources belong to the active and queued build phases
- what gets built first
- what should be manually acquired later

## Project Snapshot — 2026-04-01

### Where The Project Stands

- Core vault architecture is stable: canonical hub files, verse-anchor contract, companion-note model, shared nav contract, and validator framework are all in place.
- The primary source stack is already implemented and usable: OSB, Lexham, EOB, NET, Greek NT, Greek LXX, Apostolic Fathers, and lectionary integration.
- Full extraction and Google Drive sync have already been exercised for the main Bible stack, but that does **not** mean the project is in a "done building, start new sources freely" phase.
- The project has shifted from foundational extraction work to three parallel concerns:
  - quality triage on generated output
  - polish of note presentation and navigation
  - disciplined admission of new sources only when quality is high enough
- Linear now reflects that shift explicitly: Phase 3 is the active execution lane, while Phase 2, Phase 4, and Phase 5 are queued/backlog.

### Linear Board Snapshot

- Phase 1 — Core Sources: complete.
- Phase 2 — New Sources: backlog/queued; Alter, DBH NT, NOAB RSV, and related source assessment work live here.
- Phase 3 — Vault Polish: active; current issues cover parallel passages, citation routing, and companion discoverability.
- Phase 4 — Photocopy PDF Sources: backlog; NOAB quality gating and OCR cleanup live here.
- Phase 5 — Interlinear Hubs: backlog; dynamic/embedded interlinear work lives here.

### Current Reality Check

- **NOAB RSV is still gated.** A substantial `pdfplumber` refactor improved layout recovery, but the source PDF remains poor enough that extraction quality is still not acceptable for routine vault use or inclusion in full runs.
- **Navigation and note UX still need polish.** The next high-value work is improving hub-to-notes navigation, tightening cross-layer navigation behavior, and making note layers easier to move through in actual reading.
- **Visual callout styling is still missing.** New taxonomy callouts render with Obsidian defaults; this is now a polish task, not an architecture task.
- **Validator follow-up is still required.** Full-stack extraction has been run, but its remaining warnings/errors need to be classified into true bugs, source limitations, or validator expectation mismatches.
- **Phase 2 source work is not the immediate focus.** New-source candidates remain valid, but the board is intentionally keeping them behind the current polish lane.

### Immediate Next 3 Tasks

1. **Finish the active Phase 3 lane**
   - Land the in-progress parallel-passage and citation-routing work.
   - Keep companion discoverability and note navigation aligned with the shared nav contract.
   - Treat the current polish lane as the primary board focus until it is actually closed out.
2. **Keep Phase 2 source additions queued**
   - Leave Alter, DBH NT, NOAB RSV, and similar source-admission work in backlog unless a source has a clear audited path and an approved implementation slot.
   - Avoid starting a new source just because it is available locally.
   - Promote only when the source structure doc and extraction target are both ready.
3. **Hold Phase 4 and Phase 5 as planned follow-on work**
   - Keep NOAB quality gating and photocopy-PDF cleanup in the dedicated PDF lane.
   - Keep dynamic interlinear / embedded-hub work in reserve until the current polish lane is stable.
   - Do not let later-phase architecture distract from the current execution lane.

## Current Source Status

### Bible Texts — Local

| Source | Format | Current Role | Confidence |
|-------|--------|--------------|------------|
| OSB | EPUB | Mode 1 canonical text + OSB notes | High |
| EOB NT | PDF | Primary Mode 2 NT candidate | Medium-high |
| EOB OT | PDF | Secondary OT comparison candidate | Medium |
| Lexham English Septuagint | EPUB | Primary Mode 2 OT candidate | High |
| Holy Transfiguration Monastery Psalter | PDF | Psalter-only liturgical supplement, not default Mode 2 | Medium |
| The Psalms of David | EPUB | Psalter-only poetic/devotional supplement, not default Mode 2 | Medium-high |
| NET Bible (1st ed.) | PDF | Notes-first technical layer | High |
| Philokalia | PDF | Distributed/manual source | Medium |
| Apostolic Fathers | EPUB + PDF | Distributed Patristic source; EPUB preferred for English extraction | Medium-high |
| Manley (Bible and the Holy Fathers for Orthodox) | Web/PDF | Lectionary-organized Fathers catena; candidate companion source | Medium-high |

### Greek Sources

| Source | Format | Location | Status |
|-------|--------|----------|--------|
| `byztxt/greektext-antoniades` | Text (unaccented, Beta Code + unicode) | `source_files/Greek/antoniades/` | ✓ Cloned |
| `byztxt/byzantine-majority-text` | CSV (`chapter,verse,text`, polytonic) | `source_files/Greek/byzantine-majority-text/` | ✓ Cloned — superseded by GOArch |
| GOArch Online Chapel | Live HTML scrape — 1904 Antoniades Patriarchal Text, fully polytonic | `https://onlinechapel.goarch.org/biblegreek/` | ✓ **Active NT source** |
| CCAT Rahlfs LXX | Beta Code `.mlxx` files (requires user declaration) | Not yet acquired | Pending |
| STEPBible TAGOT | TSV CC BY 4.0, still "coming" | Not yet available | Watch |

**Decision (2026-03-22):** Switched from Byzantine Majority Text CSV to GOArch 1904 Antoniades Patriarchal Text (live scrape). Antoniades is the actual text chanted at GOArch/OCA/Antiochian/ROCOR services. Local Antoniades repo (`byztxt/greektext-antoniades`) confirmed unaccented monotonic — unusable. GOArch is the only accessible source with full polytonic Unicode for the liturgical text. Byzantine CSV retained locally as reference.

## Source-Specific Assessments

### OSB

- best source in the current inventory
- structured EPUB
- semantic verse IDs
- study-note families already separated in source files
- first extraction target and canonical foundation

### EOB NT

- **source**: `source_files/New Testament/EOB NT.epub` (EOB-2 split-file EPUB, 128 HTML files)
- EPUB adapter (`eob_epub.py`) supersedes the old PDF adapter (`eob_pdf.py`)
- EPUB is substantially cleaner than the PDF: structured HTML, consistent chapter/verse markers, no page-layout heuristics, no intro-prose bleed
- chapter markers: `<p>` whose full text is a single integer 1–28 (multiple CSS class variants — detected by content, not class name)
- verse markers: inline `<sup class="calibre31">N</sup>`; verse 1 is implicit (text before first sup after chapter marker)
- endnote refs (`<a id="_ednrefN">`) are stripped from reading text; some verses carry `{word}` curly-bracket notation for implied words — this is EOB editorial markup, not an artifact
- keep as primary Mode 2 NT source
- Phase 1 policy: strip endnote markers from reading text; defer any dedicated `EOB Notes` layer until after base text extraction is stable

### EOB OT

- owned PDF is readable and digitally extractable
- more structurally cumbersome than Lexham
- keep as a secondary Orthodox comparison layer unless later extraction quality proves strong enough to promote it

### Lexham English Septuagint

- local EPUB
- structured XHTML with book/chapter anchors and linked footnotes
- current best OT Mode 2 extraction target in local inventory
- back-of-book note apparatus is linked cleanly from the chapter XHTML, which makes later note extraction feasible
- Phase 1 policy: produce a text companion first, remove inline note markers from the reading text, and document the note-link strategy rather than forcing a second Lexham notes artifact immediately

### Holy Transfiguration Monastery Psalter

- local PDF
- body text is readable and extractable, but the artifact is still PDF-first rather than clean structured HTML
- includes kathisma framing, doxologies, the nine odes, and recitation guidance in addition to Psalm text
- stronger as a specialized Orthodox/liturgical Psalter layer than as the default OT Mode 2 replacement

### The Psalms of David

- local EPUB
- structurally extractable with per-Psalm headings, verse numbers, and sparse footnotes inside kathisma groupings
- literary and contemplative in register rather than primarily literal or technical
- best understood as a poetic/devotional Psalter supplement rather than the default comparison layer

### NET

- notes-first source, not primarily a second reading Bible
- PDF is digitally extractable
- stable note-type markers already present on-page
- should produce a notes-first technical companion

### Apostolic Fathers

- EPUB is preferred for English extraction
- Greek/English PDF is a diglot reference source, not the default parser target
- best modeled as distributed Patristic notes first, curated catena files later

### Manley

- Internet Archive scan of the 1984 SVS Press edition is available with PDF plus OCR derivatives
- `_djvu.txt` is the best primary parse target; the PDF text layer is noisy in the front matter
- the source is liturgical / lectionary-organized, not chapter-shaped
- best modeled as source-backed Fathers companions keyed to Scripture chapters, with the Scripture anchor inferred from the reading header or explicit citation line
- sample output now follows the shared sample envelope used by the other source adapters; remaining work is OCR cleanup and broader chapter coverage

### Philokalia

- readable OCR prose with numbered sections and Scripture citations
- not naturally chapter-commentary shaped
- keep distributed and manual

## Psalter-Specific Decision

The Psalter deserves special attention, but Phase 1 should still avoid introducing a book-specific exception to the base mode system.

- keep Lexham as the default Phase 1 OT Mode 2 source, including Psalms
- do not replace Lexham with a Psalms-only source in the main Mode 2 slot during the first pass
- treat the HTM Psalter as a later liturgical Psalter supplement
- treat `The Psalms of David` as a later poetic/devotional Psalter supplement

Practical implication:

- the first usable vault keeps one consistent Mode 2 OT comparison strategy
- later Psalter-only layers can be added without changing the hub contract or global mode logic
- if one Psalter-only source is promoted earlier than the other, HTM has the stronger Orthodox/liturgical case, while `The Psalms of David` is the technically easier extraction target

## Phase 1 — Complete ✓

All 8 Phase 1 gates passed as of 2026-03-21.

| # | Item | Status |
|---|------|--------|
| 1 | Validator and structural correctness | ✓ Done |
| 2 | OSB hub text | ✓ Done |
| 3 | OSB notes companion layer | ✓ Done |
| 4 | Full-run OSB validation hardening (0 ERRORs) | ✓ Done |
| 5 | Lexham OT Mode 2 text companion | ✓ Done |
| 6 | EOB NT Mode 2 text companion | ✓ Done |
| 7 | NET notes-first layer | ✓ Done |
| 8 | Lectionary integration and pericope linking | ✓ Done |

## Concrete Build Order

### Phase 2 — Deferred Work (Wiring Already Built)

**2.1 EOB Notes companion layer ✓ Done (2026-03-21)**

- Wired in `extract_eob.py`; emits `{Book} {Ch} — EOB Notes.md` companions
- Sample output confirmed: `Matthew 1 — EOB Notes.md`, `John 1 — EOB Notes.md`, etc.

**2.2 Lexham Notes companion layer ✓ Done (2026-03-21)**

- `extract_lexham_notes.py` wires `read_notes()` → `render_notes()` → Lexham Notes companions
- Sample output confirmed: `Genesis 1 — Lexham Notes.md`, `Psalms 50 — Lexham Notes.md`, etc.

**2.3 Esdras B chapter-offset split (Lexham) ✓ Done (2026-03-21)**

- `lexham_epub.py` handles ES2 with chapter-offset mapping: chapters 1–10 → Ezra, 11–23 → Nehemiah (ch 1–13)
- Output confirmed: `output/Scripture/01 - Old Testament/16 - Ezra/`, `17 - Nehemiah/`

### Phase 2 — New Source Acquisition and Extraction

**2.4 Greek NT acquisition and adapter ✓ Updated (2026-03-22)**

- Source: GOArch Online Chapel — 1904 Antoniades Patriarchal Text, fully polytonic Unicode, Public Domain
  - Replaced: `byztxt/byzantine-majority-text` Robinson-Pierpont 2018 (scholarly, not liturgical)
- Adapter: `vault_builder/adapters/sources/goarch_greek_nt.py` (`GoArchGreekNtSource`)
  - 27 books, one request each (`?id={N}&book={abbr}&chapter=full`); rate limit 1.5 s
  - Handles Pattern A (linegroup) and Pattern B (inline) HTML verse structures
- Extract script: `extract_greek_nt_goarch.py` (supersedes `extract_greek_nt.py`)
- Output: `{Book} {Ch} — Greek NT.md` companion — file names unchanged; vault links valid
- Source label `"Greek NT"` unchanged; new frontmatter field `edition: "Antoniades 1904"` (planned)
- Gate: 26 adapter tests pass; 260 NT companion files written; full polytonic accents confirmed

**2.5 Greek OT (LXX) acquisition and adapter ✓ Done (2026-03-21)**

- Source: Rahlfs 1935 LXX via MyBible TSV (`LXX-Rahlfs-1935-master/11_end-users_files/MyBible/Bibles/LXX_final_main.csv`)
- Adapter: `vault_builder/adapters/sources/greek_lxx_csv.py` (`GreekLxxCsvSource`)
- Extract script: `extract_greek_lxx.py`; strips `<S>` and `<m>` morphological tags from TSV text
- Output: `{Book} {Ch} — LXX.md` companion; Psalter uses LXX primary numbering
- Nav: hub callout includes `LXX` for OT books; LXX companion self-suppresses its own link
- Gate: sample renders confirmed for `Genesis 1`, `Psalms 50`, `Psalms 151`, `Isaiah 7`

**2.6 Apostolic Fathers extraction ✓ Done (2026-03-22)**

- Source: `source_files/Commentary/Apostolic Fathers/The Apostolic Fathers.epub` (Holmes 3rd ed., 14 documents)
- Adapter: `vault_builder/adapters/sources/apostolic_fathers_epub.py`
- Extract script: `extract_apostolic_fathers.py`
- Output: `{output_root}/100-References/Apostolic Fathers/{Document}/`
- Per-chapter files (`1 Clement 4.md`) with verse anchors (`^{ch}-{verse}`), inline footnotes as blockquotes
- Scripture cross-refs in footnotes auto-linked to vault hubs: `[[Genesis 4#v3|Gen. 4:3–8]]`
- Deferred: Shepherd of Hermas (3-book structure), Papias Fragments (no chapter structure)
- Structure doc: `docs/apostolic-fathers-source-structure.md`

**2.7 Psalter-specific supplements**

*HTM Psalter (liturgical)*

- Source: `source_files/Psalms/HTM Psalter.pdf` (19 MB)
- Contains: kathisma framing, doxologies, the nine odes, recitation guidance
- Modeling: liturgical Psalter layer — separate from Mode 2 slot; adds kathisma/ode structure
- PDF extraction will require page-range analysis (similar to NET/EOB PDF approach)

*The Psalms of David (poetic/devotional)*

- Source: `source_files/Psalms/The Psalms of David.epub` (8.9 MB EPUB — preferred format)
- Contains: per-Psalm headings, verse numbers, kathisma groupings, sparse footnotes
- Modeling: poetic/devotional Mode 2 supplement for Psalms only
- Task: audit EPUB structure first; this is technically the easier extraction target of the two

### Phase 2 — NOAB RSV Status

**NOAB RSV — ⚠ Extraction Incomplete (updated 2026-03-25)**

- Source: `source_files/New Oxford Annotated Bible with Apocrypha RSV.pdf` (~2032 pages)
- Adapter: `vault_builder/adapters/sources/noab_pdf.py` (`NoabPdfSource`)
- Extract script: `extract_noab.py`
- Slot in nav: RSV (3rd position, after OSB and EOB/Lexham)
- **Status: DO NOT include in full runs.** Known extraction quality problems:
  - OCR artifacts bleeding into verse text (e.g. `HE BOOK` for `THE BOOK`, stray footnote sigla)
  - Multi-verse merging: entire genealogies or poetry stanzas collapsed into a single verse block
  - GlyphLessFont encoding: verse numbers in some fonts render as non-digit characters, silently dropping verse boundaries (Genesis 1 yields ~15–20 of 31 verses)
  - Psalms excluded from sample due to verse contamination across adjacent short Psalms on shared pages
- Recent refactor note:
  - `pdfplumber`-based extraction, column-major sorting, lazy OCR verse-number recovery, and drop-cap handling improved the baseline substantially
  - even after that refactor, overall quality is still not good enough to treat NOAB as production-ready; expect further work before any promotion
- **Gate before full run:** extraction must produce clean per-verse text with no merge artifacts and ≥ 95% verse boundary detection across representative sample chapters
- **Future target:** keep NOAB as a two-artifact source once it is viable: `{Book} {Ch} — NOAB RSV.md` plus `{Book} {Ch} — NOAB RSV Notes.md`
- **Immediate plan:** finish the NOAB note-family audit, harden the text-verification bar, stabilize chapter-local verse recovery, and only then add notes extraction / nav exposure
- See `docs/noab-pdf-source-structure.md` for detailed structural notes and known issues

### Phase 2 — Secondary Comparison Layers

These are lower priority; assess only after Greek and deferred-wiring work is complete.

**EOB OT**

- Source: `source_files/Old Testament/EOB OT.pdf` (7.6 MB)
- More structurally cumbersome than Lexham; keep as secondary Orthodox OT comparison layer
- Promote only if extraction quality proves strong enough to prefer over Lexham

**DBH (David Bentley Hart NT)**

- Source: `source_files/New Testament/DBH.epub` (4.4 MB)
- A literal NT translation with strong Greek fidelity — potential second NT Mode 2 layer
- Not assessed for EPUB structure yet; treat as lower-priority Phase 2 item

**Robert Alter (OT)**

- Source: `source_files/Old Testament/Robert Alter.epub` (32 MB — large)
- Literary/scholarly OT translation with extensive commentary
- Not assessed for EPUB structure yet; treat as lower-priority Phase 2 item

**Philokalia**

- Source: `source_files/Commentary/Philokalia volumes` (PDFs)
- Readable OCR prose with numbered sections and Scripture citations
- Not naturally chapter-commentary shaped; keep distributed and manual

### Phase 2 — Cross-Cutting Enhancements

These affect multiple source adapters and the renderer. Not gating on any single source.

**Italic formatting preservation**

- All three text adapters (OSB, EOB, Lexham) currently extract `<i>` as plain text
- OSB: italics mark words added for clarity not in Greek/Hebrew — semantically meaningful
- EOB: italics mark titles and foreign terms
- Lexham: similar translator conventions
- Enhancement: preserve as `*text*` in verse output; add a `_to_md_inline()` helper shared across adapters

**Poetry line-break formatting**

- EOB `poetry1cxsp*` paragraphs are collected as verse continuations without line breaks
- Rendered output loses the poetic line structure (e.g., Magnificat in Luke 1)
- Enhancement: add `\n` between poetry continuation paragraphs so Markdown renders as separate lines

**Provenance-aware rendering for OSB aux families**

- `alternative.html` (5 notes), `background.html` (2 notes), `translation.html` (4 notes) are ingested but their source bucket is folded into `variants`/`footnotes`
- At render time, all are treated identically to their bucket's callout style
- Enhancement: add `provenance` field to `StudyNote` and thread through renderer to use distinct callout types (`[!alt]`, `[!bg]`, `[!xlation]`)
- Low priority (11 notes total); document decision before implementing

**verse_end in renderer**

- `StudyNote.verse_end` is defined in the domain model and set by OSB for cross-chapter pericopes
- Renderer never reads `verse_end` — the field has no effect on output
- Enhancement: use `verse_end` to group notes into their actual pericope heading (e.g., `v18–2:2` heading for a cross-chapter range)

**StudyArticle subtype distinction**

- OSB inline study articles contain `ext` (quoted excerpts), `ul2` (list items), and `sub1` (subheadings) paragraphs
- Currently all rendered as plain body text paragraphs — structural distinction lost
- Enhancement: map `ext` → blockquote (`> …`), `ul2` → list item (`- …`), `sub1` → bold heading or `####`

## Acceptance-Gated Sequence

### Phase 1 Gates — All Passed ✓ (2026-03-21)

| Gate | Status |
|------|--------|
| Validator passes on representative sample fixtures | ✓ |
| Full-run OSB validation (0 ERRORs, completeness-aware) | ✓ |
| OSB hubs: one verse per anchor, inline vN styling, `#vN` + `^vN` both present | ✓ |
| OSB notes: verse-ordered, source provenance preserved, no category-first layout | ✓ |
| Lexham OT: representative chapters clean, footnote sigla stripped from verse body | ✓ |
| EOB NT: no page bleed, `{word}` notation preserved, appendix guard active | ✓ |
| NET: notes-first files readable, semantic note types preserved | ✓ |
| Lectionary: pericope links resolve, cross-chapter ranges safe | ✓ |

### Phase 2 Gates

#### EOB Notes companion (2.1)

- `extract_eob.py` calls `read_notes()` and writes `{Book} {Ch} — EOB Notes.md`
- companion frontmatter includes `source: "EOB"` and correct `hub` link
- validator recognizes EOB Notes companions (new rule) and checks structural correctness
- representative NT chapters verified: `John 1`, `Romans 8`, `I Corinthians 13`

#### Lexham Notes companion (2.2)

- `extract_lexham.py` calls `read_notes()` and writes `{Book} {Ch} — Lexham Notes.md`
- 1,150 footnotes correctly attributed to verse and book
- validator checks Lexham Notes companion presence for chapters with known notes

#### Esdras B split (2.3)

- Lexham ES2 chapters 1–10 emit as Ezra chapters 1–10
- Lexham ES2 chapters 11–23 emit as Nehemiah chapters 1–13
- validator accepts Ezra and Nehemiah Lexham companions as structurally valid

#### Greek NT (2.4)

- sources present locally under `source_files/Greek/NT/`
- provenance note recorded
- `John 1`, `Matthew 5`, `Romans 8` render with stable `#vN` anchors

#### Greek OT / LXX (2.5)

- sources present locally under `source_files/Greek/OT/`
- provenance note recorded
- `Genesis 1`, `Psalms 50`, `Isaiah 7` render with stable anchors
- Psalter numbering uses LXX primary (coherent with vault)

#### Apostolic Fathers (2.6)

- EPUB structure audited and documented in `docs/apostolic-fathers-source-structure.md`
- modeling decision recorded (distributed-notes vs. catena files)
- at least one author's texts render against the verse-linking contract

#### Psalter supplements (2.7)

- at least one Psalter supplement (HTM or Psalms of David) emits per-Psalm companions
- kathisma/ode structure (HTM) or verse groupings (Psalms of David) preserved in output
- supplement companions link to hub verse anchors correctly

## Manual Greek Acquisition Checklist

### Target Local Paths

- `source_files/Greek/NT/greektext-antoniades/`
- `source_files/Greek/NT/byzantine-majority-text/`
- `source_files/Greek/NT/robinson-documentation/`
- `source_files/Greek/OT/LXX-Rahlfs-1935/`
- `source_files/Greek/_provenance/`

### Checklist

1. Acquire `byztxt/greektext-antoniades`.
2. Acquire `byztxt/byzantine-majority-text` if comparative NT work is desired.
3. Acquire `byztxt/robinson-documentation`.
4. Complete CCAT declaration and obtain the OT Greek dataset in a locally usable form.
5. Save a provenance note for each source including:
   - name
   - origin
   - date acquired
   - local path
   - license summary
   - caveats
6. Verify the NT dataset includes:
   - book
   - chapter
   - verse
   - Greek text
   - morphology and/or Strong's-related fields
7. Verify the OT dataset includes:
   - book
   - chapter
   - verse
   - Greek text
   - promised morphology/gloss fields
8. Add a short `README.md` under `source_files/Greek/` naming the authoritative NT and OT Mode 4 datasets.

### Minimum Verification Examples

- NT: `John 1:1`, `Matthew 5:3`, `Romans 8:28`
- OT: `Genesis 1:1`, `Psalms 50:1`, `Isaiah 7:14`, and a Daniel additions representation check

## Phase 1 Source Fixture Matrix — Complete ✓

| Source / Layer | Required Fixtures | Status |
|----------------|-------------------|--------|
| OSB hub text | `Genesis 1`, `Psalms 50`, `Sirach 1`, `John 1`, `Romans 8` | ✓ |
| OSB notes | `Genesis 1 — OSB Notes`, `John 1 — OSB Notes`, `Romans 8 — OSB Notes`, `Sirach 1 — OSB Notes` | ✓ |
| Lexham OT Mode 2 | `Genesis 1`, `Psalms 50`, `Isaiah 7`, `Sirach 1` | ✓ |
| EOB NT Mode 2 | `Matthew 1`, `John 1`, `Romans 8`, `James 1` | ✓ |
| NET notes-first layer | `John 1`, `Romans 8`, `Psalm 1`, `Acts 15` | ✓ |
| Lectionary links | cross-chapter pericope, single verse, multi-block | ✓ |

## Phase 2 Source Fixture Matrix

| Source / Layer | Required Fixtures |
|----------------|-------------------|
| EOB Notes companion | `John 1 — EOB Notes`, `Romans 8 — EOB Notes`, `I Corinthians 13 — EOB Notes` |
| Lexham Notes companion | `Genesis 1 — Lexham Notes`, `Psalms 50 — Lexham Notes`, `Sirach 1 — Lexham Notes` |
| Greek NT | `John 1 — Greek`, `Matthew 5 — Greek`, `Romans 8 — Greek` |
| Greek OT / LXX | `Genesis 1 — LXX`, `Psalms 50 — LXX`, `Isaiah 7 — LXX` |
| Apostolic Fathers | at least one author, two representative chapters |
| HTM Psalter | `Psalms 1 — HTM`, `Psalms 50 — HTM`, one kathisma boundary |
| Psalms of David | `Psalms 1 — Psalms of David`, `Psalms 50 — Psalms of David` |

## Related Documents

- `Orthodox-Vault-Goals.md`
- `docs/implementation-architecture.md`
- `docs/validation-plan.md`
- `docs/osb-epub-source-structure.md`
