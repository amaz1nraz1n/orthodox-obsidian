# Content Taxonomy Refactor — Design Plan

**Status:** Approved — all decisions confirmed, ready for implementation
**Date:** 2026-03-23
**Bead:** orthodox-obsidian-94

---

## Problem Statement

The domain model's content taxonomy is incomplete and semantically overloaded. This makes downstream filtering, callout styling, and future adapter routing unreliable.

### Semantic conflation (things crammed into wrong slots)

| Slot | What's actually in it | What should be there |
|---|---|---|
| `ChapterNotes.footnotes` | Study/commentary notes **+** translator's notes **+** background/geographical notes | Study/commentary notes only |
| `ChapterNotes.variants` | Textual variant notes **+** translation alternatives ("Or: *spirit*") **+** translation notes | Textual variant notes only |
| `ChapterNotes.cross_references` | Scripture cross-refs **+** map/geography references (NET) | Scripture cross-refs only |

### Missing domain types

| Missing concept | Where it appears in sources | Current state |
|---|---|---|
| `BookIntro` | OSB per-book intro prose | Extracted via ad-hoc `osb_epub.read_intros()` as raw `(str, str)` tuple — not in domain model or port interface |
| `ChapterIntro` | Some scholarly editions (DBH, etc.) | Not modeled anywhere |
| `parallel_passages` | OSB `<p class="sub2">` — 303 instances like "(Mt 3:1–6; Mk 1:1–6)" | Skipped entirely during extraction |
| ~~`study_notes`~~ | Dropped — no source has commentary requiring a slot distinct from `footnotes`. Range notes use `StudyNote.ref_str`; topical essays use `StudyArticle` in `articles`. | N/A |
| `translator_notes` | NET `tn`, Lexham footnotes (both are translator rationale, not commentary) | Currently in `footnotes` |
| `alternatives` | OSB `alternative.html` — "Or: *spirit*" type notes | Currently folded into `variants` |
| `background_notes` | OSB `background.html` — historical/geographical context | Currently folded into `footnotes` |

### Port interface gap

`read_intros()` exists only on `OsbEpubSource`, not on the abstract `ScriptureSource` port. No other adapter can advertise intro support without bypassing the contract.

---

## Full Content Taxonomy (reference)

### Layer 1 — Verse Text
- Canonical verse text (`Verse.text`) ✅
- Source language text (Greek NT, LXX) ✅

### Layer 2 — Structure
- Pericope headings (`Chapter.pericopes`) ✅
- Psalm superscriptions (currently treated as v1 — LXX-correct but semantically distinct) ⚠️
- Chapter intro paragraphs (prose before v1) ❌ not modeled
- Book introductions ⚠️ extracted but not in domain
- Parallel passage references (e.g., "(Mt 3:1–6)") ❌ skipped
- Poetry line structure (flat in all adapters) ❌ known gap

### Layer 3 — Per-verse Annotations
- Study/commentary notes (`footnotes`) ✅ but conflated
- Translator's notes (`footnotes`/`variants`) ⚠️ conflated
- Textual variant notes (`variants`) ✅ but conflated
- Translation alternative notes (`variants`) ⚠️ conflated
- Background/geographical notes (`footnotes`) ⚠️ conflated
- Cross-references (`cross_references`) ✅
- Map references (`cross_references`) ⚠️ conflated
- Lectionary/liturgical annotations (`liturgical`) ✅
- Patristic citations (`citations`) ✅

### Layer 4 — Thematic Articles
- Inline study articles (`ChapterNotes.articles`) ✅ OSB gray boxes

### Layer 5 — Canonical/Liturgical Metadata
- Kathisma/stasis groupings (hard-coded in canon.py, emitted as frontmatter) ⚠️
- Lectionary pericope assignments (separate `extract_lectionary.py` script) ⚠️

### Layer 6 — Text Markup (lost in all adapters — known gaps)
- Implied/added words (EOB `{word}`, OSB `<i>`)
- Poetry line structure
- Red-letter text (not in current sources)

---

## Proposed Solution

### New domain types (`models.py`)

