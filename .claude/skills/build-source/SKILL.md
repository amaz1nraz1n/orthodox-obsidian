---
name: build-source
description: TDD loop to build or improve a Scripture source adapter, then LLM-examine the output and sync to Google Drive. Requires an existing source structure doc (run /audit-source first). Re-invocation resumes from post-sync verification phase via open bead state.
argument-hint: [source-name]
---

Build or improve the adapter for a registered Scripture source. Reads the source's structure doc, runs a TDD loop until tests pass, performs LLM examination, syncs output to Google Drive. Bead stays open after sync so re-invocation resumes verification rather than restarting.

## Step 1 — Lookup

Read `sources.yaml` from the project root. Resolve the source by short name.

If the name is not found:
- List registered sources and exit.

Extract: `path`, `format`, `adapter`, `extract_script`, `structure_doc`, `status`.

Check that `structure_doc` exists on disk:
- If not: "No structure doc found for `{name}`. Run `/audit-source {name}` first." Exit.

## Step 2 — Resume Detection

Check for an open bead titled `"build-source: {name}"`.

- **Bead found, notes indicate post-sync phase** (e.g., "Synced to Google Drive. Awaiting manual verification."): Skip to **Step 7 — Manual Verification Loop**.
- **Bead found, still in TDD phase**: Resume from where the loop left off.
- **No bead**: Create one (`bd create --title "build-source: {name}" --type=task`), claim it, then proceed to Step 3.

## Step 3 — Read Structure Doc

Read `docs/{source}-source-structure.md` in full.

Extract and internalize:
- Verse marker patterns (class names, id patterns, element types)
- Chapter boundary signals
- Pericope heading patterns and their elements
- Footnote marker patterns (inline) and footnote definition location
- Column layout / reading order (for PDF)
- Known limitations or quality flags
- Expected verse counts for any sample chapters mentioned
- Book boundary signals (for multi-book sources)

This document is the specification. The adapter and tests derive from it.

## Step 4 — TDD Loop

Repeat until all tests pass:

### RED — Write a failing test

Write or update `tests/test_{adapter_name}_extraction.py` and/or `tests/test_{adapter_name}_rendering.py`.

Required test coverage (add tests for any not already present):
- **Verse count**: Assert expected verse count for at least one representative chapter (e.g., John 1 = 51 verses for OSB, Genesis 1 = 31 verses).
- **Known verse text**: Assert John 1:1 text for NT sources; Genesis 1:1 for OT Torah; Psalm 50:1 for LXX Psalter; Rev 1:1 for Apocalyptic.
- **Pericope presence**: Assert at least one pericope heading is extracted for a chapter known to have one.
- **Frontmatter fields**: Assert required frontmatter keys (`testament`, `book_id`, `aliases`, `hub`, `source`) are present in output files.
- **Companion file naming**: Assert companion file name matches `{Book} {Ch} — {Source} Notes.md` pattern.
- **No verse merge**: Assert no single verse block contains two or more verse numbers (catches multi-verse merging bugs).
- **No OCR artifacts** (PDF only): Assert verse text contains no stray digit-substitution patterns (e.g., `l` for `1`, `O` for `0`).
- **Note slot routing**: For each annotation type the source contains, assert it routes to the correct `ChapterNotes` slot — e.g., `translator_notes` for translator rationale, `alternatives` for "Or:" alternatives, `background_notes` for historical/geographical notes, `parallel_passages` for structural cross-refs like "(Mt 3:1–6)". See taxonomy table in `docs/taxonomy-refactor-plan.md`.

Run the test. It **must fail** before writing any adapter code.

### GREEN — Write adapter code

Write or update `vault_builder/adapters/sources/{adapter}.py` to make the failing test pass.

Follow existing adapter patterns (read `vault_builder/adapters/sources/osb_epub.py` or the most similar existing adapter before writing).

Minimum code to pass the test. No premature abstractions.

### REFACTOR

Clean up while all tests stay green. Extract duplication, improve names, simplify logic.

### Run tests

```bash
.venv/bin/python3 -m pytest tests/test_{adapter_name}*.py -v --tb=short
```

If failures remain, fix adapter or tests and repeat the cycle.

### Run sample extraction

Once tests pass, run extraction on sample chapters:

```bash
.venv/bin/python3 {extract_script} --sample
```

(Check the extract script for the correct sample flag; if no `--sample` flag exists, run without it and note this.)

Verify output files were created under `output/Scripture/`.

## Step 5 — Output Content Examination

Read hub and companion output files for key chapters. This step has two parts.

### Part A — Hub Verse Text

