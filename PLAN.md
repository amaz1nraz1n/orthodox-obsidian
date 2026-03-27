# Source Audit & Build Skills — Implementation Plan

## Architecture Decisions

- **Project-local skills**: Skills live in `.claude/skills/{name}/SKILL.md` (project-local, version-controlled with the repo, same format as global `~/.claude/skills/`). Invoked as `/audit-source` and `/build-source`. Project skills take priority over any global skill of the same name.
- **sources.yaml at project root**: Central source registry mapping short names → path, format, structure_doc, adapter, extract_script, testament, status. Replaces scattered `DEFAULT_EPUB`/`DEFAULT_PDF` constants as a future cleanup — not required to unblock these skills.
- **`/audit-source` = raw inspection only**: Never runs extractor code. Always reads raw EPUB/PDF/CSV files directly. Mode-aware: additive (existing structure doc found) vs. full audit (new source).
- **`/build-source` = TDD loop + LLM exam + sync**: Reads structure doc → writes tests → writes adapter → runs extraction → iterates → LLM examination → rsync to Google Drive. Bead stays open after sync; re-invocation resumes from post-sync phase (no `--verify` flag needed).
- **Sub-verse markers**: Passively documented in structure doc during audit. No interactive decision point.
- **Decision presentation in audit**: Batch — collect all findings first, present all decisions at the end in one block.

---

## Phases

### Phase 1: sources.yaml Registry
- [x] **Goal**: Create a central YAML registry mapping all 8 source short-names to their file paths, formats, structure docs, adapters, and status.
- **Files**:
  - `sources.yaml` (create)
- **Dependencies**: none
- **Testing**: `python3 -c "import yaml; s = yaml.safe_load(open('sources.yaml')); print(list(s['sources'].keys()))"` — should print all 8 source names. Manually verify each `path` resolves on disk.
- **Commit**: `"feat: add sources.yaml central source registry"`

---

### Phase 2: /audit-source Command
- [x] **Goal**: Create a project slash command that raw-inspects any registered source, collects structural findings, runs user spot-checks, presents batch decisions, and updates the source structure doc.
- **Files**:
  - `.claude/skills/audit-source/SKILL.md` (create)
- **Dependencies**: Phase 1
- **Skill behavior** (to encode in the command prompt):
  1. **Lookup**: Read `sources.yaml`. Resolve source by name. If name not found, list available sources and exit.
  2. **Mode detection**: If `docs/{source}-source-structure.md` exists → additive/verify mode. Else → full audit mode. State mode clearly at start.
  3. **Raw inspection**:
     - EPUB: `zipfile.ZipFile` → read OPF (`content.opf` or `package.opf`) → iterate spine items → parse HTML with BeautifulSoup → identify verse markers, chapter markers, footnote/`<sup>` markers, pericope headings, section headings, intro material. Document inline marker types passively (class names, href patterns, element types) without making a decision.
     - PDF: `pdfminer.high_level.extract_pages` → classify text boxes by font size and position → identify page headers, verse text, footnotes, pericope headings.
     - CSV/TSV: Read first 20 rows → identify columns, delimiter, verse/chapter fields, text encoding.
     - Web: Fetch one sample chapter URL → inspect HTML structure.
  4. **Example extraction**: Pull 3 real verse samples — one from chapter 1 of first book, one from a middle chapter, one from a known reference verse (John 1:1 for NT, Genesis 1:1 for OT, Psalm 50:1 for Psalter).
  5. **Spot-check questions**: Present extracted samples as targeted yes/no questions the user answers by checking the open source file. E.g.: "Does John 1:1 read: '[extracted text]'? Do you see a pericope heading '[heading]' before verse 1? Do you see inline markers like 'a' or '†' in the verse text?"
  6. **Collect all decisions**: After spot-checks, list all open decisions in a single batch block. For each: state what was found, options, and ask for user input. E.g.: "Inline footnote markers found (`<sup>a</sup>` with href links to footnote definitions). Preserve word-position + link? Or strip as currently done?"
  7. **Update structure doc**: In additive mode — add gap sections only, annotate existing claims with ✓ verified / ✗ needs update. In full audit mode — write the complete structure doc from findings.
  8. **Approval gate**: Ask "Is this source approved for extraction?" If yes: update `status: approved` in `sources.yaml` and update the CLAUDE.md source table row for this source.
  9. **Beads**: Create bead at start (`bd create --title "audit-source: {name}"`), update after spot-checks, close with decision summary.