```python
@dataclass
class BookIntro:
    """Book-level introduction prose from a source."""
    book: str
    source: str
    content: str  # Markdown-formatted

@dataclass
class ChapterIntro:
    """Optional prose preamble before verse 1 of a chapter."""
    book: str
    chapter: int
    source: str
    content: str  # Markdown-formatted

@dataclass
class PartIntro:
    """Introduction spanning a group of books (e.g. Alter's 'Torah', 'Historical Books').

    No adapter is required to produce these — most sources have no part structure.
    Placeholder for multi-book editorial introductions and future personal vault
    part-level notes (e.g. a user's own 'Introduction to the Prophets').
    """
    part_name: str   # e.g. "Torah", "Historical Books", "Wisdom Literature"
    source: str      # e.g. "Robert Alter", "Personal"
    content: str     # Markdown-formatted
```

### New fields on `ChapterNotes`

```python
# New fields (all default to empty — backward compatible)
translator_notes: List[StudyNote] = field(default_factory=list)  # NET tn, Lexham footnotes
alternatives: List[StudyNote] = field(default_factory=list)      # OSB alternative.html
background_notes: List[StudyNote] = field(default_factory=list)  # OSB background.html
parallel_passages: List[StudyNote] = field(default_factory=list) # OSB sub2 (deferred extraction)
chapter_intro: Optional[ChapterIntro] = None
```

**Key decision**: `footnotes` stays as the general commentary slot (OSB study notes, NET `sn`, EOB). `study_notes` was dropped — no current or planned source has a commentary type that needs a slot distinct from `footnotes`. Range/section notes (e.g. 1:1–3) are `StudyNote` objects with `ref_str` capturing the range; broad topical essays are `StudyArticle` in `articles`.

### New callout mappings (`renderer.py`)

```python
_CALLOUT = {
    # existing
    "footnote":         "",
    "variant":          "[!info]",
    "cross_reference":  "[!quote]",
    "liturgical":       "[!liturgy]",
    "citation":         "[!cite]",
    # new
    "translator_note":  "[!tn]",
    "alternative":      "[!alt]",
    "background_note":  "[!bg]",
    "parallel_passage": "[!parallel]",
}
```

### Port interface (`source.py`)

```python
def read_intros(self) -> Iterator[BookIntro]:
    """Yield BookIntro objects. Default: yield nothing (non-abstract)."""
    return iter([])
```

### Adapter re-routing

| Adapter | Content | Current slot | Correct slot |
|---|---|---|---|
| `osb_epub` | `alternative.html` | `variants` | `alternatives` |
| `osb_epub` | `background.html` | `footnotes` | `background_notes` |
| `osb_epub` | `translation.html` | `variants` | `translator_notes` |
| `net_epub` | `tn` notes | `footnotes` | `translator_notes` |
| `lexham_epub` | footnotes | `footnotes` | `translator_notes` |

---

## Implementation Phases

### Phase 1 — Domain model expansion
**Files:** `vault_builder/domain/models.py`
**Change:** Add `BookIntro`, `ChapterIntro`, `PartIntro` dataclasses; add 5 new fields + `sorted_` methods to `ChapterNotes`
**Tests:** New `tests/test_domain_model.py` — field defaults, sorted methods, instantiation of all three new types

### Phase 2 — Port interface update
**Files:** `vault_builder/ports/source.py`
**Change:** Import `BookIntro`; add non-abstract `read_intros()` with empty default
**Tests:** New `tests/test_source_port.py` — default `read_intros()` returns empty iterator

### Phase 3 — Renderer callout map
**Files:** `vault_builder/adapters/obsidian/renderer.py`
**Change:** Add 5 new `_CALLOUT` entries; add new slots to `render_notes()` tagged list; add `translator_note` to `_NET_CALLOUT`; add `translator_notes` read to `render_net_notes()`
**Tests:** New `tests/test_taxonomy_rendering.py` — one test per callout type; sort-order test across all 10 families

### Phase 4 — OSB adapter re-routing
**Files:** `vault_builder/adapters/sources/osb_epub.py`, `scripts/extract_osb.py`
**Change:** Re-route 3 misrouted passes to correct slots; `read_intros()` yields `BookIntro` domain objects
**Tests:** New `tests/test_osb_routing.py` — verify correct slot per note family; BookIntro instantiation

