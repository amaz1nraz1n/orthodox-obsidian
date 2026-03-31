# Orthodox Obsidian Vault — Goals & Preferences
*North star document for vault architecture and Claude Code specs*

---

## Driving Philosophy

> *We do not study the Bible in order to understand it. We study the Bible in order to live it.*

This is the principle that governs every architectural decision in this vault. The Orthodox Church does not approach Scripture as an academic text to be analyzed, mastered, or systematized. Scripture is the living Word of God, encountered within the life of the Church — in the Liturgy, in the Fathers, in prayer, in repentance, in the home. The vault exists to serve that encounter, not to substitute for it.

This means:
- A note that produces repentance is worth more than a note that produces knowledge
- The liturgical calendar is not a metadata layer — it is the interpretive framework within which Scripture is read
- The Fathers are not commentators — they are witnesses to the same life the Scriptures describe
- Links and graphs and modes are tools — the goal is transformation, not information
- When the vault becomes the thing being tended, something has gone wrong

Every feature, every script, every mode should be evaluated against this: *does this help me live what I am reading?*

---

## Core Purpose

A permanent, offline-first personal knowledge management system in Obsidian for Eastern Orthodox Christian study. Built by a software engineer / catechumen for lifelong use — not a catechumenate project, but a system that grows with the faith. Integrates Scripture, Patristics, liturgical cycle, and personal study notes into a single linked graph, in service of living the faith — not merely knowing it.

---

## Companion Planning Docs

This file is the north-star document. It should stay focused on:

- purpose
- guiding principles
- major structural decisions
- high-level roadmap

Detailed implementation planning now lives in:

- `docs/implementation-architecture.md` — adapter/model/renderer decisions
- `docs/source-roadmap.md` — source status, build order, acquisition plan
- `docs/validation-plan.md` — validator rules, fixture matrix, execution policy
- `docs/osb-epub-source-structure.md` — OSB EPUB audit and source-structure notes

---

## Project Scope & Licensing Bifurcation

This is **first and foremost a personal project.** The personal vault has no licensing constraints beyond fair use — PDFs of copyrighted translations owned by the user can be extracted and used freely for private study.

Any future public/open-source release requires a clean rebuild using only:
- Public domain texts (Brenton, LXX2012, KJV, Schaff Fathers series, LSJ)
- Openly licensed texts (OCMC lectionary EPL-2.0, STEPBible CC-BY datasets)
- EOB and other texts if/when they become openly licensed

**Design principle for future-proofing:** Keep copyrighted content in clearly marked frontmatter fields (e.g., `osb_note:`, `nets_text:`) so a future public export script can simply omit those fields and replace them with public domain equivalents. The *structure* of the vault is always open; the *content* in personal fields is not.

### Personal PDF Sources Available
The following copyrighted translations are available for personal vault use via owned PDFs:
- OSB (Orthodox Study Bible) — text + study notes
- NETS (New English Translation of the Septuagint)
- EOB (Eastern Orthodox Bible)
- Lexham English Septuagint
- Others TBD

**Extraction strategy:** Claude Code + `pdfplumber` or `pymupdf` to extract and structure text chapter by chapter into Markdown. EPUB sources preferred where available (structured HTML is dramatically cleaner than PDF). Quality will vary by PDF formatting; manual cleanup likely needed for some volumes. All extraction scripts write per-book `_extraction-log.md` files documenting any interpretive transformations (see Extraction Logging under Phase 0). This unlocks the full ideal stack for Mode 1–4 without waiting for open-source equivalents.

### Future Public Vault — Design Principle

A future open-source version is a pie-in-the-sky aspiration, not a current goal. If it ever happens, it would use only public domain and openly licensed sources (LXX2012, Schaff Chrysostom, OCMC lectionary, Apostolic Fathers, `byztxt` Greek texts) and offer the *structure and linking* as the value — the texts are available everywhere, but nobody has wired them together in an Orthodox-liturgical graph. The architecture decisions already made (hub scope rule, source-keyed companion naming, clearly marked copyrighted frontmatter fields) make a future public export possible without a rebuild. That's sufficient future-proofing for now.

---

## Bidirectional Linking — Core Requirement

*This is the primary functional goal: study notes and Bible files must be able to find each other.*

### How It Works

Obsidian handles bidirectional linking automatically once a consistent convention is established. No plugins required for basic functionality.

**Forward links (study notes → Scripture):**
Anywhere a Scripture reference appears in any note, use the wikilink format instead of plain text:
```
[[John 1#v14]]          ← links to verse 14 anchor in John 1 chapter file
[[Romans 8#v28]]        ← same pattern throughout
[[Psalm 50#v10]]        ← LXX numbering is primary for Psalms
```

**Backlinks (Scripture → study notes):**
Automatic. The backlinks panel on any `[[John 1]]` chapter file will list every note in the vault that links to it — class notes, homily notes, podcast notes, Zettelkasten entries, daily notes. No manual maintenance required.

**The graph builds itself:** Every Lord of Spirits note, every Divine Liturgy class note, every Zettelkasten insight that cites Scripture becomes a visible connection in the vault graph. Over time the most-cited verses become the densest nodes — which is itself a form of Patristic hermeneutics (the verses the Fathers return to most are the ones worth dwelling on longest).

### Anchor Convention — DECIDED

All chapter files use `###### v[N]` (level-6 heading) for verse anchors:
```markdown
###### v1
<span class="vn">1</span> In the beginning was the Word... ^v1

###### v14
<span class="vn">14</span> And the Word became flesh... ^v14
```

**Canonical link format: `[[John 1#v14]]`**

The `v` prefix is non-negotiable — it prevents collisions with any other numbered headings that might appear in a chapter file (section headers, footnote numbers, etc.), and makes Scripture citations unambiguous when reading raw Markdown. Every import script, every template, every retroactive linking script must use this format without exception.

**Secondary hidden anchor:** keep a hidden per-verse block ID like `^v14` at the end of the verse when practical. This is a useful secondary anchor for implementation flexibility, transclusion, and compatibility, but it does **not** replace the canonical vault citation format above.

### Hub Verse Presentation — DECIDED

The desired chapter-hub reading experience is one visually continuous verse line per verse, not a detached verse-number heading followed by a separate paragraph.

**Required qualities**

- one actual verse per anchor
- visible verse number styled inline with the verse text using the established `.vn` treatment
- canonical `#vN` addressability preserved for normal vault links
- hidden per-verse `^vN` block IDs preserved as a secondary stability layer where possible
- no grouped multi-verse containers under one heading
- no visible-number corruption where the wrong heading number is shown and the real verse digit leaks into the verse body, such as `1In...`

The old Google Drive output proves the desired *feel* but not a safe extractor shape: it had inline-styled verse numbers, but it also garbled visible numbering and swallowed multiple verses into one anchor block. The current sample output preserves verse integrity but lost the intended reading layout. Phase 1 correctness work should restore the reading layout **without** reintroducing the old parsing bugs.

### Chapter Hub Scope Rule — DECIDED

The chapter hub file (`John 1.md`, `Romans 8.md`, etc.) is the load-bearing structure of the vault. To prevent it from accumulating complexity over time, enforce a strict boundary:

**The chapter hub contains ONLY:**
- Canonical text (Mode 1 translation)
- H6 verse anchors (`###### v14`) with inline `.vn`-styled verse numbers and hidden `^vN` block IDs
- A `> **Modes:**` navigation callout linking all mode companions and notes companions — this is part of the hub contract
- Breadcrumb frontmatter (`up`, `prev`, `next`)
- Identity/taxonomy frontmatter (`testament`, `genre`, `book_id`, `aliases`, `cssclasses: [scripture-hub]`)
- Optional reference-system frontmatter (`mt_ref`, `lxx_ref`) only where a modeled MT/LXX divergence is actually needed
- `intro:` frontmatter field on Chapter 1 hubs only, pointing to the book intro companion when one exists

**Everything else lives in companion notes (never added to the hub, never pulled via Dataview for navigation):**
- Mode 2/3/4 text → companion text files (e.g. `John 1 — EOB.md`, `John 1 — Greek NT.md`)
- OSB study notes → `John 1 — OSB Notes.md`
- NET apparatus → `John 1 — NET Notes.md`
- Liturgical feast mappings → `300-Liturgical Cycle/` day notes linking *back to* hub verses
- Patristic references → `400-Patristics/` notes linking *back to* hub verses
- `domestic_church` flag → personal notes in `000-Zettelkasten/` and `500-Orthodox-Life/`

**Dataview is for cross-cutting personal queries, not for companion navigation.** The `> **Modes:**` callout handles Bible-mode navigation inline. Dataview serves orthogonal concerns: domestic church filtering, liturgical day surfacing, all-notes-touching-a-verse reports. Scripture files stay static and identical between personal and public vault versions.

**Rationale:** The hub must be stable and structurally identical between personal and public vault versions. Growth happens in companion notes; the hub is a foundation, not a living document. When you want to add a new source, a new liturgical connection, or a new Patristic link, the answer is always "create or update a companion note," never "add another field to the chapter file."

**Canonical chapter hub frontmatter:**
```yaml
---
cssclasses: [scripture-hub]
testament: "NT"
genre: "Gospel"
book_id: "Jn"
aliases: ["Jn 1"]
up: "[[John]]"
prev: ""
next: "[[John 2]]"
# intro: "[[John — OSB Intro]]"   ← Chapter 1 only, when a book intro exists
---
```

