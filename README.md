# Orthodox Obsidian Vault Builder

Python pipeline that extracts Scripture text and study notes from EPUB/PDF sources
and generates Obsidian-formatted Markdown for an Eastern Orthodox personal study vault.

## Current Focus

- Core extraction architecture is in place and the main source stack is already usable.
- Linear currently shows Phase 3 as the active execution lane, with Phase 2, Phase 4, and Phase 5 queued/backlog.
- Current work is centered on output quality, note polish, and navigation refinement rather than raw source count.
- NOAB RSV remains explicitly gated: the PDF is still too noisy for trustworthy routine extraction, even after recent parser improvements.
- The next practical wins are:
  - finishing parallel-passage and citation-routing work
  - improving hub-to-notes navigation and companion discoverability
  - keeping Phase 2 source additions queued unless they have a clear audited path and approved slot
  - keeping NOAB quality gating and interlinear work in their dedicated later-phase lanes

## Linear Board Snapshot

- Phase 1 — Core Sources: complete.
- Phase 2 — New Sources: backlog/queued; Alter, DBH NT, NOAB RSV, and related source assessment work live here.
- Phase 3 — Vault Polish: active; current issues cover parallel passages, citation routing, and companion discoverability.
- Phase 4 — Photocopy PDF Sources: backlog; NOAB quality gating and OCR cleanup live here.
- Phase 5 — Interlinear Hubs: backlog; dynamic/embedded interlinear work lives here.

## Project Layout

```
orthodox-obsidian/
├── sources.yaml           # Central source registry (all EPUB/PDF/CSV sources)
├── source_files/          # Source EPUB/PDF files (not committed)
│   ├── Full Bible/        # OSB, NET 2.1, KJV, NJB, NOAB PDFs
│   ├── Old Testament /    # Lexham EPUB, EOB OT PDF, Robert Alter EPUB
│   ├── New Testament/     # EOB NT EPUB, DBH NT EPUB
│   ├── Psalms/            # HTM Psalter PDF, Psalms of David EPUB
│   ├── Greek/             # LXX Rahlfs CSV, Antoniades repo, Byzantine Majority Text
│   ├── Commentary/        # Apostolic Fathers EPUB+PDF, Philokalia PDFs
│   └── Lectionary/        # OCMC lectionary CSV
├── output/                # Generated Markdown (not committed)
│   ├── Scripture/         # Sample extraction output
│   └── Scripture-full/    # Full-run extraction output
├── vault_builder/         # Core library (Ports & Adapters)
│   ├── domain/            # Plain data models (Book, Chapter, Verse, StudyNote)
│   ├── ports/             # Interfaces (ScriptureSource, VaultRenderer)
│   └── adapters/
│       ├── sources/       # osb_epub, lexham_epub, eob_epub, net_epub,
│       │                  # goarch_greek_nt, greek_lxx_csv,
│       │                  # apostolic_fathers_epub, noab_pdf (incomplete)
│       └── obsidian/      # Renderer + writer
├── tests/                 # Pytest regression suite + fixtures
├── docs/                  # Architecture and per-source structure docs
├── .claude/skills/        # Project-local Claude Code skills
│   ├── audit-source/      # /audit-source — raw source inspection + structure doc
│   └── build-source/      # /build-source — TDD adapter build + sync
├── scripts/               # CLI entry points
│   ├── extract_osb.py     # Orthodox Study Bible (hub files + OSB Notes)
│   ├── extract_lexham.py  # Lexham LXX (OT text + Lexham Notes companions)
│   ├── extract_eob.py     # EOB NT (NT text + EOB Notes companions)
│   ├── extract_net.py     # NET Bible 2.1 (NET Notes companions)
│   ├── extract_greek_nt_goarch.py  # GOArch Greek NT (polytonic Antoniades 1904)
│   ├── extract_greek_lxx.py        # Rahlfs LXX (OT Greek companions)
│   ├── extract_apostolic_fathers.py
│   ├── extract_lectionary.py
│   ├── validate_output.py # Validator for generated Markdown
│   ├── inspect_epub.py    # EPUB internals inspector (debugging)
│   └── fix_*.py           # One-off migration/repair utilities
└── assets/                # Vault CSS and static resources
```

## Quick Start

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r requirements-dev.txt   # pytest, black, ruff
.venv/bin/pip install -e .                      # install vault_builder as editable package

# Sample extraction (representative chapters only → output/Scripture/)
.venv/bin/python3 scripts/extract_osb.py
.venv/bin/python3 scripts/extract_lexham.py
.venv/bin/python3 scripts/extract_eob.py
.venv/bin/python3 scripts/extract_net.py
.venv/bin/python3 scripts/extract_greek_nt_goarch.py   # live scrape — rate limited
.venv/bin/python3 scripts/extract_greek_lxx.py
.venv/bin/python3 scripts/extract_apostolic_fathers.py

