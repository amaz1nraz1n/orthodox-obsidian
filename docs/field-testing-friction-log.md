# Field Testing Friction Log

Use this file while reading and navigating the generated vault in normal use.
The goal is to capture friction before it gets translated into implementation work.

This is not a backlog. It is a review scratchpad that helps separate:

- real usage friction
- source-quality limitations
- renderer/navigation problems
- polish ideas that can wait

## Current Review Focus

These are the most useful things to watch for during the next few days of use:

1. Hub-to-notes navigation
2. Companion discoverability from the hub
3. Dead, misleading, or missing nav links
4. Note ordering and readability inside companion files
5. Callout readability and visual distinction
6. Cases where the generated output is technically correct but awkward to use
7. Cases where source quality is still too poor for practical reading

## How To Log Issues

Keep entries short and concrete.
Prefer "what I tried / what happened / why it felt wrong" over immediate solutioning.

If you have a likely category, tag it loosely as one of:

- `navigation`
- `presentation`
- `content-quality`
- `source-limitation`
- `validation`
- `polish`

If a finding clearly belongs to an existing bead, note it.
If it does not, leave that blank until a pattern emerges.

## Entry Template

```md
### YYYY-MM-DD — Short title

- Area: `navigation|presentation|content-quality|source-limitation|validation|polish`
- File(s): `Book Chapter`, companion file name, or folder
- Context: what I was trying to do
- Observed: what happened
- Expected: what would have felt correct or easier
- Impact: low | medium | high
- Likely bucket: renderer | nav contract | source extraction | validator | CSS | unclear
- Related bead: `orthodox-obsidian-###` or blank
- Notes: anything worth preserving before forgetting it
```

## Seeded Findings To Watch

These are known review themes, included here so repeated observations can be grouped:

### Navigation

- Hub should feel like the reliable launch point into all useful companion layers.
- Gated or absent layers should not create confusing expectations.
- Notes companions should make it easy to get back to the hub and into the relevant apparatus.

### Presentation

- New taxonomy callouts still need dedicated CSS and may not be visually distinct enough in live use.
- Companion files should read sequentially and locally, not like exports.

### Source Quality

- NOAB remains gated; if it still feels noisy, merged, or unreliable in actual reading, log that as evidence rather than trying to explain it away.

## Log Entries

### 2026-03-25 — Initial review setup

- Area: `navigation`
- File(s): `generated vault overall`
- Context: established a field-testing log before the next few days of real use
- Observed: there was no dedicated place to collect day-to-day friction in one running document
- Expected: one lightweight review file for live observations before they become beads or code work
- Impact: medium
- Likely bucket: review workflow
- Related bead: `orthodox-obsidian-119`
- Notes: use this file to collect repeated friction before deciding what deserves a bead

### 2026-03-25 — Hub file to notes navigation

- Area: `polish`
- File(s): `generated vault overall`
- Context: trying to quickly and easily get from a specific verse in a reading to corresponding notes
- Observed: when reading a scripture reading that's somewhere in the middle or a high number verse, navigating to corresponding notes required finding the relevant file, then scrolling way down to find the verse number notes.
- Expected: a quick link at the end of a verse or within a verse after a certain word
- Impact: medium
- Likely bucket: review workflow
- Related bead: `orthodox-obsidian-119`
- Notes: use this file to collect repeated friction before deciding what deserves a bead