#### Reference-System Fields (`mt_ref` / `lxx_ref`)

These fields exist to normalize citations across traditions, translations, and automation boundaries. They are **not** required on every hub file.

- **Use them when they solve a real mapping problem.** Their purpose is import normalization, retroactive citation linking, and source-to-source reconciliation, not everyday reading.
- **Current required use: Psalms.** The vault is LXX-primary for the Psalter, so `lxx_ref` stores the vault's canonical Psalm reference and `mt_ref` stores the MT equivalent.
- **Current default elsewhere: omit them.** For ordinary OT and NT chapter hubs, the file's own chapter reference is already the operative reference, so `aliases` are sufficient unless a specific divergent mapping is being automated.
- **Expansion rule:** add `mt_ref` / `lxx_ref` to non-Psalm hubs only after there is a concrete, concordance-backed need. No speculative boilerplate.

### Retroactive Linking of Existing Notes

Your existing notes (Lord of Spirits, class notes, etc.) contain plain-text Scripture references. Once the Bible files exist, a Claude Code script can:
1. Parse all notes for Scripture citation patterns (full list below)
2. Replace them with wikilinks (`[[John 1#v14]]`)
3. Report any ambiguous or unresolved citations for manual review

This means existing notes don't need to be manually updated — the script retrofits them once the Bible files are in place.

#### Citation Format Regex Spec

The script must recognize and normalize all of the following input formats to `[[Book Chapter#vVerse]]`:

**Colon-separated (most common):**
```
John 1:14
Jn 1:14
Jn. 1:14
1 John 1:14         ← numbered books with space
1Jn 1:14            ← numbered books without space
I John 1:14         ← Roman numeral prefix
```

**Period-separated:**
```
John 1.14
Jn. 1.14
```

**Verse with explicit marker:**
```
John 1 v. 14
John 1 v14
John 1 verse 14
```

**Ranges (link to first verse, flag range in display text):**
```
John 1:14-18        → [[John 1#v14|John 1:14-18]]
John 1:14–18        ← en-dash variant
John 1:14—18        ← em-dash variant
```

**Multi-verse same chapter:**
```
John 1:14, 16       → two separate links
```

**Cross-chapter ranges (flag for manual review — ambiguous):**
```
John 1:14-2:3       → flag, do not auto-link
```

**Parenthetical citations (common in Patristic notes):**
```
(John 1:14)
(cf. John 1:14)
(see John 1:14)
(cf John 1:14)
```

**Book abbreviation mapping:**
The script must maintain a full Orthodox canon abbreviation table covering all 73+ books including Deuterocanon, handling common variants:
```
Gen / Gn → Genesis
Ps / Psa / Psalm → Psalm      ← vault uses LXX numbering; MT-sourced citations must be translated via concordance
Sir / Ecclus → Sirach
Wis / Wisd → Wisdom
1 Mac / 1Macc / 1 Macc → 1 Maccabees
Tob / Tobit → Tobit
Jdt / Judith → Judith
Bar → Baruch
... etc.
```

**False positive guards — do NOT link:**
```
John 1:14 AM        ← time format collision
1 John Street       ← address
Chapter 1, verse 14 ← generic prose, not a citation
```

**Abbreviation safety assessment (tested across 9 Patristic sources):**

The following abbreviations were tested against Chrysostom, Symeon the New Theologian, Cult of the Saints, Apostolic Fathers (English and Greek/English editions), Maximos the Confessor, Nikodemos, Philokalia Vol. 1, and the Athonite Gerontikon:

- `Sir` (Sirach): **SAFE.** Zero false positives across all sources. Only appears as citations.
- `Wis` (Wisdom): **SAFE.** Zero false positives. Only appears as citations.
- `Bar` (Baruch): **SAFE.** Never appeared in any source at all.
- `Am` (Amos): **SAFE** when requiring `Am` + space + chapter:verse pattern.
- `Is` (Isaiah): **ONLY DANGEROUS ABBREVIATION.** 50+ false positives in Nikodemos alone ("Is" as English verb). Safe when requiring `Is` + space + digit + separator + digit.

All abbreviations are safe when the regex requires `{Abbreviation} {chapter}[.:]{verse}` — the chapter:verse pattern after the abbreviation eliminates false positives. The feared collisions with common English words do not occur in Patristic scholarly editions (SVS Press, Popular Patristics, CUA Press) because these abbreviations appear only in footnote apparatus, never in running prose.

**Source-specific cleanup required before linking (PDF sources):**

| Source | Issue | Cleanup |
|--------|-------|---------|
| Chrysostom (SVS PDF) | OCR-fused footnote numbers: `«I Cor`, `9Gen`, `®Rom`, `HI Cor` | Strip non-alphabetic characters immediately preceding book abbreviations |
| Philokalia (Palmer/Sherrard/Ware PDF) | OCR-damaged spaces in citations: `Luke 2 1 : 34`, `Ps. I 2 5 : 1` | Collapse spaces within citation patterns before linking |
| Apostolic Fathers Gk/Eng (Holmes PDF) | Mixed `Book.Ch:V` pattern: `Gen.4:3` | Handle period after book name as optional separator |
| Athonite Gerontikon | Uses full book names only: `Matthew 25:25-40` | Standard pattern handles this; no special cleanup |

**Separator convention varies by source — both MUST be supported:**
- **Colon** (`Jn 1:14`): Chrysostom, Nikodemos, Gerontikon
- **Period** (`Jn 1.14`): Symeon, Maximos, Apostolic Fathers (English), Cult of Saints
- **Mixed**: Apostolic Fathers Gk/Eng uses period for chapter.verse but colon within apparatus

**Psalm numbering varies by source — concordance required:**

| Numbering | Sources |
|-----------|---------|
| LXX (Ps 50 = Miserere) | Symeon, Philokalia |
| MT (Ps 51 = Miserere) | Nikodemos, Chrysostom, Apostolic Fathers (both editions) |

Each Patristic source imported into the vault needs a `psalm_numbering: LXX|MT` flag in its import configuration so the linking script knows whether to apply concordance translation.

**Edge case caution:** This assessment covers 9 sources from SVS Press, CUA Press, and other Patristic publishers. Other sources (monastic texts, older translations, non-English Patristic literature) may introduce citation patterns not yet seen. The linking script should log unrecognized patterns to `citation-errors.md` rather than silently skipping them, and new sources should be spot-checked against the regex before bulk processing.

**Additional patterns confirmed across sources:**
- Multi-citation chains: `Gen 2:24, Mt 19:5, Eph 5:31` — semicolons between books, commas between verses
- `ff.` suffix: `Gen 39:6 ff.`, `Mt 18:23ff.` — strip and link to first verse only
- `Cf.` / `cf` prefix: `Cf. Gen 3:15`, `cf 1 Cor 5:9` — strip prefix, link normally
- Numbered books use space: `1 Cor`, `2 Pet`, `1 Tim` — consistent across all sources

**Output behavior:**
- Successful match: replace in-place with wikilink
- Range: replace with aliased link preserving original text
- Ambiguous / cross-chapter range: leave plain text, append `%%CITATION_REVIEW%%` inline comment for manual triage
- Unknown abbreviation: leave plain text, log to a `citation-errors.md` report file
- Dry-run mode required before any destructive replacement — output diff to review first

### The Practical Result

From `[[John 1]]` you see every note you've ever written that touched that chapter. From your Lord of Spirits note you click through directly to the verse. Your class notes, homilies, Zettelkasten, and daily notes all become a commentary tradition on the Scripture — your own personal catena, built one note at a time.

---



*These are not new ideas — they are the vault architecture's job to support what already exists.*

### Frontmatter Schemas

Two distinct schemas govern different file types. The chapter hub schema is minimal by design (per the hub scope rule above); the personal/study note schema carries the richer metadata.

**Foldering decision:** Deuterocanonical books do **not** get their own top-level `Scripture/03 - Anagignoskomena/` tree. They live under `Scripture/01 - Old Testament/` beside the protocanonical OT books. Their distinction is semantic, not topological: frontmatter and canonical metadata identify them as Deuterocanonical.

#### Chapter Hub Frontmatter (Scripture files only)

```yaml
---
testament: "NT"
genre: "Gospel"
book_id: "Jn"
aliases: ["Jn 1"]
up: "[[John]]"
prev: ""
next: "[[John 2]]"
---
```

**Psalter hub frontmatter** (LXX-primary numbering — filename is `Psalms 50.md`):
```yaml
---
lxx_ref: "Psalms 50"
mt_ref: "Psalms 51"
testament: "OT"
genre: "Wisdom"
book_id: "Ps"
aliases: ["Ps 50", "Ps 51", "Psalms 51"]
up: "[[Psalms]]"
prev: "[[Psalms 49]]"
next: "[[Psalms 51]]"
---
```

#### Companion Note Frontmatter

```yaml
---
cssclasses: [scripture-hub]   # text companions; notes companions may use scripture-notes
hub: "[[John 1]]"
source: "EOB"
# layer_type, book, chapter optional — used for Dataview queries
---
```

Note: `mode:` numbers and `lxx_mt_divergence:` were dropped from the implemented schema. Source name is the stable key; mode numbers are internal jargon. LXX/MT divergence is tracked in the source structure docs, not per-chapter frontmatter.

