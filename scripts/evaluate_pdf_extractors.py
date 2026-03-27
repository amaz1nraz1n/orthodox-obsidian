import time
import json
import pdfplumber
import fitz  # PyMuPDF
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

# Constants based on NoabPdfSource logic
PDF_PATH = "./source_files/Full Bible/New Oxford Annotated Bible with Apocrypha RSV.pdf"
OUTPUT_DIR = Path("output/benchmarks")
PAGES_TO_TEST = [50, 1500] 

# Classification thresholds (from current adapter)
HEADER_Y_MIN = 560
HEADER_FONT_MIN = 8.0
HEADER_FONT_MAX = 10.5
PAGE_NUM_MIN = 10.0
SUPERSCRIPT_MAX = 6.0
FOOTNOTE_MAX = 8.0
PERICOPE_MAX = 8.7
PERICOPE_LEN_MAX = 70

@dataclass
class TextBlock:
    text: str
    x: float
    y_top: float # Top of the box (from bottom-left origin usually, but pdfminer/fitz differ)
    y_bot: float
    font_size: float
    classification: str = "unknown"

    def to_dict(self):
        return asdict(self)

def classify_block(text: str, size: float, y_top: float, width: float) -> str:
    """Classify a text block based on NOAB structural rules."""
    text = text.strip()
    if not text:
        return "empty"
    
    # Note: coordinate systems differ. 
    # pdfminer: (0,0) is bottom-left. y_top is high.
    # fitz: (0,0) is top-left usually, but we can request different boxes.
    # We will normalize to PDF logic (0,0 bottom-left) for comparison if possible,
    # or adjust thresholds per library. 
    # For now, let's assume we pass in "PDF coordinate" y_top.
    
    if size > PAGE_NUM_MIN:
        return "page_num"
    if size < SUPERSCRIPT_MAX:
        return "superscript"
    if size < FOOTNOTE_MAX:
        return "footnote"
    
    # Header check (y > 560 in PDF coords)
    if y_top > HEADER_Y_MIN:
         # Simplified header check
        return "header"

    if size < PERICOPE_MAX and len(text) < PERICOPE_LEN_MAX:
        return "pericope"
        
    return "verse"


def evaluate_pdfplumber(pdf_path, page_indices) -> Dict[int, List[TextBlock]]:
    """
    Extract structured blocks using pdfplumber.
    pdfplumber returns bbox=(x0, top, x1, bottom) where (0,0) is top-left.
    We need to invert Y to match pdfminer/NOAB logic (0,0 is bottom-left).
    """
    results = {}
    with pdfplumber.open(pdf_path) as pdf:
        for idx in page_indices:
            try:
                page = pdf.pages[idx]
                height = page.height
                blocks = []
                
                # extracting "words" gives the most detailed font info
                words = page.extract_words(keep_blank_chars=True, extra_attrs=["size"])
                
                # Grouping words into crude lines/blocks is hard without logic.
                # But let's just dump the words to see if we CAN get the data.
                # For a fair comparison, we want "text boxes" like pdfminer.
                # pdfplumber doesn't give font size for a whole "extract_text" block easily.
                # We'll approximate by averaging word sizes in a line.
                
                # Actually, let's just return the raw words as "tiny blocks" 
                # to prove we have the granularity.
                for w in words:
                    # Invert Y: pdfplumber top=0 -> pdfminer top=height
                    # y_top in pdfminer is distance from bottom.
                    # w['top'] is distance from top.
                    # so y_top_pdf = height - w['top']
                    y_top_pdf = height - w['top']
                    y_bot_pdf = height - w['bottom']
                    
                    sz = float(w['size'])
                    cls = classify_block(w['text'], sz, y_top_pdf, page.width)
                    
                    blocks.append(TextBlock(
                        text=w['text'],
                        x=float(w['x0']),
                        y_top=y_top_pdf,
                        y_bot=y_bot_pdf,
                        font_size=sz,
                        classification=cls
                    ))
                results[idx] = blocks
            except Exception as e:
                print(f"pdfplumber error on {idx}: {e}")
    return results

