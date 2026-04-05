# Orthodox Vault Implementation Architecture

This document captures the implementation-oriented architecture decisions for the vault builder.

`Orthodox-Vault-Goals.md` remains the north-star document focused on purpose, principles, and major decisions.
This file records the detailed "how" for extractor, model, and renderer design.

## Core Decision

The project should use:

- source-specific extractors/adapters
- one shared normalized domain model
- shared rendering primitives with a small number of rendering profiles

It should **not** use:

- one giant extractor that tries to parse every source type with one code path
- fully separate end-to-end renderer and output schema per source

## Why This Hybrid Model

The inputs are structurally different:

- OSB is structured EPUB with multiple note families and linked auxiliary files
- Lexham is structured EPUB with chapter anchors and linked footnotes
- EOB is PDF text extraction with page-layout cleanup concerns
- NET is PDF apparatus-first, not primarily a reading-text source
- Greek sources are expected to be repository/database exports rather than page-layout documents
- Fathers and Philokalia often behave more like distributed note corpora than chapter-by-chapter Bible layers

Because of this:

- extraction must be source-aware
- output contracts should still stay normalized and shared

## Architecture Shape (Implemented)

The project uses **Ports & Adapters (Hexagonal Architecture)** with a DDD domain core. All layers are now implemented and tested.

### Domain Layer (`vault_builder/domain/`)

**Value objects (frozen dataclasses)** — immutable after construction:
- `Verse(number, text)`
- `VerseRef(book, chapter, verse)` — canonical citation reference
- `StudyNote(verse_number, ref_str, content, verse_end?, anchor_id?)`
- `StudyArticle(title, content)`
- `BookIntro(book, source, content)`, `ChapterIntro`, `PartIntro`

**Aggregates (mutable dataclasses)** — mutation via methods only:
- `Chapter(book, number, verses, pericopes, after_markers)`
  - `add_verse(number, text)` → raises `DuplicateVerseError` on collision
  - `sorted_verses()` → ordered list
- `Book(name)`
  - `chapters` → read-only `MappingProxyType` (direct write raises `TypeError`)
  - `add_chapter(chapter)` → raises `DuplicateChapterError` on collision
  - `max_chapter()` → int
- `ChapterNotes(book, chapter, source, ...)`
  - `add_note(NoteType, StudyNote)` → routes to correct list
  - `add_article(StudyArticle)`
  - `sorted_notes(NoteType)` → verse-ordered list

**`NoteType` enum** — all note routing uses typed enum, never bare strings:
`FOOTNOTE`, `VARIANT`, `CROSS_REF`, `LITURGICAL`, `CITATION`, `TRANSLATOR`, `ALTERNATIVE`, `BACKGROUND`, `PARALLEL`

**Domain exceptions** (`vault_builder/domain/exceptions.py`):
`VaultDomainError` (base), `DuplicateVerseError`, `DuplicateChapterError`, `UnknownBookError`, `MissingSourceError`

### Ports Layer (`vault_builder/ports/`)

Abstract base classes that adapters must implement:

- `ScriptureSource`: `read_text() → Iterator[Book]`, `read_notes() → Iterator[ChapterNotes]`, `read_intros() → Iterator[BookIntro]`
- `VaultRenderer`: `render_hub()`, `render_text_companion()`, `render_notes()`, `render_book_intro()`
- `VaultWriter`: `write_hub()`, `write_text_companion()`, `write_notes()`, `write_book_intro()` — all return `Path`

### Source Adapters (`vault_builder/adapters/sources/`)

Implemented adapters:

| Short name | Class | Mode |
|-----------|-------|------|
| `osb` | `OsbEpubSource` | HUB |
| `lexham` | `LexhamEpubSource` | COMPANION |
| `eob` | `EobEpubSource` | COMPANION |
| `greek_lxx` | `GreekLxxCsvSource` | COMPANION |
| `greek_nt` | `GoArchGreekNtSource` | COMPANION (custom interface) |
| `net` | net_epub/net_pdf | COMPANION (custom pipeline) |
| `apostolic_fathers` | `ApostolicFathersEpubSource` | COMPANION (custom renderer) |

### Service Layer (`vault_builder/service_layer/extraction.py`)

`ExtractionService` orchestrates the full pipeline:

```
source.read_intros()  → renderer.render_book_intro() → writer.write_book_intro()
source.read_text()    → renderer.render_hub() (HUB mode)
                        renderer.render_text_companion() (COMPANION mode)
                        → writer.write_hub() / write_text_companion()
source.read_notes()   → renderer.render_notes() → writer.write_notes()
```