# Validate generated output
.venv/bin/python3 scripts/validate_output.py output/Scripture/

# Full extraction (entire Bible)
.venv/bin/python3 scripts/extract_osb.py --full     # → output/Scripture-full/
.venv/bin/python3 scripts/validate_output.py output/Scripture-full/ --full-osb
```

## Running Tests

```bash
# Unit tests only (fast, ~0.1s)
.venv/bin/pytest tests/ -m "not integration"

# Full suite including PDF integration tests (~9 min, requires source files)
.venv/bin/pytest tests/ -v
```

## Sync to Obsidian Vault

```bash
rsync -av output/Scripture/ \
  "~/Library/CloudStorage/GoogleDrive-jmtharp90@gmail.com/My Drive/Jasper/Holy Tradition/Holy Scripture/"
```

## Source Coverage

| Source | Format | Output | Adapter | Status |
|---|---|---|---|---|
| Orthodox Study Bible (OSB) | EPUB | Hub files + OSB Notes companions | `osb_epub.py` | approved |
| Lexham English Septuagint | EPUB | OT text + Lexham Notes companions | `lexham_epub.py` | approved |
| Eastern Orthodox Bible NT (EOB) | EPUB | NT text + EOB Notes companions | `eob_epub.py` | approved |
| NET Bible 2.1 | EPUB | Full Bible NET Notes companions | `net_epub.py` | approved |
| Greek NT — GOArch Antoniades 1904 | Web | NT Greek text companions | `goarch_greek_nt.py` | approved |
| Greek OT — Rahlfs LXX 1935 | CSV | OT Greek text companions | `greek_lxx_csv.py` | approved |
| Apostolic Fathers (Holmes 3rd ed.) | EPUB | `100-References/Apostolic Fathers/` | `apostolic_fathers_epub.py` | approved |
| Manley (Bible and the Holy Fathers for Orthodox) | Web/PDF | Source-backed Fathers companions in `output/Scripture/` | `manley_archive.py` | extracted |
| OCMC Lectionary | CSV | Pericope links in hub files | `extract_lectionary.py` | extracted |
| NOAB RSV | PDF | (gated — quality issues) | `noab_pdf.py` | incomplete |
| KJV with Apocrypha | EPUB | — | — | new |
| New Jerusalem Bible | PDF | — | — | new |
| David Bentley Hart NT | EPUB | — | — | new |
| Robert Alter OT | EPUB | — | — | new |
| EOB Old Testament | PDF | — | — | new |
| Psalms of David | EPUB | — | — | new |
| HTM Psalter (liturgical) | PDF | — | — | new |
| Philokalia (Palmer/Sherrard/Ware) | PDF | — | — | new |

## Documentation

| Doc | Contents |
|---|---|
| `Orthodox-Vault-Goals.md` | North-star goals, principles, major decisions |
| `CLAUDE.md` | Behavioral spec for Claude Code in this repo |
| `sources.yaml` | Central source registry (all EPUB/PDF/CSV sources) |
| `docs/implementation-architecture.md` | Adapter/model/renderer design; canonical nav order |
| `docs/source-roadmap.md` | Source status, phase roadmap, acquisition plan |
| `docs/validation-plan.md` | Validator rules, fixture strategy, execution policy |
| `docs/osb-epub-source-structure.md` | OSB EPUB tag/class inventory |
| `docs/lexham-epub-source-structure.md` | Lexham EPUB anchor patterns, span taxonomy |
| `docs/eob-epub-source-structure.md` | EOB NT EPUB chapter/verse markers, note handling |
| `docs/net-epub-source-structure.md` | NET Bible 2.1 EPUB structure, note type taxonomy |
| `docs/goarch-greek-nt-source-structure.md` | GOArch web scrape patterns, polytonic Unicode |
| `docs/noab-pdf-source-structure.md` | NOAB PDF layout, known quality issues, GlyphLessFont |
| `docs/apostolic-fathers-source-structure.md` | Apostolic Fathers EPUB structure, verse anchor scheme |
| `docs/manley-source-structure.md` | Manley OCR/text structure, Fathers companion extraction plan |
| `docs/greek-nt-source-structure.md` | Survey of available Greek NT sources (reference) |

## Claude Code Skills

Project-local skills invocable as slash commands in this directory:

| Skill | Invoke | Purpose |
|---|---|---|
| audit-source | `/audit-source [source]` | Raw-inspect a source, produce/update its structure doc |
| build-source | `/build-source [source]` | TDD loop to build an adapter, LLM-examine, sync to Drive |
| verify-source | `/verify-source [source] [--sync]` | Run tests + extraction + LLM check on an existing adapter |
