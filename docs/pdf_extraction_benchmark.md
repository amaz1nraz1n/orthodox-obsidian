# PDF Extraction Benchmark Report

**Date:** March 24, 2026
**Subject:** Evaluation of PDF extraction libraries for NOAB RSV source.

## Executive Summary
We benchmarked 4 libraries on the NOAB RSV PDF to identify a more efficient alternative to the current `pdfminer.six` implementation.

**Winner:** **PyMuPDF (fitz)**
- **Speed:** ~40x faster than current implementation (0.04s vs 1.47s per page).
- **Quality:** Correctly identifies column reading order by default.
- **Capability:** Provides rich metadata (bounding boxes, font sizes) for filtering headers/footers.

## Benchmark Results (Sample Pages 50 & 1500)

| Library | Avg Time/Page | Status | Notes |
| :--- | :--- | :--- | :--- |
| **PyMuPDF (fitz)** | **0.036s** | ✅ Excellent | Blazing fast. Text extracted in correct column order. Captures headers inline (easy to filter by bbox). |
| **pdfplumber** | 0.82s | ⚠️ Good | Slower. Default `extract_text()` merges columns (requires `layout=True` or manual cropping). |
| **pymupdf4llm** | 1.01s | ❌ Failed | Returned empty/image placeholders for sample pages. Likely confused by PDF structure. |
| **pdfminer.six** | 1.47s | 🐢 Slow | Current baseline. Slowest. Raw text extraction is messy without custom logic. |

## Detailed Analysis

### 1. Current Implementation (`pdfminer.six`)
- **Pros:** Precise low-level control (currently used for detailed font-size logic).
- **Cons:** Extremely slow. Full PDF scan takes ~10-15 minutes.
- **Verdict:** The primary bottleneck for development iteration.

### 2. PyMuPDF (`fitz`)
- **Pros:**
  - **Speed:** Can scan the entire 2032-page PDF in **~1.5 minutes** (vs 10+ mins).
  - **Structure:** `page.get_text("blocks")` returns text with bounding boxes, allowing us to easily replicate the current logic (filtering headers by Y-coordinate, detecting footnotes by font size) but much faster.
- **Cons:** Requires rewriting the adapter to use `fitz` API instead of `pdfminer`.

### 3. pdfplumber
- **Pros:** Built on `pdfminer` but with a friendlier API. Great visual debugging.
- **Cons:** Still bound by `pdfminer`'s speed. Merging columns by default requires configuration overhead.

### 4. pymupdf4llm
- **Pros:** targeted at Markdown generation.
- **Cons:** Failed to extract text from NOAB samples (likely due to layout complexity or image detection false positives).

## Recommendation
**Migrate `NoabPdfSource` to use `PyMuPDF` (fitz).**
This will reduce the "chapter index build" time from **10 minutes to < 2 minutes**, significantly accelerating the auditing and extraction workflow.