Returns `ExtractionResult` with counts and `summary()` string.

`ExtractionMode.HUB` — used by OSB; produces hub files.
`ExtractionMode.COMPANION` — used by Lexham, EOB, Greek LXX; produces text companion files.

### Composition Root (`vault_builder/bootstrap.py`)

`bootstrap(source_name, *, output_dir, full_run, source=None, renderer=None, writer=None) → ExtractionService`

- Wires all dependencies from a single source short-name
- Per-source `SAMPLE_CHAPTERS` config lives in `_SOURCE_CONFIG`
- `source=`, `renderer=`, `writer=` overrides enable test injection without real EPUB/PDF

### Output Adapters (`vault_builder/adapters/obsidian/`)

- `ObsidianRenderer(VaultRenderer)` — pure functional Markdown renderer
- `ObsidianWriter(VaultWriter)` — writes files to disk following vault folder conventions

### Test Fakes (`tests/fakes.py`)

- `FakeScriptureSource(ScriptureSource)` — in-memory source from plain Python lists
- `FakeVaultWriter(VaultWriter)` — captures write calls in dicts; never touches disk

### Source Provenance vs Normalized Meaning

All adapters map source-specific note markers to `NoteType`:

- OSB: `crossReference.html` → `CROSS_REF`; `studyNote` → `FOOTNOTE`; patristic citations → `CITATION` notes that can link out to source-backed Fathers companions when present
- Manley: OCR catena excerpts → source-backed `ChapterFathers` companions keyed to Scripture chapter
- NET: `tn` → `TRANSLATOR`; `tc` → `VARIANT`; `sn` → `FOOTNOTE`; `map` → `BACKGROUND`
- Lexham: translator notes → `TRANSLATOR`; variants → `VARIANT`
- EOB: variants → `VARIANT`; alternatives → `ALTERNATIVE`; citations → `CITATION`

## Rendering Model

`ObsidianRenderer` implements two rendering paths:

### Hub Renderer (`render_hub`)

- Canonical frontmatter (`testament`, `genre`, `book_id`, `aliases`, `up`, `prev`, `next`)
- Mode navigation callout with all companions linked
- H6 verse anchors with inline verse numbers (`.vn` span) + hidden `^vN` block IDs
- One real verse per anchor — no grouped-verse corruption

### Chapter Text Companion Renderer (`render_text_companion`)

Used for EOB NT, Lexham OT, Greek LXX, Greek NT. Scoped nav (hub + own notes + NET Notes + Fathers when present).

### Notes Companion Renderer (`render_notes`)

Used for OSB Notes, NET Notes, Lexham Notes, EOB Notes, and Fathers. Verse/pericope-ordered headings with typed callout blocks.

### Book Intro Renderer (`render_book_intro`)

Used by OSB. Linked from Chapter 1 `intro:` frontmatter field.

## Layer Participation Rules

### Chapter-Bound By Default

- Hub canonical text
- OSB notes
- Lexham OT
- EOB NT
- NET notes-first
- Greek NT
- Greek OT

### Chapter-Bound Only When Curated

- Fathers
- EOB OT comparison layer

### Distributed By Default

- Personal notes
- Philokalia
- many Patristic works
- class notes
- homily notes
- daily notes

## Current Layer Profiles

| Layer | Profile | Default Artifact |
|------|---------|------------------|
| Hub canonical text | `chapter_companion_required_text` | `John 1.md` |
| OSB study notes | `chapter_companion_required_notes` | `John 1 — OSB Notes.md` |
| EOB NT | `chapter_companion_required_text` | `John 1 — EOB.md` |
| EOB OT | `chapter_companion_optional_text` | `Genesis 1 — EOB.md` |
| Lexham LXX | `chapter_companion_required_text` | `Genesis 1 — Lexham.md` or `Genesis 1 — LES.md` |
| NET | `chapter_companion_required_notes` | `John 1 — NET.md` or `John 1 — NET Notes.md` |
| Greek NT | `chapter_companion_required_text` | `John 1 — Greek.md` |
| Greek OT | `chapter_companion_required_text` | `Genesis 1 — LXX Greek.md` |
| Fathers | `chapter_companion_optional_curated` | `John 1 — Fathers.md` |
| Personal | `distributed_only` | existing vault notes |
| Philokalia | `distributed_only_manual` | manual excerpts / existing notes |

## Phase 1 Notes Policy For New Source Layers

Not every source note system needs first-class rendering in the same phase as text extraction.

