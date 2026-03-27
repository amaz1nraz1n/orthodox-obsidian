import time
import pdfplumber
import fitz  # PyMuPDF
import pymupdf4llm
from pdfminer.high_level import extract_text
from pathlib import Path

PDF_PATH = "./source_files/Full Bible/New Oxford Annotated Bible with Apocrypha RSV.pdf"
OUTPUT_DIR = Path("output/benchmarks")
PAGES_TO_TEST = [50, 1500] 

def benchmark_pdfplumber(pdf_path, page_indices):
    start = time.time()
    results = {}
    with pdfplumber.open(pdf_path) as pdf:
        for idx in page_indices:
            try:
                page = pdf.pages[idx]
                text = page.extract_text()
                results[idx] = text
            except IndexError:
                print(f"  pdfplumber: Page {idx} out of range")
    duration = time.time() - start
    return results, duration

def benchmark_pymupdf(pdf_path, page_indices):
    start = time.time()
    results = {}
    doc = fitz.open(pdf_path)
    for idx in page_indices:
        try:
            page = doc.load_page(idx)
            text = page.get_text() # Default is plain text
            results[idx] = text
        except Exception as e:
            print(f"  pymupdf: Error on page {idx}: {e}")
    duration = time.time() - start
    return results, duration

def benchmark_pymupdf4llm(pdf_path, page_indices):
    start = time.time()
    results = {}
    for idx in page_indices:
        try:
            # pymupdf4llm.to_markdown(doc=..., pages=[...]) is also possible if we open doc first?
            # looking at docs, it takes "doc" or "filename". 
            # Using filename is safer for simple usage.
            md = pymupdf4llm.to_markdown(pdf_path, pages=[idx])
            results[idx] = md
        except Exception as e:
            print(f"  pymupdf4llm: Error on page {idx}: {e}")
    duration = time.time() - start
    return results, duration

def benchmark_pdfminer(pdf_path, page_indices):
    start = time.time()
    results = {}
    for idx in page_indices:
        try:
            # page_numbers is 0-indexed in pdfminer.high_level?
            # It expects a container (list/set).
            text = extract_text(pdf_path, page_numbers=[idx])
            results[idx] = text
        except Exception as e:
            print(f"  pdfminer: Error on page {idx}: {e}")
    duration = time.time() - start
    return results, duration

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Benchmarking PDF extraction on {PDF_PATH}")
    print(f"Pages: {PAGES_TO_TEST}")
    
    tasks = [
        ("pdfplumber", benchmark_pdfplumber),
        ("pymupdf", benchmark_pymupdf),
        ("pymupdf4llm", benchmark_pymupdf4llm),
        ("pdfminer", benchmark_pdfminer),
    ]
    
    for name, func in tasks:
        print(f"Running {name}...")
        try:
            results, duration = func(PDF_PATH, PAGES_TO_TEST)
            print(f"  Duration: {duration:.4f}s")
            for idx, content in results.items():
                out_file = OUTPUT_DIR / f"{name}_page_{idx}.md"
                wrapped_content = f"# {name} - Page {idx}\n\nTime taken: {duration:.4f}s (total for batch)\n\n---\n\n{content}"
                out_file.write_text(wrapped_content, encoding="utf-8")
        except Exception as e:
            print(f"  Failed: {e}")

if __name__ == "__main__":
    main()
