# PDF Extraction Evaluation Report

**Date:** March 24, 2026
**Subject:** Deep-dive evaluation of PDF extraction accuracy (NOAB RSV).

## Executive Summary
We evaluated `pdfplumber` and `PyMuPDF` (fitz) against the current `pdfminer` baseline, specifically looking at their ability to distinguish verses, footnotes, and headers in the complex NOAB layout.

**Recommendation:** **Migrate to `pdfplumber`.**
While `PyMuPDF` is faster, `pdfplumber` offers significantly better out-of-the-box accuracy for text coherence (handling spaces/words correctly) and provides a more Pythonic API for layout analysis which is critical for separating footnotes from verse text.

## Comparative Analysis

| Feature | `pdfplumber` | `PyMuPDF` (fitz) | Current (`pdfminer`) |
| :--- | :--- | :--- | :--- |
| **Speed** (Sample) | ~0.8s / page | **~0.2s / page** | ~1.5s / page |
| **Text Coherence** | **Excellent.** Words are properly spaced. | Poor. Often fragments words or misses spaces in "dict" mode without complex post-processing. | Good, but verbose API. |
| **Layout Info** | **Excellent.** `extract_words()` gives precise font/bbox info. | Good, but `get_text("dict")` structure is deeply nested and harder to traverse linearly. | Verbose and slow. |
| **API Usability** | High. Built for scraping. | Medium. Built for rendering/low-level access. | Low. |

## Detailed Findings

### 1. `pdfplumber`
- **Accuracy:** The `extract_words()` method (which we tested) successfully captured font sizes allowing us to distinguish:
    - **Verses:** size ~9.5 (detected 211 blocks on pg 50)
    - **Footnotes:** size < 8.0 (detected 278 blocks on pg 50)
    - **Headers:** Y-position > 560
- **Coherence:** The reconstructed text flow was readable and matched the visual reading order (when sorted by Y/X).
- **Cons:** Slower than PyMuPDF, but still **2x faster** than the current implementation.

### 2. `PyMuPDF` (fitz)
- **Speed:** Blazing fast (0.2s/page).
- **Issues:** The raw "dict" output (needed for font info) often fragmented text oddly in our test (e.g., "G o d" vs "God"), leading to lower confidence in word-boundary reconstruction without writing a complex "reassembler". 
- **Verdict:** Great for thumbnails or simple text, but `pdfplumber` is safer for *data extraction*.

## Implementation Plan
1.  **Replace `pdfminer` with `pdfplumber`** in `vault_builder/adapters/sources/noab_pdf.py`.
2.  Use `pdfplumber`'s `extract_words(extra_attrs=["size"])` to replicate the current "font-size based classification" logic.
3.  This will improve maintainability and performance (50% reduction in time) without sacrificing the granular control we need for footnotes.

## Next Steps
- [ ] Refactor `NoabPdfSource` to import `pdfplumber`.
- [ ] Rewrite `_build_chapter_index` to use `pdfplumber` (should drop scan time from 10m to ~5m).
- [ ] Update `read_chapter` to use `pdfplumber` word extraction.
