---
name: verify-source
description: Verify an existing Scripture source adapter by running its extract script, running its tests, and examining the output. No building — adapter must already exist. Use after /build-source or to re-verify an approved source after changes. Optionally syncs passing output to Google Drive.
argument-hint: [source-name] [--sync]
---

Runs the full verification loop for an existing source adapter: tests → sample extraction → output examination → optional Google Drive sync. Never writes adapter code or tests. If no adapter exists yet, stop and direct to `/build-source`.

Pass `--sync` to sync output to Google Drive if all checks pass.

## Step 1 — Lookup

Read `sources.yaml` from the project root. Resolve the source by short name.

If not found: list registered sources and exit.

Extract: `extract_script`, `adapter`, `status`, `structure_doc`, `testament`.

**Gate checks:**
- If `extract_script` is null: "No extract script for `{name}`. Run `/build-source {name}` to build one." Exit.
- If `adapter` is null: "No adapter for `{name}`. Run `/build-source {name}` to build one." Exit.

If `status` is `new`: warn that verification may be premature, but continue.

## Step 2 — Beads

Check for an open bead titled `"verify-source: {name}"`.

- **Found**: resume from where it left off (check notes for last completed step).
- **Not found**: `bd create --title "verify-source: {name}" --type=task`, claim it.

## Step 3 — Run Tests

Find all test files for this source:

```bash
ls tests/test_{source_short_name}*.py tests/test_*{source_short_name}*.py 2>/dev/null
```

If test files exist, run them:

```bash
.venv/bin/python3 -m pytest tests/test_{source}*.py -v --tb=short
```

Report: how many passed, how many failed, any tracebacks for failures.

If tests fail:
- Summarize what failed and why.
- Do NOT attempt to fix code. State: "Tests are failing — use `/build-source {name}` to enter the TDD repair loop."
- Update bead notes with failure summary.
- Exit.

If no test files found: note this as a gap (missing test coverage) and continue.

## Step 4 — Run Sample Extraction

Run the extract script in sample mode:

```bash
.venv/bin/python3 scripts/{extract_script}
```

If the script accepts a `--sample` flag (check by reading the first 30 lines of the script for argparse definitions), use it. Otherwise run without flags and note this.

Watch for:
- Non-zero exit code → report the error output and exit.
- Missing output files → report and exit.
- Warning/error log lines → capture and include in the report.

Confirm output files were created under `output/Scripture/` (or `output/` for non-Scripture sources like Apostolic Fathers or Lectionary).

## Step 5 — Output Content Examination

Read hub and companion output files for the canonical check verses. This step has two parts: **hub verse text** and **companion note alignment**.

### Part A — Hub Verse Text

Which hub files to check depends on the source's testament:

**NT sources** (testament: nt or both):
| File | Verse | Check |
|---|---|---|
| John 1 | v1 | ≈ "In the beginning was the Word…" (or Greek equivalent) |
| Matthew 1 | v1 | exists, genealogy structure intact |
| Revelation 1 | v1 | exists, no OCR artifacts |

**OT sources** (testament: ot or both):
| File | Verse | Check |
|---|---|---|
| Genesis 1 | v1 | ≈ "In the beginning God created…" (or LXX "made") |
| Psalms 50 (LXX) | v1 | exists; content is "Have mercy on me, O God…" (note: in OSB/LXX the superscription occupies v1–v2; the "Have mercy" text appears at v3) |
| Isaiah 7 | v14 | ≈ "…a virgin shall conceive…" |

**Non-Scripture sources** (Apostolic Fathers, Lectionary):
- Check the first document/entry in the output for structural correctness.
- Confirm frontmatter fields match the expected schema.

**For all hub files, also check:**
- Required frontmatter keys present (`testament`, `book_id`, `aliases`, `up`, `prev`, `next`)
- Chapter 1 hubs include `intro:` frontmatter when a book intro file exists
- Verse anchors use the `#vN` format (or `^{ch}-{verse}` for Apostolic Fathers)
- No raw HTML tags leaking into Markdown output
- No OCR artifacts (stray characters, merged words, digit substitution)
- No merged verses (two verse numbers in one block)
- No encoding issues (`\ufffd` replacement chars, garbled Unicode)

### Part B — Companion Note Alignment

For each canonical check verse above, locate the corresponding Notes companion file (`{Book} {Ch} — {Source} Notes.md`) and check:

1. **File exists** — if the source generates Notes companions, the file should be present.
2. **Verse heading present** — a heading of the form `### [[{Book} {Ch}#vN|{ref}]]` exists for the check verse (or nearby verse, since not every verse has a note).
3. **Note body non-empty** — at least one line of substantive text or a callout block follows the heading.
4. **Heading links back correctly** — the wikilink in the heading resolves to the hub (`[[John 1#v1|1:1]]`, not `[[John 1v1|...]]` or a malformed anchor).
5. **Callout labels correct** — note-type callouts match the source's expected schema:
   - OSB Notes: `[!info]` variants, `[!quote]` cross-refs, `[!liturgy]` liturgical, `[!cite]` patristic citations, `[!tn]` translator notes, `[!alt]` alternatives, `[!bg]` background notes, `[!parallel]` parallel passages
   - NET Notes: `[!tn]` translator notes, `[!tc]` text-critical, `[!sn]` study notes, `[!map]` map references
   - Lexham Notes: `[!tn]` translator notes
   - Other sources: check against the `_CALLOUT` and `_NET_CALLOUT` dicts in `renderer.py`
6. **Variant callouts present** (if source has textual variants): confirm at least one `[!info]` or `[!tc]` callout exists somewhere in the companion — confirms variant parsing is working.
7. **No orphan headings** — no verse heading in the companion references a verse number absent from the hub.
8. **Companion frontmatter** — required keys present (`hub`, `source`).
9. **Companion file names** match `{Book} {Ch} — {Source} Notes.md` pattern.

Not every canonical check verse will have a note entry — that is normal and not a failure. Flag it only if the companion file is entirely empty or structurally broken.

**Known gaps from structure doc:** Read `docs/{source}-source-structure.md` (if it exists) and note any documented known gaps. Check whether those gaps are still present in the current output — they may have been fixed since the doc was written.

## Step 6 — Quality Report

Produce a structured report:

```
## Verify-source: {name} — {date}

### Tests
- {N} passed / {N} failed
- [list any failures]

### Extraction
- Output root: output/Scripture/ (or other)
- Files generated: {N} hub files, {N} companion files (if applicable)
- Warnings during extraction: [list]

### Output Content Examination

#### Hub Verse Text
| Verse | Expected | Found | Status |
|---|---|---|---|
| John 1:1 | "In the beginning…" | "…" | ✅ / ⚠️ / ❌ |
| ... | | | |

#### Companion Note Alignment
| Companion File | Check | Result | Status |
|---|---|---|---|
| John 1 — OSB Notes | v1 heading present, body non-empty | "In the beginning **recalls…**" | ✅ |
| John 1 — OSB Notes | variant callout present | [!info] at 1:1-17 | ✅ |
| ... | | | |

### Known Gaps (from structure doc)
- [gap 1]: still present / resolved
- [gap 2]: still present / resolved

### New Issues Found
- [any issues not already documented]

### Overall: PASS / WARN / FAIL
```

**PASS**: all tests green, all check verses correct, companions structurally sound, no new issues.
**WARN**: tests green, check verses correct, but known gaps still present or minor new issues.
**FAIL**: any test failure, any missing output, any critical verse corruption, or companion files entirely absent/broken.

## Step 7 — Sync (optional)

Only if `--sync` was passed AND the overall result is PASS or WARN:

```bash
rsync -av output/Scripture/ "~/Library/CloudStorage/GoogleDrive-jmtharp90@gmail.com/My Drive/Jasper/Holy Tradition/Holy Scripture/"
```

For non-Scripture output roots (Apostolic Fathers), adjust the rsync target accordingly — check the extract script for the output path.

If result is FAIL: do not sync. State why.

## Step 8 — Close Out

Update bead notes with the quality report summary and close:

```bash
bd close verify-source-bead-id --reason="PASS/WARN/FAIL: [one-line summary]"
```

If new issues were found that aren't in the structure doc:
- Add them to `docs/{source}-source-structure.md` under "Known Gaps" if the doc exists.
- If no structure doc exists, suggest running `/audit-source {name}` to create one.

If the result is PASS and status in `sources.yaml` is not `approved`, suggest updating it.

## Behavior

- Never write or edit adapter code or test files. Verification only.
- If tests fail, report and stop — do not attempt any repair.
- Read the first 30 lines of the extract script to check for `--sample` / `--full` flags before running.
- Known gaps from the structure doc are expected — note them, don't treat them as failures unless they've gotten worse.
- New issues not in the structure doc are always surfaced, even if minor.
- Missing note entries for individual check verses is normal — only flag if the entire companion file is absent or empty.
- `--sync` flag is opt-in. Never sync on FAIL, even if the user passed `--sync`.