- `Lexham OT`: chapter companion remains text-first in Phase 1. The extractor should parse or skip linked footnotes deliberately, but the rendered reading file should not leak inline note sigla or orphan links. A later `Lexham Notes` artifact remains optional.
- `EOB NT`: chapter companion remains text-first in Phase 1. Numeric footnote markers and supplementary essays should be stripped from the reading file unless a later dedicated EOB note layer is intentionally added.
- `NET`: chapter companion is notes-first by design. Here the apparatus is the product, so note typing and verse-context rendering are part of the primary contract.

Shared rule:

- text-first companions should privilege readability and stable verse anchors
- note apparatus that is deferred should be deferred cleanly, not half-rendered
- validator expectations must reflect the chosen strategy per source

## Shared Navigation Contract

Most generated files should share the same top-of-file mode navigation shape so the vault feels like one system rather than a set of isolated exports.

### Canonical Nav Order — DECIDED (2026-04-04)

| Slot | NT | OT | Purpose |
|------|----|----|---------|
| 1 | OSB | OSB | Orthodox primary (hub) |
| 2 | EOB | Lexham | Primary comparison text |
| 3 | Greek NT | Greek LXX | Original language |
| 4 | NET Notes | NET Notes | Technical apparatus (universal) |
| 5 | + | + | Per-chapter Translations hub (all text modes) |
| 6 | EOB Notes | Lexham Notes | Source-specific notes |
| 7 | Study Notes | Study Notes | OSB study notes |
| 8 | Fathers | Fathers | Patristic companion (curated chapters only) |

**Slot 5 (`+`)** links to `{Book} {Chapter} — Translations.md`, a generated per-chapter index of every available text translation for that chapter: OSB, EOB/Lexham, Greek NT/LXX, DBH, RSV, NETS, and any future text companions. Only emitted when at least one source has content for the chapter (in practice, always). This replaces inline nav slots for supplemental translations (DBH, RSV, NETS) — those are discoverable via `+`, not listed individually in the main nav.

**NET text companion** is not included in the nav. It exists on disk but is accessed via an inline link within NET Notes files only. This reflects NET's notes-first purpose — the text is a support artifact for the apparatus, not a reading mode.

### Translations Hub — DECIDED (2026-04-04)

File name: `{Book} {Chapter} — Translations.md`
Nav label: `+` (rendered as `[[John 1 — Translations|+]]`)

Contains a structured list of every text-mode companion available for the chapter, including:
- OSB (hub)
- EOB (NT) / Lexham (OT)
- Greek NT / Greek LXX
- DBH NT (NT chapters only, when extracted)
- RSV (when extracted)
- NETS (OT chapters only, when extracted)
- Any future text companions

This file is the comprehensive discovery surface for translations. It does not include notes companions or Fathers — those are accessed from the main nav.

### Hub vs. Companion Nav Scoping — DECIDED (2026-04-04)

**Hub nav is comprehensive** — links to all mode companions and all notes companions. The hub is the navigation home; discoverability is the priority.

**Companion navs are scoped** — each companion links only to:
1. The hub (back link)
2. Its own notes companion (if applicable)
3. NET Notes (universal apparatus — always present)
4. Fathers (when a Fathers companion exists for the chapter)

This keeps companion navs to 2–4 items. Notes companions link back to the hub and include NET Notes; they do not link to each other.

### Book Intros — DECIDED (2026-03-23)

- Book intro files (e.g. `Matthew — OSB Intro.md`) are linked from the **book index file** via the standard navigation.
- Chapter 1 hub files also include an `intro:` frontmatter field pointing to the intro file when one exists for that source (e.g. `intro: "[[Matthew — OSB Intro]]"`). This field is **only on chapter 1** — not repeated on every chapter hub.
- All other chapter hubs omit the `intro:` field.

### General Principles

- keep label order stable and consistent with the canonical order above
- allow source-specific omissions when a layer does not exist for that chapter or source
- keep OT-only additions (Lexham, LXX) conditional rather than universal
- samples must be regenerated whenever the renderer nav logic changes; stale companion navs are a known failure mode

This should be validated as a shared output contract, not as a source-specific implementation detail.

## Validation Expectations

Validation should test shared output contracts, not source internals only.

Shared validation concerns:

- hub frontmatter and path policy
- verse-anchor continuity and order
- companion/hub link integrity
- verse-order rendering for note layers
- malformed range detection
- source-to-output structural correctness

Source-specific extraction can vary internally as long as it emits valid normalized output.

## Planning Rule

When adding a new source:

1. decide whether it is chapter-bound or distributed
2. define its adapter
3. map its source-specific structures into the shared normalized model
4. choose an existing rendering profile if possible
5. add a new rendering profile only if the source genuinely needs one