### Validation & Regression Plan

High-level policy stays here. The detailed validator rule set, fixture matrix, and execution policy now live in `docs/validation-plan.md`.

The extractor should not rely on visual spot-checking alone. Before any future `--full` extraction is treated as trustworthy, the generated Markdown must pass an automated validation layer.

The high-level release policy is:

- treat validation as a release gate, not as optional QA
- validate generated hubs, generated companions, and run-level coverage
- require a representative sample run before any trusted full extraction
- preserve machine-readable failure output alongside human-readable terminal summaries
- keep the validator authoritative rather than fixing generated Markdown manually after the fact

The detailed rule catalog, failure record shape, fixture floor, source-specific fixture matrix, and execution behavior are maintained in `docs/validation-plan.md`.

#### Personal / Study Note Frontmatter (from existing notes)

The Lord of Spirits note establishes the real working schema. All personal and study notes should extend this:

```yaml
---
tags:
  - 🌱          # seedling (in-progress)
  - ⛪           # Orthodox
  - ⛪/class     # or /homily, /podcast, /reading, /media
topics:
  - keyword-array   # searchable theological terms
source: podcast     # class | homily | podcast | reading | spiritual-direction
up: "[[MOC Note]]"  # parent Map of Content
date-processed: YYYY-MM-DD
domestic_church: false     # ⌂ filter — true if applicable to family/vocation
---
```

### The ⌂ Filter — Revised Implementation

The `domestic_church: true` flag belongs on **personal notes** (`000-Zettelkasten/` and `500-Orthodox-Life/`), not on Scripture chapter files or verse anchors.

**Why:** A chapter-level flag is too coarse — all of Romans 8 is not domestic church material. A verse-level flag inside a chapter file would require something other than frontmatter (inline tags, dataview annotations), adding complexity to the hub file that violates the hub scope rule. The ⌂ judgment belongs in your own reflection, not baked into the text.

**Implementation:**
- `domestic_church: true` lives in the frontmatter of personal study notes, class notes, homily notes, and Zettelkasten entries
- Those notes link to specific verses via `[[Romans 8#v28]]`
- A Dataview query surfaces verses *transitively* — "show me all verses linked from notes where `domestic_church = true`"

```dataview
TABLE file.link AS "Note", filter(file.outlinks, (x) => contains(string(x), "Scripture")) AS "Verses"
FROM "000-Zettelkasten" OR "500-Orthodox-Life"
WHERE domestic_church = true
SORT file.mtime DESC
```

This is the digital equivalent of the physical ⌂ symbol in the OSB — mark it once, find it everywhere. The Dataview query becomes a personal domestic lectionary. The Scripture files stay clean and identical between personal and public vaults.

### Iconographic Color System → Tag Taxonomy

The existing color-coding system maps directly to a tag taxonomy for verse notes. Instead of losing the color meaning when moving from physical to digital, encode it:

| Physical Color | Theological Meaning | Vault Tag |
|---------------|--------------------|-|
| Gold/Yellow | Theophany, Christ's words, Uncreated Light | `⛪/type/theophany` |
| Blue | Divine realm, Theotokos, Holy Spirit | `⛪/type/pneumatological` |
| Red | Incarnation, Passion, Martyrdom | `⛪/type/incarnation` |
| White | Resurrection, Baptism, Purity | `⛪/type/resurrection` |
| Green | Pentecost, Holy Cross, New Life | `⛪/type/pneumatological` |
| Purple | Repentance, Lenten, Penitential | `⛪/type/penitential` |

### The 8-Step Study Workflow and Where the Vault Fits

The existing workflow card (Orient → Read → Deepen → Study → Mark → Serve → Devote → Close) maps to the vault at specific points — not at all points:

- **Step 2 (Read — Manley):** Vault provides the lectionary day link. Manley stays physical.
- **Step 3 (Deepen — Catena):** Mode 2 Patristic notes are the vault equivalent of Catena. Use sparingly — the card says max 2x/week, one Father.
- **Step 4 (Study — OSB):** Mode 1 chapter note. OSB stays physical for the worn-copy experience.
- **Step 5 (Mark):** The ⌂ flag and color tags are recorded in the vault *after* physical marking. Vault records what the physical copy marks.
- **Step 6 (Serve):** `domestic_church: true` in personal note frontmatter. The vault becomes a queryable record of teaching material for kids and arrow prayers for the father.
- **Steps 1, 7, 8:** Prayer, Prologue, Jesus Prayer — **not vault activity.** The vault serves the prayer; it does not replace it.

### Vault Exit Point

The daily note template should include a deliberate "close the vault" marker after the lectionary readings and any study prompts are rendered:

```markdown
---
*The vault has served its purpose for today. Close the screen. Pray.*

> Lord Jesus Christ, Son of God, have mercy on me, a sinner.
---
```

This is a design decision, not just a pious reminder. If the daily note template auto-populates with lectionary data and linked study prompts, the natural temptation is to keep scrolling, keep clicking, keep tending. The marker is the architectural equivalent of the prayer card's Step 7 (Devote) and Step 8 (Close) — the vault serves the prayer, then gets out of the way.

### Antiochian Parish Context

The Ascension bilingual vespers document reveals an important detail: your Antiochian parish uses **Arabic alongside English** in services. This means:
- The Arabic liturgical text is an existing layer of your worship experience
- Arabic transliteration of key liturgical phrases (كيري إيليسون, etc.) belongs in the Glossary alongside Greek
- This is also a clue about which RSV edition is in use — the Antiochian Gospel Book compiled by Bishop Demetri is the RSV, blessed by Patriarch Athenagoras, and is the same text used in Arabic-language Antiochian parishes worldwide

---

## Guiding Principles

- **Orthodox-first, not Protestant-accommodating.** Every architectural decision defaults to the Orthodox tradition — canon, versification, textual tradition, hermeneutics — even when this creates friction with existing tools.
- **English primary.** Greek is essential for lexical and theological precision, but English is the working language of the vault.
- **Offline and permanent.** Static Markdown files over dynamic API-dependent plugins wherever possible. The vault should be fully functional without internet access.
- **Linkable at the verse level.** All Scripture notes structured to support `[[Book Chapter#v1]]` transclusion and Dataview queries.
- **Liturgically grounded.** Scripture and Patristic notes are always contextualized within the liturgical life of the Church, not treated as isolated academic data.
- **Built to share.** Architecture should be clean enough that the vault (or a stripped version) could eventually be useful to other Orthodox users.

---

## Canon

- **Full Orthodox canon** — 73+ books including all Deuterocanon / Anagignoskomena
- Deuterocanonical books treated as fully canonical, not as "Apocrypha" or a separate tier
- Deuterocanonical books live under the OT Scripture folder, not a separate top-level Scripture subtree
- Greek additions to Daniel (Susanna, Bel and the Dragon) and Esther included with correct chapter labeling (A, B, etc. or 13–16 depending on versification scheme)

### OT Pseudepigrapha — Future Extension

The Old Testament Pseudepigrapha (1 Enoch, Jubilees, Testaments of the Twelve Patriarchs, Psalms of Solomon, 2 Baruch, 4 Ezra, etc.) are not canonical but illuminate the theological world of Second Temple Judaism — the "religion of the Apostles." NT authors presuppose familiarity with these texts (Jude directly quotes 1 Enoch; the Assumption of Moses is alluded to; the Testaments of the Twelve Patriarchs parallel Pauline ethics). The Fathers engaged with this literature, and Orthodox scholarship treats it as part of the broader tradition.

**Vault treatment:** Pseudepigrapha illuminate Scripture but are not Scripture. They belong in `100-References/Pseudepigrapha/` — a sibling of `Holy Tradition/`, not a child of it. This preserves the canonical boundary while keeping them in the reference layer where they can be cross-linked to the passages they illuminate. Source: Charlesworth 2-volume OTP collection (PDF, owned — 35MB+).

**Key texts with standardized chapter:verse divisions (use canonical hub-file architecture):**

| Text | Chapters | Vault Relevance |
|------|----------|----------------|
| 1 Enoch | 108 | High — Jude 14-15 quotes 1 En 1:9 directly; Watchers narrative foundational for Second Temple angelology (Lord of Spirits territory) |
| Jubilees | 50 | High — retells Genesis-Exodus with angelology, calendar theology |
| Testaments of the Twelve Patriarchs | 12 testaments, each with chapters | High — ethical content closely parallels Pauline epistles |
| Psalms of Solomon | 18 | Medium — messianic theology, pairs with canonical Psalms |
| 2 Baruch (Syriac Apocalypse) | 87 | Medium — post-destruction theology paralleling Revelation |
| 4 Ezra (2 Esdras 3-14) | 16 | Medium — theodicy, eschatology |
| Ascension of Isaiah | 11 | Low-medium — vision literature, Patristic reception |

**Texts without verse divisions** (Letter of Aristeas, Joseph and Aseneth, Life of Adam and Eve, etc.) use section-based files like Patristic texts rather than chapter/verse hubs.

**Linking convention:** Same format as canonical Scripture — `[[1 Enoch 1#v9]]`. The abbreviation table needs Pseudepigrapha entries (`1 En`, `Jub`, `T. Levi`, `Pss. Sol.`, `2 Bar`, `4 Ezra`, `Asc. Isa.`), though citations will be rare outside of academic notes and Lord of Spirits podcast notes.