- **Testing**: Invoke `/audit-source osb` — should run in additive mode, surface existing structure doc gaps, ask spot-check questions about OSB verses, and not overwrite existing documented decisions.
- **Commit**: `"feat: add /audit-source project command"`

---

### Phase 3: /build-source Command
- [x] **Goal**: Create a project slash command that reads a source's structure doc, runs a TDD loop to build or improve the adapter, performs LLM examination of output, and syncs to Google Drive.
- **Files**:
  - `.claude/skills/build-source/SKILL.md` (create)
- **Dependencies**: Phase 1, Phase 2 (structure doc must exist for target source)
- **Skill behavior** (to encode in the command prompt):
  1. **Lookup**: Read `sources.yaml`. Resolve source. Check that `structure_doc` exists — if not, tell user to run `/audit-source {name}` first.
  2. **Resume detection**: Check for an open bead titled `"build-source: {name}"`. If found and status is `in_progress` with notes indicating post-sync phase → skip to **Manual verification loop** step. Otherwise start from TDD loop.
  3. **TDD loop**:
     - Read structure doc to understand: verse marker patterns, chapter markers, pericope extraction, footnote handling, known verse counts for sample chapters.
     - Write pytest tests in `tests/test_{adapter_name}_extraction.py` and `tests/test_{adapter_name}_rendering.py` covering: verse count assertions, known verse text (e.g. John 1:1 expected text), pericope presence, frontmatter fields, companion file naming.
     - Write or update adapter in `vault_builder/adapters/sources/{adapter}.py` to pass tests.
     - Run extraction on sample chapters: `.venv/bin/python3 extract_{name}.py` (sample mode).
     - Run tests: `.venv/bin/python3 -m pytest tests/test_{adapter_name}_*.py -v --tb=short`.
     - Iterate on failures — fix adapter or tests — until all pass.
  4. **LLM examination**: Read output files for key chapters. Check the following per testament/genre:
     - NT prose (John 1): John 1:1 should read approximately "In the beginning was the Word…"
     - OT Torah (Genesis 1): Gen 1:1 should read approximately "In the beginning God created…"
     - OT Psalter (Psalm 50 LXX): Ps 50:1 should read approximately "Have mercy on me, O God…"
     - OT Prophet (Isaiah 7): Isa 7:14 should read approximately "…a virgin shall conceive…"
     - Apocalyptic (Revelation 1): Rev 1:1 should open with "The Revelation of Jesus Christ…"
     - Check for: OCR artifacts (stray characters, digit substitutions), merged verses (multiple verse numbers in one block), encoding issues (replacement chars, garbled Unicode), "text smells" (lines that are clearly not Scripture text, footnote bleed, header bleed).
     - Report all findings. Iterate adapter if critical issues found.
  5. **Google Drive sync**: `rsync -av output/Scripture/ "~/Library/CloudStorage/GoogleDrive-jmtharp90@gmail.com/My Drive/Jasper/Holy Tradition/Holy Scripture/"`
  6. **Bead update**: Update bead notes with "Synced to Google Drive. Awaiting manual verification." Leave bead open.
  7. **Manual verification loop**: When re-invoked with open bead in post-sync state — ask: "Did the manual verification reveal issues? If yes, describe them." Take issues as input, iterate adapter, re-run tests, re-sync, update bead, leave open again. Repeat until user confirms clean.
  8. **Completion**: User confirms clean → close bead → update `sources.yaml` status if changed.
- **Testing**: Invoke `/build-source noab` (known issues source — good stress test). Should detect existing adapter, write tests that expose known problems (verse merge, OCR artifacts), surface them in LLM examination report.
- **Commit**: `"feat: add /build-source project command"`

---

## Open Items (post-Phase 3)

- **Extractor script cleanup**: Replace `DEFAULT_EPUB`/`DEFAULT_PDF` constants in each `extract_*.py` with a lookup from `sources.yaml`. Low priority — doesn't affect skills functionality.
- **Sub-verse marker decision**: After running `/audit-source` on OSB and Lexham, the batch decision output will surface whether to preserve inline marker positions. That decision drives a follow-on implementation task, not these skills.
- **RSV Notes slot**: Deferred until NOAB RSV extraction quality is resolved (see `docs/source-roadmap.md`).
