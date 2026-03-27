# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Beads

`.beads/` is tracked in git for this repo. Commit it as part of normal git workflow. This overrides the global stealth-mode rule.

## Linear

Issue tracking: **Linear workspace `tharp-personal`, team `PER`**. Config in `.linear.toml`.

### Structure

```
Workspace: tharp-personal
  Team: PER (Personal)
    Project: Orthodox Obsidian Vault  (slugId: 2b159ac7c42c)
      Milestone: Phase 1 — Core Sources   (complete)
      Milestone: Phase 2 — New Sources    (active: Alter, DBH, NOAB)
      Milestone: Phase 3 — Vault Polish   (nav, linking, validator)
```

### Issue conventions

- One issue per discrete source adapter or feature
- Assign to the appropriate milestone when creating
- Priority: 1=urgent, 2=high, 3=medium, 4=low
- Use `--project "Orthodox Obsidian Vault"` and `--milestone "<name>"` on `linear issue create`
- Do NOT use `--start` — it auto-creates a git branch and switches to it

### Useful commands

```bash
linear issue list                          # open issues assigned to me
linear issue list -A --all-states          # everything
linear issue create --title "..." --priority 2 --project "Orthodox Obsidian Vault" --milestone "Phase 2 — New Sources"
linear issue update PER-XX --state "In Progress"
linear project view 2b159ac7c42c          # project overview
```

### GitHub integration

Not connected. Issues are managed via CLI only. Reference Linear issue IDs in commit messages (e.g. `PER-10`) for traceability.

## Project Overview

Orthodox Obsidian vault builder — Python scripts that extract Scripture from EPUB/PDF sources and generate Obsidian-formatted Markdown notes for an Eastern Orthodox personal study vault.

Planning docs:

- `Orthodox-Vault-Goals.md` — north-star goals, principles, major decisions
- `docs/implementation-architecture.md` — adapter/model/renderer implementation decisions
- `docs/source-roadmap.md` — source status, phase roadmap, acquisition planning
- `docs/validation-plan.md` — validator rules, fixtures, execution policy
- `docs/{source}-source-structure.md` — per-source EPUB/PDF structural audit notes (one file per source)

Source registry:

- `sources.yaml` — canonical registry of all source files: short name → path, format, testament, structure_doc, adapter, extract_script, status. Used by `/audit-source` and `/build-source` skills.

## Current State

Phase 1 complete as of 2026-03-21. All 8 Phase 1 gates passed (see `docs/source-roadmap.md`).

Active sources (adapter + extract script + tests):
- **OSB** — hub files + OSB Notes companions (canonical text, study articles, footnotes, cross-refs, lectionary, patristics)
- **Lexham** — OT text companions + Lexham Notes companions
- **EOB** — NT text companions + EOB Notes companions
- **NET** — Full Bible translator's notes companions (NET Notes; NET text file is support-only, not in nav)
- **Greek NT** — GOArch 1904 Antoniades Patriarchal Text (polytonic Unicode, live scrape)
- **Greek OT (LXX)** — Rahlfs 1935 via MyBible TSV
- **Apostolic Fathers** — Holmes 3rd ed. EPUB; output to `100-References/Apostolic Fathers/`
- **Lectionary** — OCMC CSV; pericope linking in hub files

Incomplete / gated:
- **NOAB RSV** — adapter exists but gated from full runs; OCR artifacts, verse merging, GlyphLessFont issues (see `docs/noab-pdf-source-structure.md`)

Not yet started (status: new): KJV, NJB, DBH NT, Robert Alter OT, EOB OT, Psalms of David, HTM Psalter, Philokalia

Test harness: `tests/` pytest suite (unit + integration); `scripts/validate_output.py` for generated Markdown.

## Running Scripts

All extract scripts live in `scripts/`. See `README.md` for the full Quick Start. Key scripts:

```bash
# Extraction (sample mode — representative chapters to output/Scripture/)
.venv/bin/python3 scripts/extract_osb.py
.venv/bin/python3 scripts/extract_lexham.py
.venv/bin/python3 scripts/extract_eob.py
.venv/bin/python3 scripts/extract_net.py
.venv/bin/python3 scripts/extract_greek_nt_goarch.py   # live web scrape — rate limited
.venv/bin/python3 scripts/extract_greek_lxx.py
.venv/bin/python3 scripts/extract_apostolic_fathers.py

# Full OSB run (entire Bible → output/Scripture-full/)
.venv/bin/python3 scripts/extract_osb.py --full

# Validate generated output
.venv/bin/python3 scripts/validate_output.py output/Scripture/

# Inspect EPUB internals (debugging)
.venv/bin/python3 scripts/inspect_epub.py

# Sync to live Obsidian vault
rsync -av output/Scripture/ "~/Library/CloudStorage/GoogleDrive-jmtharp90@gmail.com/My Drive/Jasper/Holy Tradition/Holy Scripture/"
```

Notes:
- sample runs → `output/Scripture/`; full runs → `output/Scripture-full/` (don't overwrite sample)
- `extract_greek_nt_goarch.py` supersedes `extract_greek_nt.py` (old Byzantine CSV adapter)
- `extract_lexham_notes.py` is a standalone notes-only run; `extract_lexham.py` also emits notes in the same pass
- Dependencies: see `requirements.txt` (`beautifulsoup4`, `lxml`, `pyyaml`, `pdfminer.six`)

## Architecture

The project follows a **Ports & Adapters (Hexagonal)** architecture with a DDD-inspired domain core.

```
vault_builder/
  domain/   # Plain data objects (Book, Chapter, Verse, StudyNote)
  ports/    # Interfaces (ScriptureSource, VaultRenderer)
  adapters/
    sources/  # osb_epub, lexham_epub, eob_epub, net_epub, goarch_greek_nt,
              # greek_lxx_csv, apostolic_fathers_epub, noab_pdf (incomplete)
    obsidian/ # Markdown renderer + writer
```

### Output Structure

```
Scripture/
  01 - Old Testament/
    {Order} - {BookName}/
      {BookName} {Chapter}.md            # Chapter Hub (canonical text)
      {BookName} {Chapter} — OSB Notes.md # Companion Notes (study content)
  02 - New Testament/
```

### Chapter Hub Format (canonical, do not alter structure)

Hub files contain **only** canonical text, H6 verse anchors, and breadcrumb frontmatter.

- **Frontmatter**: required `testament`, `genre`, `book_id`, `aliases`, `up`, `prev`, `next`; optional `mt_ref`, `lxx_ref` only when a modeled reference-system divergence matters
- **Nav callout**: see canonical nav order in `docs/implementation-architecture.md` § "Shared Navigation Contract". Hub nav is comprehensive (all modes + all notes). Companion navs are scoped: Hub · own notes · NET Notes only. NET text is not in the nav; accessible inline from NET Notes files only.
- **Verses**: one real verse per anchor, with canonical linking still resolving as `[[Book Chapter#vN]]`
- **Reading layout**: the visible verse number should be styled inline with the verse text for normal Bible reading flow, typically via `.vn` styling, rather than rendering the number as a detached heading line above a separate paragraph
- **Secondary stability anchor**: preserve a hidden per-verse block ID such as `^vN` when possible; it is useful for compatibility, transclusion, and implementation flexibility, but it does not replace the canonical external link contract
- **Regression guard**: do not restore the older broken grouped-verse behavior where one heading swallowed multiple verses, visible verse numbers were wrong, or verse digits leaked into the verse body like `1In...`

Chapter 1 hub also includes `intro:` frontmatter pointing to the source intro file when one exists (e.g. `intro: "[[John — OSB Intro]]"`). Other chapters omit this field.

```markdown
---
testament: "NT"
genre: "Gospel"
book_id: "Jn"
aliases: ["Jn 1"]
up: "[[John]]"
prev: ""
next: "[[John 2]]"
intro: "[[John — OSB Intro]]"
---
> **Modes:** [[John 1|OSB]] · [[John 1 — EOB|EOB]] · [[John 1 — RSV|RSV]] · [[John 1 — Greek NT|Greek NT]] · [[John 1 — NET Notes|NET Notes]] · [[John 1 — EOB Notes|EOB Notes]] · [[John 1 — OSB Notes|Study Notes]]

###### v1
<span class="vn">1</span> In the beginning was the Word, and the Word was with God, and the Word was God. ^v1
```

### Companion Notes

Named `{BookName} {Chapter} — {Source} Notes.md`.
- **Frontmatter**: required `hub: "[[HubLink]]"`, `source: "SourceName"`; recommended `layer_type`, `book`, `chapter`, `cssclass`
- **Heading links**: Link back to hub verse anchors using `### [[{Book} {Ch}#v{N}|{Ref}]]`
- **Ordering rule**: Render companion content in verse/pericope order, not in large top-level sections by note family. Keep note-type distinction via callouts/CSS within each verse block.
- **Nav scope rule**: Companion navs are scoped — each shows only: Hub (back link) · own notes companion (if applicable) · NET Notes. Do NOT replicate the full hub nav in companion files.
- **NET text**: The NET text companion (`{Book} {Ch} — NET.md`) is not linked in any nav. It is accessed via an inline link within the NET Notes file only. NET Notes is linked in all files as universal apparatus.
- **Schema note**: Generic fields like `type: commentary` may be added later for convenience, but they must not replace the established `hub` / `source` metadata or the normalized per-entry data model.
- **Scope note**: This companion-file pattern applies to imported source layers like OSB, NET, Fathers, and Greek. Personal reflections remain distributed across `000-Zettelkasten/`, `500-Orthodox-Life/`, class notes, homily notes, etc., and link back to hub verses rather than living in a generated per-chapter companion file.
- **Layer note**: Not every imported layer needs both a full-text companion and a notes companion. Default bias: emit the artifact that carries the real value. For NET that is usually the translator apparatus first; for Fathers, generate a chapter companion only when the source material is actually verse/pericope-addressable enough to justify one.

## Critical Conventions

**Verse anchor format is non-negotiable:** `[[John 1#v14]]` — the `v` prefix prevents collisions with internal Obsidian numbering and must be used everywhere (import scripts, templates, linking scripts).

**Secondary block IDs:** hidden per-verse block IDs such as `^v14` may coexist in hub output and are desirable as a secondary anchor/stability layer, but they are not the canonical citation format for the vault.

**Hub scope rule:** Chapter hub files contain ONLY canonical text and H6 verse anchors. All other content lives in companion notes.

**Psalter versioning:** LXX numbering is primary. `Psalm 50.md` = "Have mercy on me, O God" (MT Ps 51). MT equivalents go in `aliases`.

**Reference-system metadata:** `mt_ref` and `lxx_ref` are not universal boilerplate. Use them only when a chapter's stable reference differs across traditions and that divergence is being modeled for automation. Current required case: Psalms, with LXX primary and MT stored separately.

**Canon:** Full Orthodox canon (73+ books). Deuterocanonical books are treated as fully canonical and live under `01 - Old Testament/`; distinction is carried by frontmatter, not a separate top-level Scripture folder.

**Foldering rule:** `03 - Anagignoskomena/` is no longer the intended target structure. Future extraction and validation should treat any generated Deuterocanonical path outside `01 - Old Testament/` as a structural error.

**EPUB verse ID pattern:** `{prefix}_vchap{chapter}-{verse}`. Prefix mapping is in `PREFIX_TO_BOOK` in `osb_epub.py`.

## Key Design Decisions (from Orthodox-Vault-Goals.md)

- **Linking format:** `[[Book Chapter#vN]]` everywhere; retroactive linking script will convert plain-text citations in existing notes
- **Psalm numbering source of truth:** LXX; concordance table maps MT→LXX at import boundary
- **Psalter comparison layers:** Lexham remains the default Phase 1 OT Mode 2 source, including Psalms. HTM Psalter and `The Psalms of David` are later Psalter-specific supplements rather than early replacements for the main OT comparison layer.
- **Copyrighted content isolation:** OSB notes, NETS text etc. in clearly named frontmatter fields (`osb_note:`, `nets_text:`) for future public-vault export stripping
- **Folder:** `100-References/Pseudepigrapha/` for OT Pseudepigrapha (not under `Scripture/`)
- **Avoid NRSV** — not used in any Antiochian/GOA/OCA liturgical context

## Planned Scripts (not yet built)

- Retroactive citation linker: parse existing vault notes, replace plain-text Scripture references with wikilinks
- `psalter-concordance.json`: MT↔LXX verse-level mapping (~90 psalms with offsets)
- Extraction log writer: per-book `_extraction-log.md` documenting transformations

## Source Registry

`sources.yaml` at project root is the canonical registry of all source files. Every source has a short name (e.g., `osb`, `eob`, `lexham`, `kjv`) mapped to:

- `path` — file path or URL
- `format` — `epub`, `pdf`, `csv`, `web`
- `testament` — `ot`, `nt`, or `both`
- `structure_doc` — path to `docs/{source}-source-structure.md` (null if not yet audited)
- `adapter` — Python module path (null if not yet built)
- `extract_script` — script filename in `scripts/` (null if not yet built)
- `status` — `approved`, `incomplete`, `new`, `reference`, `superseded`, or `extracted`

Status meanings: `approved` = working adapter included in vault builds; `incomplete` = adapter exists but gated from full runs; `new` = file acquired, no adapter yet; `reference` = available for reference, not an extraction target; `superseded` = replaced by a better-format equivalent; `extracted` = fully integrated via dedicated script.

Do not hardcode source file paths in scripts. Use `sources.yaml` lookups (cleanup of existing `DEFAULT_EPUB`/`DEFAULT_PDF` constants is deferred).

## Claude Code Skills

Project-local skills live in `.claude/skills/{name}/SKILL.md`. They are version-controlled with the repo and take priority over any global skill of the same name.

### `/audit-source [source-name]`

Raw-inspects a registered source (EPUB/PDF/CSV/web) and produces or updates its structure doc.

- Looks up the source in `sources.yaml`
- **Additive mode** (structure doc exists): fills gaps and verifies existing claims
- **Full audit mode** (no structure doc): writes a complete new `docs/{source}-source-structure.md`
- Inspects raw files directly — never runs the extractor
- Extracts 3 verse samples, presents spot-check questions, then collects all decisions in one batch
- On approval: updates `sources.yaml` status and CLAUDE.md source table

### `/build-source [source-name]`

Builds or improves a source adapter using a TDD loop, then syncs output to Google Drive.

- Requires an existing structure doc (`/audit-source` must run first)
- Reads the structure doc, writes failing tests, writes adapter code, iterates until passing
- LLM-examines key verses (John 1:1, Gen 1:1, Ps 50:1, Isa 7:14, Rev 1:1) for correctness
- Syncs output via rsync to Google Drive after passing LLM examination
- Bead stays open after sync — re-invoking resumes at manual verification rather than restarting

### `/verify-source [source-name] [--sync]`

Verifies an existing source adapter without building anything.

- Requires an adapter and extract script to already exist (`/build-source` must have run first)
- Runs existing tests, runs sample extraction, LLM-examines canonical check verses
- Produces a structured PASS / WARN / FAIL quality report
- Compares output against known gaps in the structure doc — flags new issues, notes resolved ones
- Pass `--sync` to sync output to Google Drive if the result is PASS or WARN
- Use after code changes, before syncing, or to periodically re-verify approved sources

## Full-Run Validation Note

The current validator checks whatever Markdown exists under the selected Scripture root. That is sufficient for sample validation but not for trusted full-OSB signoff.

Before treating a full OSB extraction as a gate:

- support a separate full-run output root
- add completeness-aware validator behavior that checks expected hubs and expected `OSB Notes` companions against canonical chapter metadata