**Not a Phase 1 item.** Phase 3 or later. The folder and graph color group are reserved now; integration happens when the canonical Scripture and Patristic layers are stable.

---

## Versification Strategy

**Dual-keyed: LXX-primary for Psalms, MT for book/chapter organization elsewhere.**

- **Psalter:** LXX numbering is the primary file ID. `Psalm 50.md` is "Have mercy on me, O God." MT equivalents are aliases: `aliases: ["Psalm 51", "Ps 51"]`. This aligns with the OSB (which uses LXX numbering natively), all Patristic citations, all liturgical sources, and the OCMC lectionary. The concordance table maps MT → LXX at the import boundary for Protestant-sourced tools (NET Bible PDF, external commentaries).
- **Everything else:** MT chapter/verse numbering for filenames, since even LXX-based English translations (OSB, NETS, Lexham) follow MT chapter sequence. For now, ordinary non-Psalm hubs do not need `lxx_ref` / `mt_ref`; add them only when a concrete, concordance-backed divergence is being automated.
- **Rationale:** The original plan used MT-primary everywhere for compatibility with existing tools. But the vault's driving principle is "Orthodox-first, not Protestant-accommodating." Every source that matters to this vault — OSB, Fathers, liturgy, Greek text — uses LXX psalm numbering. Putting the translation friction on foreign sources adapting to the vault, not the vault adapting to foreign sources, is the correct design.

### Psalter Internal Versification — Engineering Note

Beyond psalm-level numbering (LXX 50 = MT 51), the Psalter also diverges at the **verse level within each psalm**:

- MT Psalm 51:1-2 is the superscription; LXX Psalm 50 starts the text body at v1
- This means `#v1` is ambiguous — it could be MT v1 (superscription) or LXX v1 (first line of text)
- The offset is not uniform: some psalms differ by 1, some by 2, some align

**Decision:** Since the vault uses LXX psalm numbering, verse anchors in Psalm files follow **LXX verse numbers**. This means the OSB EPUB extraction can use verse numbers as-is with no translation. The concordance table is needed only at the boundary when importing MT-numbered sources (NET Bible, Protestant commentaries).

**Required: a verse-level concordance table.**
Build a JSON lookup file (`psalter-concordance.json`) that maps MT verse → LXX verse for every psalm where they diverge. The linking script consults this table when processing any MT-sourced Psalm reference.

**Implementation sequence:**
1. Build and test the linking pipeline on NT books first (no versification divergence)
2. Extract Psalms from OSB EPUB using LXX numbers directly — no concordance needed for this step
3. Build the concordance table for Psalms (approximately 90 psalms have internal verse-number offsets)
4. Use the concordance when importing MT-numbered sources or running the retroactive linking script on notes that may contain MT-numbered Psalm citations

**Jeremiah note:** The LXX chapter order for Jeremiah is substantially rearranged (not just renumbered). However, even LXX-based English translations (including the OSB) follow MT chapter order. The vault follows MT chapter order for Jeremiah. Document the divergence in the Jeremiah book MOC note so it's not lost.

---

## Four-Mode Architecture

The vault is organized around four distinct but interlinked reading modes. Every Scripture note is the hub; the modes are implemented as linked companion notes and frontmatter fields, not separate vaults. A reader can start in any mode and navigate to another without leaving the verse.

```
[[John 1#v14]]  ← canonical hub note (LXX numbering for Psalms; MT for all other books)
    ├── Mode 1: Liturgical/Familiar    → NKJV/OSB + Chrysostom + lectionary
    ├── Mode 2: Orthodox Study         → EOB/LXX + Patristic commentary
    ├── Mode 3: Language/Technical     → NET + full translator notes (on demand)
    └── Mode 4: Greek Original         → Patriarchal Text / LXX + lexicon links
```

Each mode is a companion note or frontmatter field linked from the hub — not a separate vault. A reader enters at whatever mode fits their purpose and navigates between them freely. The Greek mode (4) is the foundation the others translate from; Mode 1 is the door most people walk through.

### Mode 1 — Liturgical / Familiar
**Purpose:** What you hear at Liturgy. What the person in the pew has in their OSB. The default view.

- **NT text:** NKJV (via OSB) — the translation used in most Antiochian, GOA, and OCA parishes, and the basis of the OSB
- **OT text:** OSB SAAS (LXX-based) — endorsed by metropolitans of Antiochian, GOA, and OCA
- **Liturgical anchor:** OCMC lectionary data links each reading to its place in the Church calendar
- **Patristic layer:** John Chrysostom homily excerpt linked for Gospel and Epistle passages (he preached on most of the NT)
- **Design principle:** Familiar, minimal, devotional. No apparatus clutter. This is what you open on Sunday morning.

> **Jurisdictional note:** There is no single official English translation across North American jurisdictions. The NKJV and KJV are more common for liturgical use and are preferred as they follow the majority text of the original Greek New Testament. The OSB has received endorsements from Metropolitan Maximos of Pittsburgh (GOA), Metropolitan Philip (Antiochian), and Metropolitan Theodosius (OCA), making it the closest thing to a cross-jurisdictional standard for personal study. The OCA is the only jurisdiction to have issued a formal statement forbidding use of the NRSV in liturgical services — avoid NRSV entirely.

### Mode 2 — Orthodox Study
**Purpose:** Better translations and Orthodox-oriented scholarship. For deeper reading, catechesis, and connecting Scripture to the living Tradition.

- **NT text:** EOB (Eastern Orthodox Bible) — translated from the Byzantine Majority Text / Patriarchal Text; most internally consistent Orthodox NT available in English
- **OT text:** Lexham English Septuagint (primary) or LXX2012 (fallback) — modern scholarly translations directly from the LXX
- **Study notes:** OSB commentary excerpts (manual) + links to Chrysostom, Apostolic Fathers, and Philokalia
- **LXX/MT divergence:** Explicitly flagged where the two traditions differ with theological significance
- **Future layer:** Fr. John Romanides, modern Orthodox theological commentary where available digitally
- **Design principle:** Orthodox hermeneutic throughout. The Fathers read Scripture; we read Scripture with the Fathers.

### Mode 4 — Greek Original
**Purpose:** The source texts themselves. For prayer, study, and formation in the actual language of the NT and LXX. The mode that all English modes are ultimately translating from.

