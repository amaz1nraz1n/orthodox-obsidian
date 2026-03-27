# Orthodox Vault Validation Plan

This document captures the detailed validation and fixture strategy for generated Markdown output.

`Orthodox-Vault-Goals.md` keeps the high-level release policy.
This file contains the detailed implementation-oriented validator plan.

## Severity Model

- `ERROR`: structural failure; blocks signoff
- `WARN`: suspicious output requiring review
- `INFO`: summary/statistical output

## Validation Scope

The validator should check generated Markdown, not just extractor internals.

It should validate:

- chapter hubs
- companion files
- run-level coverage and summary behavior

For chapter hubs, validation should eventually cover not just anchor existence but also the approved reading contract:

- one real verse per anchor
- no accidental multi-verse grouping under a single heading
- no visible-number/body corruption such as the heading number diverging from the verse text number
- no long-term acceptance of the detached heading-line regression once the renderer contract is restored to inline verse presentation
- when secondary `^vN` block IDs are emitted, they should exist exactly once per verse and stay numerically aligned with the corresponding verse anchor

## Rule Families

### Hub Rules

- `HUB001 Required frontmatter fields`
- `HUB002 Frontmatter field shape`
- `HUB003 Reference-metadata policy`
- `HUB004 Folder placement`
- `HUB005 Canonical order path`
- `HUB006 Verse anchor format`
- `HUB007 Verse anchor continuity`
- `HUB008 Verse body presence`
- `HUB009 Navigation sanity`
- `HUB010 Testament/category consistency`
- `HUB011 Hub verse presentation and segmentation`
- `HUB012 Secondary block-id consistency`

### Companion Rules

- `CMP001 Required companion frontmatter`
- `CMP002 Companion/hub pairing`
- `CMP003 Anchor target integrity`
- `CMP004 Malformed range display detection`
- `CMP005 Cross-chapter source references`
- `CMP006 Duplicate section detection`
- `CMP007 Broken inline wikilinks`
- `CMP008 Verse-ordered rendering`

### Run Rules

- `RUN001 Sample coverage`
- `RUN002 Zero structural errors`
- `RUN003 Summary statistics`
- `RUN004 Full-run completeness`

## Output Format

### Terminal Summary

- one-line verdict
- severity counts
- grouped top failures
- first N detailed records

### Record Shape

Each record should include:

- `severity`
- `code`
- `path`
- `line`
- `message`
- `expected`
- `actual`
- `suggestion`

### Machine Report

Always write `validation-report.json` or equivalent.

Exit behavior:

- exit `0` only when there are no `ERROR` records
- non-zero exit when any `ERROR` exists

## General Fixture Floor

Minimum genre-based fixture coverage:

- Torah prose: `Genesis 1`, `Exodus 20`
- Psalter / versification: `Psalms 1`, `Psalms 50`
- Wisdom / poetry: `Job 3`, `Proverbs 8`, `Song of Solomon 1`
- Prophecy: `Isaiah 53`, `Jeremiah 1`, `Ezekiel 1`
- Gospel: `John 1`, `Matthew 5`
- Epistle: `Romans 8`, `I Corinthians 13`
- Apocalypse: `Revelation 1`
- Deuterocanon: `Sirach 1`, `I Maccabees 1`

## TDD Fixture Strategy

Use the current generated vault as the starting baseline, then turn known regressions into explicit fixtures before broadening coverage.

Primary fixture philosophy:

- prefer a small number of high-signal fixtures over a large generic suite
- encode known regressions as failing examples before changing code
- keep source-specific expectations close to the relevant source fixture block
- validate the current output shape, not just extractor internals

High-priority fixture targets:

- OSB hub reading layout and hidden block-id stability
- OSB notes verse ordering and category flattening
- NET sample-mode bleed and cross-chapter note handling
- Lexham and EOB text-companion visibility and hub pairing
- shared mode navigation across hub, text companions, and notes companions

Recommended TDD loop:

1. add or update a fixture for the observed failure
2. make the validator fail for that fixture
3. fix the adapter/renderer
4. keep the fixture as a regression guard

## Phase 1 Source Fixture Matrix

### OSB Hub Text

Required fixtures:

- `Genesis 1`
- `Psalms 50`
- `Sirach 1`
- `John 1`
- `Romans 8`

Pass criteria:

- zero structural validator errors
- correct OT/NT and Deuterocanon placement
- correct verse-anchor order and hub frontmatter

### OSB Notes

Required fixtures:

- `Genesis 1 — OSB Notes`
- `John 1 — OSB Notes`
- `Romans 8 — OSB Notes`
- `Sirach 1 — OSB Notes`

Pass criteria:

- verse/pericope-ordered note flow
- no category-first layout
- `source_bucket` and `semantic_kind` both recoverable
- no malformed cross-chapter display ranges

### Lexham OT Mode 2

Required fixtures:

- `Genesis 1`
- `Psalms 50`
- `Isaiah 7`
- `Sirach 1`

Pass criteria:

- verse order preserved
- footnote-handling strategy explicit
- no leaked Lexham note sigla or orphan note links in the readable chapter output
- OT/Deuterocanon path policy preserved

### EOB NT Mode 2

Required fixtures:

- `Matthew 1`
- `John 1`
- `Romans 8`
- `James 1`

Pass criteria:

- no page-header/footer bleed
- stable chapter starts
- chapter companion output remains readable
- numeric footnote markers do not pollute the chapter text unless intentionally rendered
- no introduction, appendix, or special essay bleed into ordinary chapter fixtures

### NET Notes-First Layer

Required fixtures:

- `John 1`
- `Romans 8`
- `Psalm 1`
- `Acts 15`

Pass criteria:

- `tn`, `tc`, `sn`, `map` note types normalize cleanly
- local verse context is sufficient for readability
- no requirement for a second plain-text NET chapter file

## Validator Expansion For New Source Layers

As Lexham, EOB, and NET are added, validator coverage should expand beyond the current OSB-focused checks.

Source-specific additions should include:

- Lexham text companions: detect leaked inline note sigla, broken back-of-book note links, or accidental note-page dumps into the chapter file
- EOB text companions: detect page-header/footer bleed, numeric marker litter, and appendix/introduction contamination
- NET notes-first companions: detect missing note-type normalization, unreadable note blocks with no local verse context, and malformed companion naming/pairing

The existing validator does not need a separate executable per source, but the fixture matrix and failure messages should become source-aware as these layers are implemented.

### Lectionary Links

Required fixtures:

- `John 1:1-17`
- `Romans 8:28-39`
- `Genesis 1:1-13`
- one cross-chapter pericope

Pass criteria:

- visible first-verse links resolve
- invisible stacked links resolve when used
- cross-chapter ranges never collapse into invalid same-chapter links

## Execution Policy

- run sample extraction first
- run validator against generated sample
- allow full extraction only after sample passes
- for a full OSB gate, run validator in a completeness-aware mode against the full extraction root
- keep validator authoritative
- do not fix generated output manually instead of fixing extraction/render logic

## Test Performance Strategy

The test suite should stay fully enabled while still getting faster and more predictable.

Primary performance goals:

- profile before optimizing, so time is spent on real bottlenecks
- reuse expensive immutable setup through fixture scopes instead of recreating it per test
- parallelize safe pure-Python tests once the suite is deterministic under concurrency
- avoid repeated source parsing when a read-only parsed artifact can be shared
- keep collection bounded to `tests/` and keep heavyweight source parsing out of import time

Preferred tactics:

- use `pytest --durations=10` periodically to identify the slowest tests and fixture setup time
- centralize shared pure-Python fixtures in `conftest.py` when they are safe to reuse
- prefer module- or session-scoped fixtures for read-only renderer/source objects that are expensive to build
- add `pytest-xdist` and use `-n auto` once the suite is confirmed safe under parallel execution
- keep integration markers for reporting and profiling, but do not rely on them to reduce the default suite

The intent is to reduce wall-clock time without dropping coverage or disabling any tests locally.

## Full OSB Completeness Gate

The current validator walks whatever Markdown exists under the chosen Scripture root.
That is necessary but not sufficient for a trusted full OSB signoff.

For full-run validation, add a mode such as `--full-osb` that:

- cross-checks generated hubs against `BOOK_CHAPTER_COUNT`
- verifies every expected OSB chapter hub exists
- verifies every expected `— OSB Notes` companion exists
- reports missing books/chapters as structural failures, not just warnings

This is distinct from ordinary sample validation:

- sample validation checks structural correctness of the extracted sample set
- full-run validation checks both structural correctness and canonical completeness

Recommended behavior:

- `RUN004` should emit `ERROR` when expected OSB hubs or companions are missing in full-run mode
- the machine-readable report should include missing-book and missing-chapter counts
- the terminal summary should clearly distinguish "validated existing files" from "validated full expected canon"

## Related Documents

- `Orthodox-Vault-Goals.md`
- `docs/source-roadmap.md`
- `docs/implementation-architecture.md`
