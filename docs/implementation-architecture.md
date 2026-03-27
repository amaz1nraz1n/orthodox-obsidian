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

## Architecture Shape

### Source Adapters

Each source should have its own adapter responsible for:

- source discovery
- parsing and cleanup
- source-specific normalization
- provenance retention

Planned adapters:

- `osb_epub`
- `lexham_epub`
- `eob_nt_pdf`
- `eob_ot_pdf`
- `net_pdf`
- `patriarchal_nt`
- `rahlfs_lxx`
- future Patristic/source adapters as needed

### Shared Domain Model

All adapters should emit into a shared model that can describe:

- chapter hub text
- chapter companion layers
- verse-linked note entries
- provenance and semantic meaning

Recommended normalized concepts:

#### Canonical Chapter Document

Represents a chapter hub.

Suggested fields:

- `book`
- `book_id`
- `chapter`
- `testament`
- `genre`
- `aliases`
- `up`
- `prev`
- `next`
- optional `mt_ref`
- optional `lxx_ref`
- ordered `verses`

#### Verse Record

Represents one hub verse.

Suggested fields:

- `verse_number`
- `anchor_id`
- `text`
- optional `source_ref`

#### Companion Layer Document

Represents a chapter-bound companion file.

Suggested fields:

- `hub`
- `source`
- `layer_type`
- `book`
- `chapter`
- optional `cssclass`
- ordered `entries`

#### Verse-Linked Entry

Represents one normalized note or annotation block within a chapter-bound layer.

Suggested fields:

- `book`
- `chapter`
- `verse_start`
- `verse_end`
- optional `subref`
- `ref_display`
- `sort_key`
- `heading_link`
- `source`
- `layer_type`
- optional `source_bucket`
- optional `semantic_kind`
- `content`
- optional `author`
- optional `title`
- optional `tags`
- optional `raw_ref`

### Source Provenance vs Normalized Meaning

The model must preserve both:

- `source_bucket`
- `semantic_kind`

This is especially important for OSB and NET.

Examples:

- OSB `crossReference.html` may contain material that is semantically a textual variant
- NET `tn`, `tc`, `sn`, `map` note markers have both source and semantic value

The rule is:

- preserve raw source family/provenance
- normalize vault meaning separately

## Rendering Model

Rendering should be profile-based, not source-by-source from scratch.

### Shared Renderers

#### Hub Renderer

Responsible for:

- canonical frontmatter
- mode navigation bar
- H6 verse anchors
- canonical text only
- the approved hub reading layout: one real verse per anchor, with visible verse numbers rendered inline in a Bible-reading-friendly way without reintroducing grouped-verse corruption
- preserving the vault's primary `#vN` addressability while also emitting secondary hidden `^vN` block IDs when the output shape benefits from them

#### Chapter Text Companion Renderer

Used for readable chapter-text layers such as:

- EOB NT
- Lexham OT
- future Greek companions

Responsible for:

- layer frontmatter
- chapter text presentation
- optional light footnote/annotation handling

#### Notes-First Companion Renderer

Used for note-dominant layers such as:

- OSB Notes
- NET notes-first layer
- future curated Fathers chapter catena files

Responsible for:

- verse/pericope-ordered headings
- stacked note blocks under each relevant verse/pericope
- callout/CSS styling by semantic type

#### Distributed Layer Helpers

Used for layers that are not default chapter companions:

- Personal
- Philokalia
- many Patristic corpora

These do not need a standard chapter renderer.
They mainly need:

- consistent verse-linking conventions
- metadata expectations
- optional assembly helpers for later curated catena files

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

### Canonical Nav Order — DECIDED (2026-03-23)

| Slot | NT | OT | Purpose |
|------|----|----|---------|
| 1 | OSB | OSB | Orthodox primary (hub) |
| 2 | EOB | Lexham | Orthodox comparison text |
| 3 | RSV | RSV | Classic ecumenical text |
| 4 | Greek NT | LXX | Original language |
| 5 | NET Notes | NET Notes | Technical apparatus (universal) |
| 6 | EOB Notes | Lexham Notes | Source-specific notes |
| 7 | Study Notes | Study Notes | OSB study notes |

**NET text companion** is not included in the nav. It exists on disk but is accessed via an inline link within NET Notes files only. This reflects NET's notes-first purpose — the text is a support artifact for the apparatus, not a reading mode.

**RSV Notes** is a planned slot (parallel to EOB Notes / Lexham Notes) once RSV extraction quality is resolved.

### Hub vs. Companion Nav Scoping — DECIDED (2026-03-23)

**Hub nav is comprehensive** — links to all mode companions and all notes companions. The hub is the navigation home; discoverability is the priority.

**Companion navs are scoped** — each companion links only to:
1. The hub (back link)
2. Its own notes companion (if applicable)
3. NET Notes (universal apparatus — always present)

This keeps companion navs to 2–3 items. Notes companions link back to the hub and include NET Notes; they do not link to each other.

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