- **NT:** Patriarchal Text (Ecumenical Patriarchate 1904/1912) — source: `byztxt/greektext-antoniades` (public domain, parsed with morphology + Strong's numbers)
- **OT:** Rahlfs LXX 1935 — source: CCAT → `eliranwong/LXX-Rahlfs-1935` (SQLite database, morphology + Strong's numbers; requires CCAT user declaration)
- **Interlinear layer:** Links to BTB vault (separate, URI-linked) for word-by-word morphological breakdown
- **Lexicon links:** Every significant Greek term links to its LSJ entry (ancient/Patristic range) and TBESG (NT/LXX Strong's tagged)
- **Patristic Greek:** Key theological terms (θέωσις, νῆψις, μετάνοια, κένωσις, etc.) get their own Glossary notes in `300-Liturgical Cycle/Glossary/` with Patristic usage examples, not just dictionary definitions
- **Liturgical Greek:** Service texts (Trisagion, Cherubic Hymn, etc.) in Greek with links to corresponding Scripture sources — showing how the liturgy is woven from Scripture
- **Design principle:** Not a Greek course. The goal is *familiarity with the living language of the Church*, not academic fluency. Prioritize terms that appear in liturgy and the Fathers over comprehensive coverage.

> **Note on scope:** Full Greek interlinear in the main vault is expensive (performance, maintenance). The strategy is: Greek text as a mode-4 companion note, with heavy lifting delegated to BTB via `obsidian://` URI links. The main vault holds the *theologically significant* Greek — terms, key verses, liturgical texts — not a full parsed corpus.

### Mode 3 — Language / Technical
**Purpose:** Scholarly apparatus, translation transparency, textual criticism. For when you want to know *why* a word was translated a certain way, or what the Greek actually says.

- **NT text:** NET Bible with full 60,000+ translator notes (extracted from owned PDF, 1st ed.)
- **Greek text:** Patriarchal Text 1904/1912 (`byztxt/greektext-antoniades`) for NT; Rahlfs LXX 1935 (CCAT/`eliranwong`) for OT
- **Default delivery:** notes-first chapter companions; do not assume the NET translation itself deserves a separate full-text reading file in every case
- **Note types rendered as typed Obsidian callouts** (driven by `NoteType` enum in domain):
  - `[!note]` — study note / background (OSB `sn`, NET `sn`, general footnote)
  - `[!tn]` — translator note (NET `tn`, Lexham translator notes)
  - `[!info]` — textual variant / manuscript note (NET `tc`, EOB variant)
  - `[!alt]` — alternative rendering (EOB `alt`, Lexham alternative)
  - `[!quote]` — cross-reference citation
  - `[!liturgy]` — lectionary / liturgical marker (OSB liturgical notes)
  - `[!cite]` — patristic citation
  - `[!bg]` — background / map note
  - `[!parallel]` — parallel passage (planned)
- **Strong's links:** Where available, Greek words link to LSJ/TBESG lexicon entries
- **Design principle:** Maximum transparency. This is the mode for studying a passage, not praying it.

### OSB Note Taxonomy Policy

The OSB EPUB's auxiliary files are useful provenance buckets, but they are not always clean semantic categories. A note's **source file** and its **meaning** may diverge.

- Preserve the OSB source family in metadata. If a note came from `crossReference.html`, that fact should remain knowable even if the content is variant-like.
- Allow normalized semantic rendering on top of that provenance. If a note says "NU-Text omits..." it should be able to render with textual-variant styling even when the OSB stored it under cross references.
- Do not collapse provenance into presentation. The vault should be able to answer both "what did the OSB call this?" and "how should this feel to read in Obsidian?"

**Recommended future model for OSB companion notes:**

- `source_bucket`: raw OSB family such as `footnote`, `variant`, `cross_reference`, `liturgical`, `citation`, `alternative`, `background`, `translation`
- `semantic_kind`: normalized vault meaning such as `textual_variant`, `cross_reference`, `lectionary`, `patristic_citation`, `background_note`, `translation_note`
- CSS/callout styling should follow `semantic_kind`
- Raw provenance must remain available for debugging and future reclassification

**Implication for Romans 8 and similar chapters:** the current rendering is source-faithful but semantically clunky. That is an argument for dual taxonomy, not for throwing away the OSB source classification.

### Companion Note Reading Order Policy

Companion notes should read like an annotated chapter, not like a database export grouped by note family.

**Decision:** Order companion-note content by verse/pericope position in the chapter. Do **not** split OSB notes into large category-first sections such as `Textual Variants`, `Cross References`, `Lectionary`, followed later by the main study notes.

**Preferred rendering shape:**

- One verse/pericope anchor heading at a time, in ascending order
- Under that heading, stack all relevant note blocks for that verse/pericope
- Preserve visual distinction through callout/CSS styling and labels, not by forcing the reader to jump to a different section of the file

**Example direction:**

```markdown
### [[Romans 8#v1|8:1]]
Main study note text...

> [!variant] 8:1a
> NU-Text omits the rest of this verse.

### [[Romans 8#v3|8:3-4]]
Main study note text...

### [[Romans 8#v26|8:26]]
Main study note text...

> [!variant] 8:26a
> NU-Text omits *for us.*

> [!liturgy] 8:28-39
> This passage is read on days commemorating martyrs and monk martyrs.

### [[Romans 8#v36|8:36]]
> [!crossref] 8:36a
> [[Psalms 43#v22|Psalm 44:22]]
```

**Rationale:**

- Reading a chapter note should feel local and sequential
- All note material relevant to `Romans 8:36` should live near `Romans 8:36`
- CSS/callout styling already gives enough visual distinction without sacrificing navigability
- This approach scales better when more auxiliary note families are added (`alternative`, `background`, `translation`, Greek/NET technical notes)

### Unified Verse-Linked Entry Model

The detailed implementation contract for adapters, normalized models, render profiles, and **nav callout design** now lives in `docs/implementation-architecture.md`. See § "Shared Navigation Contract" for the canonical nav order, hub vs. companion scoping rules, NET text handling, and the `intro:` frontmatter convention for Chapter 1 hubs.

Future implementation should use one underlying verse-linked entry model across imported companion layers, while treating personal notes as a distributed backlink layer rather than a generated chapter companion.

The high-level architecture commitments are:

- use source-specific adapters, not one giant extractor
- normalize extracted data into a shared verse-linked domain model
- render through a small number of shared profiles rather than letting each source invent its own schema
- preserve both raw source provenance and normalized semantic meaning where the source taxonomy is messy
- keep imported layers chapter-bound when that matches the source, but allow personal and many Patristic layers to remain distributed

The strategic layer model is:

- hubs stay canonical-text-only and remain the stable anchor target
- OSB and NET are note-dominant companion layers, with verse/pericope ordering and semantic styling
- EOB, Lexham, and future Greek layers are primarily text companions
- Fathers are hybrid: curated chapter companions where useful, distributed source notes elsewhere
- Personal material remains Zettelkasten-style and links back into hub verses through backlinks and MOCs

The external ChatGPT proposal was useful as a UX sketch, but the project keeps these non-negotiable choices:

- canonical links remain `[[Book Chapter#vN]]`, not block refs
- hub structure remains H6 verse anchors plus canonical text paragraphs
- `hub` and `source` remain the primary companion metadata keys
- inline comments such as `%% type: %%` may be tolerated as output hints, but not as the authoritative data model

The detailed normalized entry shape, renderer profiles, layer-profile table, and proposal fit/conflict analysis now live in `docs/implementation-architecture.md`.

### Companion Note Naming Convention — DECIDED

Companion notes are keyed to the **source translation**, not the mode number, since mode numbers are internal jargon that will lose meaning over time.

**Pattern:** `{Chapter} — {Source}.md`

| Mode | NT Example | OT Example |
|------|-----------|------------|
| Mode 1 hub | `John 1.md` | `Genesis 1.md` |
| Mode 2 | `John 1 — EOB.md` | `Genesis 1 — NETS.md` |
| Mode 3 | `John 1 — NET.md` | `Genesis 1 — NET.md` |
| Mode 4 | `John 1 — Greek.md` | `Genesis 1 — LXX Greek.md` |
| OSB Notes | `John 1 — OSB Notes.md` | `Genesis 1 — OSB Notes.md` |

**Layer-specific naming refinements**

- When a layer is primarily an apparatus rather than a reading text, explicit names like `John 1 — NET Notes.md` are acceptable and may be preferable.
- `John 1 — NET.md` should imply that the file is functioning as the NET layer for that chapter, whether by carrying full text plus notes or a notes-first technical rendering.
- The Fathers layer is not required to exist for every chapter. `John 1 — Fathers.md` is a curated catena artifact, not a guaranteed generated companion.
- Personal notes are excluded from this naming convention because they are not a default chapter-companion layer.

**Companion note frontmatter includes:**
```yaml
---
hub: "[[John 1]]"
source: "EOB"
---
```

`mode:` numbers and `lxx_mt_divergence:` are not in the implemented schema. `source:` is the stable key. Optional fields `layer_type`, `book`, `chapter`, `cssclass` may be present.

**Folder location:** Companion notes live in a **per-chapter subfolder** within each book folder (e.g., `Holy Tradition/Holy Scripture/02 - New Testament/04 - John/Chapter 01/`). This prevents large book folders from accumulating thousands of flat files. The folder can be collapsed when not in use. See Folder Structure for the full layout.

---

## Translations

Detailed source availability, acquisition, and phase planning now live in `docs/source-roadmap.md`.

The high-level source strategy is:

- OSB remains the foundational source for canonical hub text and OSB note extraction
- Lexham is the preferred Phase 1 OT comparison layer
- EOB NT is the preferred Phase 1 NT comparison layer
- NET is a notes-first technical layer, not a default second reading Bible
- Greek sources are important but explicitly Phase 2 and should not block current Phase 1 work
- Fathers are hybrid: some sources justify curated chapter companions, many belong as distributed verse-linked notes
- Philokalia and similar ascetical corpora remain manual or distributed rather than default extraction targets

The strategic source principles are:

- prefer Orthodox or LXX-aligned witnesses for the main reading layers
- keep Psalter numbering LXX-primary
- preserve Greek as a future scholarly layer, not a prerequisite for the first usable vault
- choose the artifact that carries the real value of a source, which is why NET is notes-first and Fathers are not forced into universal chapter companions
- let later comparative layers enrich the system without changing the core hub or companion contracts

### Psalter-Specific Supplementary Translations

The Psalter is the one part of Scripture where specialized source treatment makes sense, but not at the cost of making the base mode system inconsistent too early.

- keep Lexham as the default Phase 1 OT Mode 2 comparison layer, including Psalms
- do not special-case Mode 2 for Psalms during the first implementation pass
- treat the Holy Transfiguration Monastery Psalter as a later liturgical Psalter supplement
- treat `The Psalms of David` as a later poetic/devotional Psalter supplement

If one Psalter-only source is promoted before the other, the HTM Psalter has the stronger Orthodox-liturgical rationale, while `The Psalms of David` is the structurally easier extraction target.

The detailed local-source inventory, source assessments, source prioritization, and Greek acquisition planning now live in `docs/source-roadmap.md`.

---

## Liturgical Integration

- **Primary data source:** OCMC orthodox-christian-lectionary (GitHub, EPL-2.0, JSON/CSV)
- **Supplementary source:** OSB EPUB `x-liturgical.html` — contains 369 liturgical cross-references mapping Scripture passages to specific feasts, fasting periods, and services (e.g., "read during Vespers on Great and Holy Saturday"). Linked from verse text via `ω` markers. This data can supplement the OCMC lectionary and provide additional feast-to-verse mappings.
- Maps to AGES Initiatives IDs for compatibility with parish digital service books
- Each liturgical day gets a note in `300-Liturgical Cycle/` with prescribed readings linked to verse notes
- Daily Note template (Templater) auto-populates current day's readings
- Reverse linking: verse notes show every liturgical occasion on which they are read (via Dataview or Linked Mentions)
- Major feasts, fasting periods, and the Paschal cycle tracked in existing `300-Liturgical Cycle/` subfolders

### Pericope-to-Chapter Mapping

The liturgical lectionary maps to **pericopes** (e.g., John 1:1-17 for Pascha), not to chapters. Because the vault uses chapter-based files, pericopes that span chapter boundaries require explicit handling.

**Single-chapter pericopes (most cases):**
The liturgical day note links to the chapter hub with a verse range:
```markdown
**Gospel:** [[John 1#v1|John 1:1-17]]
```
Invisible range links (per the adopted convention) ensure all verses in the pericope surface in backlinks:
```markdown
%%[[John 1#v2]][[John 1#v3]]...[[John 1#v17]]%%
```

**Cross-chapter pericopes (e.g., Matthew 16:24–17:8 for Transfiguration):**
The liturgical day note links to both chapter hubs:
```markdown
**Gospel:** [[Matthew 16#v24|Matt 16:24]]–[[Matthew 17#v8|17:8]]
%%[[Matthew 16#v25]]...[[Matthew 16#v28]][[Matthew 17#v1]]...[[Matthew 17#v7]]%%
```

**The lectionary import script must:**
1. Parse each pericope reference into start book/chapter/verse and end book/chapter/verse
2. Detect single-chapter vs. cross-chapter pericopes
3. Generate the appropriate visible link(s) and invisible range links
4. Handle edge cases: pericopes with verse gaps (e.g., "Luke 24:1-12, 36-53" — skipping vv. 13-35)

**Invisible range links are opt-in by default.** Automatic generation is limited to liturgical day notes and heavily-cited pericopes. Ordinary study notes and Patristic homily notes use only the visible first-verse link unless the user explicitly adds range links. This prevents the link count from scaling to tens of thousands before performance has been validated. (See Performance Budget below.)

**Daily note template (Templater):**
The template pulls the current day's pericope data from the lectionary note and renders it as a reading list with clickable links, not as raw wikilink syntax. Include a brief label for each reading (Epistle, Gospel, OT, Matins Gospel) drawn from the OCMC data.

---

## Folder Structure — DECIDED

**Actual live vault layout** (as of 2026-03-20):

```
Jasper/
├── 000-Zettelkasten/          # Atomic personal notes (existing)
├── 100-References/
│   ├── Pseudepigrapha/        # NOT under Scripture — sibling, not child
│   │   ├── 1 Enoch/           # Per-book subfolders where applicable
│   │   ├── Jubilees/
│   │   └── ...
│   ├── Lexicon/               # Strong's / LSJ / TBESG entries
│   └── Sources/               # Academic and reference works
├── 200-Daily Notes/           # (existing)
├── 300-Liturgical Cycle/      # (existing — expand with OCMC data)
│   ├── Bible Study/           # (existing — Jan 2026)
│   ├── Domestic Church/
│   ├── Fasting Periods/
│   ├── Glossary/
│   └── Major Feasts/
├── 400-Patristics/
│   ├── Philokalia/
│   ├── Chrysostom/
│   ├── Apostolic-Fathers/
│   └── _Index/                # MOC notes per Father
├── 500-Orthodox-Life/         # Classes, homilies, spiritual direction (existing concept)
├── Holy Tradition/            # Sacred content — no JD numbering applied here
│   └── Holy Scripture/
│       ├── 01 - Old Testament/   # OT books in canonical order (including Deuterocanon)
│       │   ├── 01 - Genesis/
│       │   │   ├── Genesis.md              ← book MOC
│       │   │   ├── Chapter 01/
│       │   │   │   ├── Genesis 1.md        ← chapter hub
│       │   │   │   ├── Genesis 1 — Lexham.md  ← Mode 2 companion (Lexham LXX)
│       │   │   │   ├── Genesis 1 — Greek LXX.md ← Mode 4 companion
│       │   │   │   ├── Genesis 1 — NET Notes.md
│       │   │   │   └── Genesis 1 — OSB Notes.md
│       │   │   ├── Chapter 02/
│       │   │   └── ...
│       │   ├── 02 - Exodus/
│       │   ├── 19 - Psalms/       # LXX-numbered
│       │   ├── 48 - Sirach/
│       │   ├── 49 - I Maccabees/
│       │   └── ...               # All 46 OT books including Deuterocanon
│       └── 02 - New Testament/   # NT books in canonical order
│           ├── 01 - Matthew/
│           │   ├── Matthew.md
│           │   ├── Chapter 01/
│           │   │   ├── Matthew 1.md
│           │   │   ├── Matthew 1 — EOB.md
│           │   │   ├── Matthew 1 — Greek NT.md
│           │   │   ├── Matthew 1 — NET Notes.md
│           │   │   └── Matthew 1 — OSB Notes.md
│           │   ├── Chapter 02/
│           │   └── ...
│           ├── 04 - John/
│           ├── 06 - Romans/
│           └── ...               # 27 book folders
├── Files/                     # (existing)
└── Templates/                 # (existing)
```

**Foldering decision: JD numbers on workflow, descriptive names on sacred content.** The top-level JD structure (`000-`, `100-`, `200-`, etc.) organizes personal workflow folders. `Holy Tradition/` sits alongside these as a top-level folder with no JD prefix — applying a catalog number to Scripture and the Fathers felt category-inappropriate. Within `Holy Scripture/`, the `01 - Old Testament/` and `02 - New Testament/` ordinal prefixes are navigational (file browser sort order), not JD categories.

**Per-book subfolders with per-chapter subfolders resolve the companion note folder question.** Each book folder contains the book MOC and one `Chapter NN/` subfolder per chapter. Without chapter subfolders, a typical Gospel folder (John, 21 chapters × 7 file types) would hold ~150 files flat. With chapter subfolders, each chapter folder holds 5–7 files, the book folder stays clean, and the book MOC sits naturally at the top. The largest book (Psalms, 150 chapters) distributes across 150 chapter folders rather than piling into one.

**Links are unaffected.** Obsidian resolves `[[John 1#v14]]` by filename, not path — as long as chapter filenames are unique across the vault (which they are), links work regardless of subfolder depth. The `up: "[[John]]"` breadcrumb resolves to `John.md` inside the `John/` folder.

**This also addresses the performance concern.** No single folder exceeds a few hundred files. Graph queries scoped by path (`path:"Holy Scripture/02 - New Testament"`) still work. Combined with the opt-in invisible range links policy, the vault should remain performant well past the 5,000 file threshold.

---

## Source File Inventory

This section is now mirrored in a more implementation-friendly form in `docs/source-roadmap.md`. Keep this file focused on high-level source priorities and use the roadmap doc for staged build planning.

At the goals level, the important source state is simply:

- local Phase 1 sources already justify building the first full reading vault
- OSB remains the strongest canonical foundation
- Lexham, EOB NT, and NET cover the next most valuable comparison and apparatus layers
- Greek, broader Patristic corpora, and secondary comparison sources remain later-phase expansions

The roadmap-level execution rule is:

- treat implementation as a gated sequence rather than a source grab-bag
- finish correctness and validation before expanding the source surface area
- only promote later layers once they fit the shared hub and companion contracts cleanly
- keep Greek acquisition deliberate and documented rather than ad hoc

For the detailed source inventory, phase ordering, acceptance gates, and Greek acquisition checklist, use `docs/source-roadmap.md`.

### Public / Open-Source Version (Future)

| Component | Source | Replaces |
|-----------|--------|---------|
| NT text | EOB if licensed openly, else LXX2012 NT / RSV-CE | OSB/NKJV |
| OT text | LXX2012 YAML → Markdown | NETS / Lexham |
| Study notes | None (NET notes are copyrighted; OSB notes are copyrighted) | OSB notes |
| Greek text | `byztxt/greektext-antoniades` (public domain) + CCAT LXX (verify NC-SA redistribution terms) | Same |
| Fathers | Schaff series + Apostolic Fathers | Same (already public domain) |

---

## Existing Vault Documents That Feed the System

These documents already exist in your Drive and should inform vault structure directly — not be recreated from scratch.

| Document | Relevance | Action |
|----------|-----------|--------|
| **Path of Entry into the Philokalia** | Sequencing guide for Philokalia reading — directly governs how `400-Patristics/Philokalia/` is organized and linked | Import as MOC note into `400-Patristics/Philokalia/` |
| **Psalm Memorization Order (Three-Year Ascent)** | Bibliographic architecture for Psalter engagement — maps to `Psalms/` folder structure and Templater daily note | Import as MOC into `Psalms/` or `300-Liturgical Cycle/` |
| **Ancient Christian Reading Plans and Practices** | Historical Patristic reading curricula — foundation for `400-Patristics/` sequencing | Reference document for vault design |
| **Orthodox Reading Plan Integration** | Synthesis of Patristic practice and modern workflow — your existing reading system | Import as hub note linking all reading-related MOCs |
| **Philokalic Lexicon (Terminology Research)** | Exhaustive Greek/ascetic term compendium — seed document for `300-Liturgical Cycle/Glossary/` | Parse into individual atomic Glossary notes per term |
| **Orthodox Bible Study System Development** | Earlier iteration of the current vault plan | Review for any decisions not captured here |
| **Prayer Rule (Catechumen)** | Defines the liturgical rhythm the vault serves | Link from `300-Liturgical Cycle/` hub; not to be replaced by vault activity |

---

## Technical Inspirations from General Obsidian Bible Projects

*Drawn from community research — adopted, adapted, or set aside based on Orthodox goals.*

### Adopted Directly

**CSS margin verse numbers.** H6 verse headings styled to appear in the left margin via custom CSS snippet, making chapter files read like a physical Bible rather than a markdown document.

**Heading anchors are canonical; block refs set aside for now.** The project currently standardizes on `[[John 1#v14]]`, not `[[John 1#^v14]]`. Mixed anchor systems are forbidden. Optional block IDs can be reconsidered later only if there is a compelling transclusion need and a full-vault migration plan.

**Invisible range links for verse stacking.** For citations spanning multiple verses, the visible link goes to the first verse; invisible wikilinks to remaining verses are appended inside `%%` comment blocks. This ensures every verse in a range surfaces the citing note in its backlinks panel. Add this to the retroactive citation regex spec — ranges become aliased links plus invisible stacked links rather than flagged for manual review. **Note:** Invisible range links are opt-in by default — automatic only for liturgical day notes and heavily-cited pericopes. See Performance Budget.

**Three-layer book hierarchy.** Every book gets its own MOC note sitting between chapter files and the canon hub:
```
[[⛪ Orthodox Life]]           ← canon hub (existing)
    └── [[John]]              ← book MOC note (new layer)
        └── [[John 1]]        ← chapter file
            └── ###### v14   ← verse anchor
```
Each book MOC contains: structure/outline, major themes, liturgical usage, key Patristic commentators, and links to related Glossary terms.

**Graph color grouping mapped to iconographic tradition:**

| Group | Query | Color |
|-------|-------|-------|
| OT Protocanon | `path:"Holy Scripture/01 - Old Testament"` | Gold/Ochre |
| Deuterocanon | `path:"Holy Scripture/01 - Old Testament" AND (Sirach OR Wisdom OR Maccabees OR Tobit OR Judith OR Baruch)` | Deep Gold |
| Psalter | `path:"Holy Scripture/01 - Old Testament/19 - Psalms"` | Purple |
| New Testament | `path:"Holy Scripture/02 - New Testament"` | Blue/Violet |
| Patristics | `path:"400-Patristics"` | Crimson |
| Liturgical Cycle | `path:"300-Liturgical Cycle"` | Green |
| Glossary | `path:"Glossary"` | White/Silver |
| Pseudepigrapha | `path:"Pseudepigrapha"` | Bronze/Copper |
| Personal Notes | `path:"000-Zettelkasten"` | Amber |

**Breadcrumbs navigation in frontmatter.** Add `up`, `prev`, and `next` fields to chapter file frontmatter for mobile navigation without the file browser.

### Adapted with Orthodox Modifications

**Local graph as liturgical-Patristic hermeneutic.** General projects use local graph to trace verse → NT quotation → sermon → commentary. For this vault the Orthodox equivalent is: verse → NT citation → Chrysostom homily → class note from Father Anthony → liturgical feast day. Set local graph depth to 3 as default. The graph visualizes the living Tradition.

**Logos integration (if applicable).** The `logos-refs` plugin creates formatted quote blocks with attribution when copying from Logos. If Logos is in the toolkit this complements PDF extraction for SVS Press Fathers titles available there.

### Recommended Plugins

- High priority: `Templater`, `Dataview`
- Medium priority: `Breadcrumbs`, `Bible Portal`
- Low priority: `Sync Graph Settings`, `Hover Editor`, `logos-refs`

### Set Aside

- community scraping/API solutions that are superseded by owned-source EPUB/PDF extraction
- sermon-prep or academic-bibliography workflows that do not serve the vault's real purpose
- atomic verse-file models that hurt readability and performance
- plugin-driven Scripture link generation that conflicts with the vault's canonical `[[Book Chapter#vN]]` convention

---

## Phase 0 — Diagnostic (Do First)

Before committing to implementation, inspect representative sample chapters and classify each source as `clean`, `usable`, or `problem`.

The governing diagnostic rules are:

- prefer EPUB over PDF whenever a real EPUB exists
- inspect actual chapter/verse structure before assuming a source is automatable
- evaluate PDF sources for page bleed, header/footer contamination, footnote interleaving, and OCR damage
- turn each assessment into a short findings note that drives extraction priority rather than relying on memory

The detailed source-by-source assessment outcomes now live in `docs/source-roadmap.md`.

### Extraction Logging — Preserve Source, Build Interpretation on Top

Every extraction script writes a `_extraction-log.md` file in each book folder documenting any transformations that involved interpretation — OCR corrections, ambiguous verse number resolution, collapsed spaces in damaged citations, stripped footnote artifacts. The log records what the raw source said and what the script interpreted it as.

**Why this matters:** When the Philokalia's OCR produces `Luke 2 1 : 34`, the script must decide whether that's `Luke 21:34` or `Luke 2:134`. When Chrysostom's PDF produces `HI Cor 6:16`, the script interprets that as `1 Cor 6:16`. These interpretations are usually correct, but when they're wrong, you need a trail back to the source to resolve it. The log provides that trail without bloating every chapter file with raw transcription data.

**Implementation:**
- EPUB sources (OSB): log is minimal — structured markup means almost no interpretation is needed
- PDF sources (EOB, NET, Chrysostom, Philokalia): log captures every OCR correction, collapsed space, stripped artifact, and ambiguous citation with the raw text and the interpreted result
- The linking script logs every citation transformation (plain text → wikilink) and flags low-confidence matches in `citation-errors.md`
- Logs live in the book folder alongside the files they document, not in a separate location

**Principle:** The vault notes contain the *interpreted* text — clean, linked, structured. The extraction logs contain the *evidence* for those interpretations. You review the logs once after each extraction run, resolve ambiguities, and the logs stay as a permanent record. This is the digital equivalent of penciling your corrections in the margin of a working copy while keeping the original text visible.

### Phase 1 Discipline — Use Before You Build

Once the OSB EPUB extraction script runs and the first chapter hubs are in the vault with H6 verse anchors — **stop coding.** Do not immediately parse the NET Bible notes, the EOB PDF, or the Patristic sources. Spend a week reading the OSB text *in the vault*. Test the `domestic_church` flag on a few personal notes. See if the daily note template serves your morning reading or creates a temptation to keep tweaking Dataview queries. Let the vault be a place of quiet encounter first and an engineering project second.

The driving philosophy says: *when the vault becomes the thing being tended, something has gone wrong.* The most likely moment for that to happen is the transition from Phase 0 (diagnostic) to Phase 1 (extraction). The engineering is interesting; the engineering is satisfying; the engineering is not the point. Extract one source, use it, then decide whether the next source actually serves your formation or just scratches the builder's itch.

---

## Out of Scope (For Now)

- Full morphological interlinear in main vault (BTB handles this as separate vault)
- OSB study notes (copyrighted — personal vault only via owned EPUB; excluded from public version)
- Lampe's Patristic Greek Lexicon (proprietary — no digital source)
- Automated Philokalia ingestion (owned digitally; targeted extraction only, not bulk ingest)

---

## Performance Budget — Mitigated by Architecture

The vault will eventually contain thousands of files:
- ~1,189 chapter hub files
- ~1,189 Mode 2 companion notes (growing to ~3,500+ across Modes 2–4)
- 365+ liturgical day notes
- Hundreds of Patristic homily notes
- Hundreds of Zettelkasten entries
- 73+ book MOC notes
- Lexicon entries (potentially thousands)

Obsidian handles this volume, but graph view and Dataview queries slow noticeably past ~5,000 files. Two architectural decisions mitigate this:

**1. Per-book subfolders** (see Folder Structure) ensure no single folder exceeds a few hundred files. The file browser remains navigable, books can be collapsed, and path-scoped graph queries still work. This is the primary structural mitigation.

**2. Invisible range links are opt-in by default.** Automatic generation is limited to liturgical day notes and heavily-cited pericopes only. Ordinary study notes and Patristic notes use only the visible first-verse link. This starts conservative; the policy can be loosened once performance has been measured at scale.

**Performance validation (after Phase 1 import):**
1. Build a representative data set: ~200 chapter files, ~50 companion notes, ~30 liturgical day notes with full invisible range links, ~50 Patristic notes
2. Measure: graph view render time, Dataview query time for the domestic_church query, vault search speed, mobile sync time
3. If performance degrades, consider:
   - Excluding `Lexicon/` from default search scope
   - Deferring Mode 3/4 companion notes to on-demand generation rather than pre-building for every chapter
   - Reducing graph view default depth

---

## Open Questions — RESOLVED

| Question | Decision | Rationale |
|----------|----------|-----------|
| **EOB availability** | Use owned PDF for extraction via pdfplumber. Owned EPUB assessed and rejected — it is a mechanical PDF-to-EPUB conversion with zero semantic markup (every page is a single `<p>` tag), corrupted verse numbers (superscripts converted to `?`, `"`, `*`, `!7`, `2°`, `*%` etc.), and footnotes mixed into body text. The EPUB is worse than the PDF because spatial position information is destroyed. | If a properly structured EPUB exists from New Rome Press, it might be worth purchasing separately, but the owned EPUB file is not usable. |
| **Lexham LXX access** | Parse owned EPUB already present locally. The XHTML structure includes chapter anchors, verse anchors, and linked footnotes, making EPUB extraction the preferred path. | No API dependency is needed for the personal vault as long as the owned EPUB remains available locally. |
| **Dual-keyed Psalter schema** | LXX numbering is primary for Psalms: `Psalms 50.md` = "Have mercy on me, O God." `lxx_ref`, `mt_ref`, and `aliases` remain explicit on Psalm hubs. Outside Psalms, dual refs stay optional until a real mapped divergence needs them. | Aligns with OSB, Patristic citations, liturgical tradition, OCMC lectionary, and Greek text sources without adding speculative metadata to every other hub. |
| **Philokalia strategy** | Owned texts (vols 1–5 + 2008 complete ed.) available; manual excerpts for vault notes, but full texts accessible for reference and targeted extraction of key passages | Physical friction principle still applies for *processing* — but having digital source means searchable reference and targeted passage extraction is possible |
| **Greek additions versification** | A/B/C chapter labeling (e.g., `Daniel A`) | Safer for cross-translation mapping; sequential numbering misaligns depending on whether additions are integrated or appended |
| **Patriarchal Text Greek source** | `byztxt/greektext-antoniades` on GitHub — public domain, parsed with morphological tags and Strong's numbers. AGES/GOA Digital Chant Stand investigated and ruled out (liturgical day format, no verse markup, incomplete coverage, restrictive license). | Confirms Mode 4 NT as scriptable in Phase 2. Robinson-Pierpont Byzantine Majority Text (`byztxt/byzantine-majority-text`) available as comparative reference. |
| **OT Greek source** | CCAT Rahlfs LXX 1935 via `eliranwong/LXX-Rahlfs-1935` — SQLite with morphology, Strong's numbers, Unicode. Requires CCAT user declaration for download. CC BY-NC-SA 4.0. | Personal vault use confirmed. Public vault redistribution requires further assessment of NC-SA terms. |
| **Deuterocanon abbreviation safety** | Tested `Sir`, `Wis`, `Bar`, `Am`, `Is` across 9 Patristic sources (Chrysostom, Symeon, Maximos, Nikodemos, Philokalia, Apostolic Fathers ×2, Cult of Saints, Gerontikon). All safe when requiring `{Abbr} {chapter}[.:]{verse}` pattern. `Is` (Isaiah) is the only abbreviation with false positives, but the chapter:verse requirement eliminates them. | Moved from open to resolved. Detailed findings in Citation Format Regex Spec section. Edge case caution remains: new sources should be spot-checked. |
| **NET Bible source** | Use owned PDF (1st ed.) for extraction via pdfplumber. Bible.org API set aside — avoids API dependency, redistribution concerns, and online requirement (vault is offline-first). | Personal vault only; NET notes are copyrighted. Public vault will have no study note layer. |
| **CCAT LXX access** | Download directly from CCAT with user declaration. Use `eliranwong/LXX-Rahlfs-1935` derivative (CC BY-NC-SA 4.0) for the SQLite database with morphology and Strong's numbers. | Manual download; no redistribution concerns for personal vault. |
| **Companion note folder convention** | Per-book subfolders within `Holy Scripture/02 - New Testament/` and `Holy Scripture/01 - Old Testament/`. Deuterocanonical books live inside the OT tree rather than a separate Deuterocanon tree. Each book gets its own ordinal-prefixed folder (e.g., `04 - John/`, `48 - Sirach/`) containing the book MOC, all chapter hubs, and all companion notes for that book. | Without subfolders, NT alone would put 1,300+ files in a flat folder. Per-book subfolders keep the largest folder (Psalms) at ~750 files and a typical Gospel folder at ~105 files. Deuterocanonical books remain structurally integrated with the OT while still being distinguishable by metadata. Links are unaffected — Obsidian resolves by filename, not path. |
| **Performance at scale** | Mitigated by two architectural decisions: per-book subfolders (no single folder exceeds a few hundred files) and opt-in invisible range links (automatic only for liturgical day notes). | Remaining validation is empirical — measure after Phase 1 import. The architecture is designed to stay well under Obsidian's ~5,000 file performance threshold per folder. |
| **Bible Linker plugin** | Set aside. Evaluated `kuchejak/obsidian-bible-linker-plugin` (v1.5.15, MIT, 103 stars). The plugin uses comma as chapter:verse input separator (European convention) — all vault sources use colon or period. The "Link" and "Copy" commands generate inconsistent output formats (developer marked the discrepancy "wontfix"). Invisible range links use empty-alias format (`[[Gen-01#v1\|]]`) rather than `%%` comment blocks. Most fundamentally, the plugin solves a problem the vault doesn't have — it's designed for users without Bible files who need the plugin to build links. This vault *has* Bible files (OSB EPUB, script-ready), a retroactive linking script handles existing notes, and Obsidian's native autocomplete handles forward linking as you type. The plugin adds a layer of indirection that's slower than typing `[[John 1#v14]]` directly. | Retroactive linking script is authoritative for existing notes. Obsidian autocomplete is sufficient for new notes. No plugin needed. |

### Canonical Psalter Frontmatter Schema
```yaml
lxx_ref: "Psalms 50"
mt_ref: "Psalms 51"
aliases: ["Ps 50", "Ps 51", "Psalms 51"]
```

## Open Questions — REMAINING

*All open questions resolved.* The vault spec is ready to build from.

---

## Usage Patterns & UI Spec

*This section defines the practical, day-to-day user experience of the architecture. It serves as the acceptance criteria for the extraction scripts and linking habits.*

### 1. Mode Navigation (The Callout Bar)

Navigation between translations and original languages happens via a consistent markdown callout bar at the top of every chapter hub and companion note.

**Chapter Hub View** (canonical nav order — all modes and notes companions):

```markdown
---
cssclasses: [scripture-hub]
testament: "NT"
genre: "Gospel"
book_id: "Jn"
aliases: ["Jn 1"]
up: "[[John]]"
prev: ""
next: "[[John 2]]"
---
> **Modes:** [[John 1|OSB]] · [[John 1 — EOB|EOB]] · [[John 1 — NET|NET]] · [[John 1 — Greek NT|Greek NT]] · [[John 1 — NET Notes|NET Notes]] · [[John 1 — EOB Notes|EOB Notes]] · [[John 1 — OSB Notes|Study Notes]]

###### v1
<span class="vn">1</span> In the beginning was the Word, and the Word was with God, and the Word was God. ^v1

```

**Companion Text View** (scoped nav — hub + own notes + NET Notes only):

```markdown
---
hub: "[[John 1]]"
source: "EOB"
---

> **Nav:** [[John 1|Hub]] · [[John 1 — EOB Notes|EOB Notes]] · [[John 1 — NET Notes|NET Notes]]

```

**Companion Notes View** (scoped nav — hub + NET Notes only):

```markdown
---
hub: "[[John 1]]"
source: "OSB"
---

> **Nav:** [[John 1|Hub]] · [[John 1 — NET Notes|NET Notes]]

```

*Result:* In reading mode, this renders as a clean, clickable navigation bar. You can flip from the OSB to the Greek text instantly, maintaining your place at the chapter level.

### 2. Companion Note Flow

Companion notes should be verse-ordered, not category-ordered.

**Bad pattern:**

- `## Textual Variants`
- `## Cross References`
- `## Lectionary`
- then much later the main verse-by-verse study notes

**Preferred pattern:**

- `### [[Romans 8#v1|8:1]]`
- main note first when present
- auxiliary notes for `8:1a`, `8:1b`, etc. directly underneath
- next verse/pericope block in ascending order

This keeps `8:36` material near `8:36`, instead of forcing the reader to scan the entire file for each note family separately.

### 3. Backlink Discovery (The Catena Effect)

You do not manually link Scripture verses to your notes. You link your notes to the Scripture, and Obsidian builds the connections automatically via the Backlinks panel.

When you open `John 1.md` and view the Backlinks panel, you will see a living catena:

* `📝 Lord of Spirits - Augustine and Original Sin.md`
* `📖 Chrysostom - Homily 1 on John.md`
* `⛪ Nativity of Christ.md` (liturgical day)

Every `[[John 1#v1]]` written anywhere in the vault enriches this panel. The local graph view (depth 3) visually maps this: `John 1` → `Chrysostom Homily 1` → `Divine Liturgy Class Note` → `Liturgical Feast Day`. The graph visualizes the living Tradition as a network.

### 4. Multi-Verse Range Linking (Invisible Stacking)

When writing a note that references a passage rather than a single verse, use the visible/invisible stacking pattern to ensure all verses register the backlink.

**Syntax:**

```markdown
The Prologue ([[John 1#v1|John 1:1-6]]) establishes...
%%[[John 1#v2]][[John 1#v3]][[John 1#v4]][[John 1#v5]][[John 1#v6]]%%

```

**Behavior:** In reading mode, this renders as a single, clean link: "The Prologue (John 1:1-6) establishes...". However, the invisible `%%` block ensures that if you open verse 3 or verse 5, this note still correctly appears in their respective backlinks panels.
*Note: This is opt-in for personal notes, but mandatory for the automated lectionary and Patristic extraction scripts.*

### 4. Synoptic Parallels (Organic Growth)

Do not pre-populate comprehensive synoptic parallel tables. The vault should reflect your lived experience with the text, not a downloaded academic database.

**Implementation:**

* A `## Synoptic Parallels` section exists as a placeholder in the Book MOC notes (e.g., `Matthew.md`).
* Populate this table manually *only* when a parallel strikes you during reading, or when it becomes relevant for the domestic church.
* Granular, verse-level parallels are handled by extracting the existing cross-references into the `[[Chapter — OSB Notes.md]]` companion files.