def evaluate_pymupdf(pdf_path, page_indices) -> Dict[int, List[TextBlock]]:
    """
    Extract structured blocks using PyMuPDF (fitz).
    fitz text dict: "blocks" -> "lines" -> "spans".
    Spans have font size and text.
    """
    results = {}
    doc = fitz.open(pdf_path)
    for idx in page_indices:
        try:
            page = doc.load_page(idx)
            height = page.rect.height
            blocks_out = []
            
            # Get text blocks
            raw_blocks = page.get_text("dict")["blocks"]
            
            for b in raw_blocks:
                if "lines" not in b: 
                    continue # likely an image block
                    
                for line in b["lines"]:
                    for span in line["spans"]:
                        # fitz bbox: (x0, y0, x1, y1) top-left origin
                        # y0 is top edge. 
                        # pdfminer y_top is distance from bottom.
                        # so y_top_pdf = height - y0
                        y_top_pdf = height - span["bbox"][1]
                        y_bot_pdf = height - span["bbox"][3]
                        
                        sz = span["size"]
                        txt = span["text"]
                        
                        cls = classify_block(txt, sz, y_top_pdf, page.rect.width)
                        
                        blocks_out.append(TextBlock(
                            text=txt,
                            x=span["bbox"][0],
                            y_top=y_top_pdf,
                            y_bot=y_bot_pdf,
                            font_size=sz,
                            classification=cls
                        ))
            results[idx] = blocks_out
        except Exception as e:
            print(f"pymupdf error on {idx}: {e}")
    return results

def format_report(library_name: str, data: Dict[int, List[TextBlock]], duration: float):
    lines = [f"# Evaluation Report: {library_name}"]
    lines.append(f"**Total Duration:** {duration:.4f}s\n")
    
    for page_idx, blocks in data.items():
        lines.append(f"## Page {page_idx}")
        counts = {}
        for b in blocks:
            counts[b.classification] = counts.get(b.classification, 0) + 1
        
        lines.append(f"**Detected Entities:** {counts}")
        lines.append("\n### Sample Verses (font 9.0-9.7)")
        verses = [b.text for b in blocks if b.classification == "verse"]
        lines.append(" ".join(verses[:50]) + "...") # First 50 words/blocks
        
        lines.append("\n### Sample Footnotes (font < 8.0)")
        footnotes = [b.text for b in blocks if b.classification == "footnote"]
        lines.append(" ".join(footnotes[:50]) + "...")
        
        lines.append("\n### Sample Headers (y > 560)")
        headers = [b.text for b in blocks if b.classification == "header"]
        lines.append(" | ".join(headers))

        lines.append("\n---\n")
        
    return "\n".join(lines)

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Evaluating Extractors on {PDF_PATH}...")
    
    # 1. Evaluate pdfplumber
    start = time.time()
    plumber_data = evaluate_pdfplumber(PDF_PATH, PAGES_TO_TEST)
    plumber_dur = time.time() - start
    
    (OUTPUT_DIR / "eval_pdfplumber.md").write_text(
        format_report("pdfplumber", plumber_data, plumber_dur), encoding="utf-8"
    )
    print(f"pdfplumber finished in {plumber_dur:.4f}s")

    # 2. Evaluate PyMuPDF
    start = time.time()
    pymupdf_data = evaluate_pymupdf(PDF_PATH, PAGES_TO_TEST)
    pymupdf_dur = time.time() - start
    
    (OUTPUT_DIR / "eval_pymupdf.md").write_text(
        format_report("PyMuPDF", pymupdf_data, pymupdf_dur), encoding="utf-8"
    )
    print(f"PyMuPDF finished in {pymupdf_dur:.4f}s")

    # JSON dump for deep inspection if needed
    with open(OUTPUT_DIR / "eval_data.json", "w") as f:
        json.dump({
            "pdfplumber": {k: [b.to_dict() for b in v] for k, v in plumber_data.items()},
            "pymupdf": {k: [b.to_dict() for b in v] for k, v in pymupdf_data.items()}
        }, f, indent=2)

if __name__ == "__main__":
    main()