Check the following per testament/genre (skip chapters the source doesn't include):

| Check | Expected content |
|---|---|
| NT prose (John 1) | John 1:1 ≈ "In the beginning was the Word…" |
| OT Torah (Genesis 1) | Gen 1:1 ≈ "In the beginning God created…" (or LXX "made") |
| OT Psalter (Psalm 50 LXX) | v3 ≈ "Have mercy on me, O God…" (v1–v2 are superscription in OSB/LXX) |
| OT Prophet (Isaiah 7) | Isa 7:14 ≈ "…a virgin shall conceive…" |
| Apocalyptic (Revelation 1) | Rev 1:1 ≈ "The Revelation of Jesus Christ…" |

For each checked hub file:
- Does the verse text read correctly?
- Are there OCR artifacts (stray characters, `1` → `l`, `0` → `O`, `rn` → `m`)?
- Are there merged verses (multiple verse numbers collapsed into one block)?
- Are there encoding issues (replacement chars `\ufffd`, garbled Unicode)?
- Are there "text smells" (footnote bleed, header bleed, lines that are clearly not Scripture text)?
- Is verse numbering continuous (no silent gaps)?

### Part B — Companion Note Alignment

For each checked hub chapter, locate the corresponding Notes companion (`{Book} {Ch} — {Source} Notes.md`) and verify:

1. **File exists** — companion was generated alongside the hub.
2. **Verse heading present** — `### [[{Book} {Ch}#vN|{ref}]]` exists for the check verse (or nearby; not every verse has a note).
3. **Note body non-empty** — substantive text or a callout block follows the heading.
4. **Heading wikilink correct** — anchor format is `#vN`, not `#v N` or `v{N}` or other malformed variant.
5. **Callout labels correct** — match the source's expected schema:
   - OSB Notes: `[!info]` variants, `[!quote]` cross-refs, `[!liturgy]` liturgical, `[!cite]` patristic citations, `[!tn]` translator notes, `[!alt]` alternatives, `[!bg]` background notes, `[!parallel]` parallel passages
   - NET Notes: `[!tn]` translator notes, `[!tc]` text-critical, `[!sn]` study notes, `[!map]` map references
   - Lexham Notes: `[!tn]` translator notes
   - Other sources: check against the `_CALLOUT` and `_NET_CALLOUT` dicts in `renderer.py`
6. **Variant callouts present** (if source has textual variants) — at least one variant-type callout appears somewhere in the companion.
7. **Companion frontmatter** — `hub` and `source` keys present.

Missing note entries for individual check verses is normal — only fail if the companion file is absent or entirely empty.

Report all findings. If critical issues are found (bad anchors, missing companions, callout label errors), return to Step 4 (TDD Loop) to fix them before syncing.

## Step 6 — Google Drive Sync

After LLM examination passes (no critical issues):

```bash
rsync -av output/Scripture/ "~/Library/CloudStorage/GoogleDrive-jmtharp90@gmail.com/My Drive/Jasper/Holy Tradition/Holy Scripture/"
```

Update bead notes: "Synced to Google Drive. Awaiting manual verification."

Leave bead **open**. Do not close it.

## Step 7 — Manual Verification Loop

When re-invoked with an open bead in post-sync state, ask:

> "Did the manual verification reveal any issues? If yes, describe them."

If **no issues**: Close the bead. Update `sources.yaml` status to `approved` if not already. Done.

If **issues described**:
1. Take the issues as input.
2. Update the structure doc if the issues reveal a documentation gap.
3. Write a failing test that reproduces the issue.
4. Fix the adapter.
5. Re-run tests.
6. Re-sync to Google Drive.
7. Update bead notes with "Re-synced after fix: [brief description]."
8. Leave bead open. Return to the top of Step 7.

## Step 8 — Completion

User confirms output is clean:
1. Close the bead with a summary of what was built, what was fixed, and any deferred items.
2. Update `sources.yaml`: `status: approved` (if not already set).
3. Note any follow-up items (e.g., RSV Notes not yet implemented, Psalms gated pending quality gate).

## Behavior

- Always read the structure doc before writing any tests or adapter code.
- TDD is strict: failing test first, then adapter code. No exceptions.
- LLM examination is non-interactive — report findings, iterate if critical, don't ask about minor style differences.
- Sync only after LLM examination passes. Never sync before.
- Bead stays open after sync — this is intentional. Re-invocation resumes from verification, not from scratch.
- If Codex MCP is available, send the adapter diff to Codex after TDD passes and before sync. Structure request as: (a) does the adapter match the structure doc spec? (b) any verse boundary edge cases missed? (c) any regressions vs existing output?
- Follow existing adapter patterns exactly. Read the most similar approved adapter before writing.
- Do not refactor code outside the adapter being built.