### Phase 5 — NET adapter re-routing
**Files:** `vault_builder/adapters/sources/net_epub.py`, `tests/conftest.py`
**Change:** `tn` → `translator_notes` in `_NOTE_TYPE_TO_SLOT`; update conftest fixtures
**Tests:** Add to `tests/test_net_epub_parsing.py` — verify tn lands in `translator_notes`

### Phase 6 — Lexham adapter re-routing
**Files:** `vault_builder/adapters/sources/lexham_epub.py`, `tests/conftest.py`
**Change:** Lexham footnote append → `translator_notes`; update conftest fixtures
**Tests:** Add to existing Lexham test files

### Phase 7 — Skill file updates
**Files:** `.claude/skills/audit-source/SKILL.md`, `build-source/SKILL.md`, `verify-source/SKILL.md`
**Change:** Add full taxonomy checklist to audit; add new slot verification to build + verify

---

## Files Modified

| File | Phase |
|---|---|
| `vault_builder/domain/models.py` | 1 |
| `vault_builder/ports/source.py` | 2 |
| `vault_builder/adapters/obsidian/renderer.py` | 3 |
| `vault_builder/adapters/sources/osb_epub.py` | 4 |
| `scripts/extract_osb.py` | 4 (call site) |
| `vault_builder/adapters/sources/net_epub.py` | 5 |
| `vault_builder/adapters/sources/lexham_epub.py` | 6 |
| `tests/conftest.py` | 5 + 6 (fixture migration) |
| `.claude/skills/audit-source/SKILL.md` | 7 |
| `.claude/skills/build-source/SKILL.md` | 7 |
| `.claude/skills/verify-source/SKILL.md` | 7 |

**New test files:**
- `tests/test_domain_model.py`
- `tests/test_source_port.py`
- `tests/test_taxonomy_rendering.py`
- `tests/test_osb_routing.py`

---

## Risks

| Risk | Mitigation |
|---|---|
| `conftest.py` fixture migration (Phases 5/6) breaks rendering tests mid-phase | Fixture change and slot migration land in the same commit per phase |
| `render_net_notes` reads both `footnotes` + `translator_notes` during transition → duplicate output | Between Phase 3 and Phase 5, `translator_notes` is always empty in real data — no duplication |
| `extract_osb.py` call site breaks after Phase 4 `read_intros()` signature change | Updated in same commit as `osb_epub.py` change |
| OSB `_collect_footnotes` accepts arbitrary string as `slot` — typo silently ignored | New slot names match field names exactly; routing tests catch misrouting |

---

## Decisions Needed Before Implementation

**1. `read_intros()` non-abstract with empty default ✅ CONFIRMED**
Avoids forcing NET, Lexham, EOB, Greek, LXX adapters to implement a method they have no data for.

**2. `footnotes` stays as-is (no rename) ✅ CONFIRMED**
OSB's `study1.html`–`study11.html` content continues populating `footnotes`. (`study_notes` dropped — no concrete use case.)

**3. NET `sn` notes → `footnotes` ✅ CONFIRMED**
Route `sn → footnotes` (Option A). General explanatory commentary stays together; `citations` slot is strictly Patristic sources. Phase 5 scope expands: NET adapter re-routing covers both `tn → translator_notes` AND `sn → footnotes` (currently `sn → citations`).

**4. `parallel_passages` extraction deferred ✅ CONFIRMED**
Slot added to domain model now; OSB `<p class="sub2">` extraction is a separate future task.

---

## Success Criteria

- All existing tests pass without modification (except conftest fixture updates in Phases 5/6)
- `ChapterNotes` has 6 new fields with correct defaults
- `BookIntro`, `ChapterIntro`, and `PartIntro` exist in `models.py`
- `ScriptureSource.read_intros()` defined at port level, returns `Iterator[BookIntro]`
- OSB `alternative.html` renders `[!alt]`, `background.html` renders `[!bg]`, `translation.html` renders `[!tn]`
- NET `tn` notes in `translator_notes`, `footnotes` empty for NET
- Lexham notes in `translator_notes`, `footnotes` empty for Lexham
- At least 20 new test functions
