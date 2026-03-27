# Refactor Analysis & Findings

**Date:** 2026-03-23
**Focus:** Pre-implementation analysis for Taxonomy Refactor (Plan: `docs/taxonomy-refactor-plan.md`)

---

## 1. Source Consistency (NET vs OSB)

**Objective:** Verify semantic equivalence between NET `sn` notes and OSB `study` notes to determine correct slot mapping.

**Findings:**
*   **Current State:**
    *   `net_epub.py` maps `sn` (Study Note) → `citations` slot.
    *   `net_epub.py` maps `tn` (Translator's Note) → `footnotes` slot.
    *   `osb_epub.py` maps `study` (Study Note) → `footnotes` slot.
    *   `osb_epub.py` maps `citation` (Patristic) → `citations` slot.
*   **Analysis:** The current mapping mixes NET's primary study notes (modern evangelical commentary) with OSB's Patristic citations. This is semantically incorrect and pollutes the `citations` slot, making it impossible to filter for "Church Fathers only".
*   **Recommendation:**
    *   Map NET `sn` → `footnotes` (aligns with OSB `study` notes).
    *   Map NET `tn` → `translator_notes` (new slot).
    *   Map NET `map` → `cross_references` (unchanged).

## 2. Renderer Logic (`renderer.py`)

**Objective:** Assess scalability of `render_notes` for 5 new slots and verify `_CALLOUT` map strategy.

**Findings:**
*   **Structure:** `render_notes` iterates through hardcoded slots (`footnotes`, `variants`, etc.) and appends to a `tagged` list for sorting.
*   **Scalability:** The pattern is manual but robust. Adding new slots requires:
    1.  Adding to `_CALLOUT` map.
    2.  Adding a new iteration loop in `render_notes`.
*   **NET Rendering:** `render_net_notes` has its own hardcoded logic and `_NET_CALLOUT` map.
    *   Currently maps `citations` → `[!sn]` (Study Note).
    *   Currently maps `footnotes` → `[!tn]` (Translator's Note).
*   **Action Required:**
    *   Update `render_net_notes` to iterate over `translator_notes` (mapped to `[!tn]`).
    *   Update `render_net_notes` to iterate over `footnotes` (mapped to `[!sn]`).

## 3. Test Gap Analysis

**Objective:** Identify test fixtures requiring updates to support the refactor.

**Findings:**
*   **Fixture:** `tests/conftest.py::john1_net_notes` explicitly constructs a `ChapterNotes` object with `tn` in `footnotes` and `sn` in `citations`.
*   **Tests:** `tests/test_net_notes_rendering.py` asserts the presence of `[!tn]` and `[!sn]` callouts but does not validate *which* slot they come from (since it trusts the fixture).
*   **Risk:** Simply changing the adapter without updating the fixture would cause tests to pass (rendering looks correct) while the data model remains incorrect in the test environment.
*   **Action Required:**
    *   Update `john1_net_notes` fixture in `conftest.py` to place `tn` in `translator_notes` and `sn` in `footnotes`.
    *   Update `tests/test_net_notes_rendering.py` to assert correct slot usage if possible, or rely on the fixture update.

## 4. Implementation Adjustments

Based on these findings, the implementation plan in `docs/taxonomy-refactor-plan.md` is confirmed with the following specific mapping for NET:

| NET Note Type | Old Slot | New Slot | Callout |
|---|---|---|---|
| **tn** (Translator) | `footnotes` | `translator_notes` | `[!tn]` |
| **sn** (Study) | `citations` | `footnotes` | `[!sn]` |
| **tc** (Text-Critical) | `variants` | `variants` | `[!tc]` |
| **map** (Map) | `cross_references` | `cross_references` | `[!map]` |

This ensures:
1.  **Semantic Purity:** `citations` contains only Patristic/Ancient sources (OSB).
2.  **Structural Alignment:** `footnotes` contains primary commentary for that edition (OSB Study, NET Study).
3.  **Distinct types:** `translator_notes` captures technical translation data separately.
