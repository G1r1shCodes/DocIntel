"""
Minimal standalone test for the heading detection fix.

Creates a resume PDF with ALL-CAPS section headers and tests that
the heading classification logic correctly identifies them.

Uses only fitz directly -- no backend imports needed.
"""
import os
import tempfile
import fitz  # PyMuPDF

# Copy of the heading classification logic from pdf_parser.py
HEADING_FONT_SIZE = 11.0
HEADING_ALL_CAPS_MAX_LEN = 60


def classify_heading_block(block: dict, spans: list[dict]) -> bool:
    """Mirrors PDFParser._classify_heading_block."""
    full_text = " ".join(s.get("text", "") for s in spans).strip()
    if not full_text:
        return False

    max_font_size = max((s.get("size", 0) for s in spans), default=0)

    # Criterion 1: Large font
    if max_font_size > HEADING_FONT_SIZE:
        return True

    # Criterion 2: ALL CAPS and short (resume section headers)
    alpha_stripped = full_text.replace(" ", "")
    if (
        alpha_stripped.isupper()
        and len(alpha_stripped) > 2
        and len(full_text) <= HEADING_ALL_CAPS_MAX_LEN
    ):
        return True

    # Criterion 3: Fully bold block and short (<= 5 words)
    bold_flags = [s.get("flags", 0) & 16 for s in spans]
    if bold_flags and all(bold_flags) and len(full_text.split()) <= 5:
        return True

    return False


def create_resume_pdf(path: str) -> None:
    """Create a synthetic resume PDF with ALL-CAPS section headers."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4

    y = 60
    margin = 72

    def insert(line: str, size: int = 11, y_off: int = 18):
        nonlocal y
        page.insert_text(fitz.Point(margin, y), line, fontsize=size, fontname="helv")
        y += y_off

    # Header (large font)
    insert("ROSHAN KUMAR", size=18, y_off=24)
    insert("roshians@proton.me  |  Faridabad, India", size=10, y_off=16)
    y += 6

    # ALL-CAPS section headers (these should be detected as headings)
    insert("SUMMARY", size=11)
    insert("AI/ML undergraduate specializing in computer vision and LLMs.", size=10)
    y += 2
    insert("EDUCATION", size=11)
    insert("B.Tech in Computer Science (AI & ML) 2023 - 2027", size=10)
    insert("IILM University, Greater Noida", size=10)
    y += 2
    insert("EXPERIENCE", size=11)
    insert("AI/ML Intern - Wildlife Institute of India (WII)", size=10)
    insert("Built an open-set elephant re-identification system.", size=10)
    insert("Achieved Rank-1 87.92%, Rank-5 91.42%.", size=10)
    y += 2
    insert("PROJECTS", size=11)
    insert("PathShala AI - LLM lesson plan generator using Gemini API", size=10)
    insert("Waste Classification - CNN with 92% accuracy", size=10)
    y += 2
    insert("CERTIFICATIONS", size=11)
    insert("Introduction to Agentic AI on AWS - AWS Jan 2026", size=10)
    insert("Introduction to Generative AI - AWS Educate Jan 2026", size=10)
    insert("Artificial Intelligence Fundamentals - IBM Jul 2025", size=10)

    doc.save(path)
    doc.close()
    print("  + Created resume PDF: {}".format(path))


def extract_and_classify(pdf_path: str) -> dict:
    """Extract blocks and classify them using the heading logic."""
    doc = fitz.open(pdf_path)
    page = doc[0]
    text_dict = page.get_text("dict")

    print("\n  Page size: {:.0f} x {:.0f}".format(page.rect.width, page.rect.height))

    results = {"headings": [], "paragraphs": [], "blocks": []}

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:  # text blocks only
            continue

        all_spans = []
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                all_spans.append(span)

        full_text = " ".join(s.get("text", "") for s in all_spans).strip()
        if not full_text:
            continue

        is_heading = classify_heading_block(block, all_spans)
        btype = "heading" if is_heading else "paragraph"
        results["blocks"].append((btype, full_text, all_spans))
        if is_heading:
            results["headings"].append(full_text)
        else:
            results["paragraphs"].append(full_text)

    # Print results
    print("\n  " + "=" * 60)
    print("  BLOCK CLASSIFICATION RESULTS")
    print("  " + "=" * 60)
    for i, (btype, text, spans) in enumerate(results["blocks"]):
        sizes = [s.get("size", 0) for s in spans]
        flags = [s.get("flags", 0) for s in spans]
        max_font = max(sizes)
        all_bold = all(f & 16 for f in flags)
        icon = "[H]" if btype == "heading" else "[P]"
        print("\n  {} [{:2d}] type={:9s} | font={:.1f}pt | bold={}".format(
            icon, i, btype, max_font, all_bold))
        print("        text: {}".format(text[:70]))

    print("\n  " + "=" * 60)
    print("  SUMMARY")
    print("  " + "=" * 60)
    print("  Total blocks: {}".format(len(results["blocks"])))
    print("  Heading blocks: {}".format(len(results["headings"])))
    print("  Paragraph blocks: {}".format(len(results["paragraphs"])))
    print("  Headings found: {}".format(results["headings"]))

    # Verification
    print("\n  " + "=" * 60)
    print("  VERIFICATION")
    print("  " + "=" * 60)

    expected_sections = ["SUMMARY", "EDUCATION", "EXPERIENCE", "PROJECTS", "CERTIFICATIONS"]
    all_pass = True
    for section in expected_sections:
        if section in results["headings"]:
            print("  [PASS] '{}' correctly classified as heading".format(section))
        else:
            print("  [FAIL] '{}' NOT classified as heading!".format(section))
            all_pass = False

    # Check that content lines are NOT classified as headings
    content_lines = [
        "IILM University, Greater Noida",
        "AI/ML Intern - Wildlife Institute of India",
    ]
    for line in content_lines:
        in_para = any(line in p for p in results["paragraphs"])
        in_head = any(line in h for h in results["headings"])
        if in_para:
            print("  [PASS] Content line correctly NOT a heading")
        elif in_head:
            print("  [FAIL] Content line WRONGLY classified as heading!")
            all_pass = False

    doc.close()
    results["all_pass"] = all_pass
    return results


def run_comparison(results: dict) -> None:
    """Compare old heuristic (font > 13) with new one."""
    print("\n\n  " + "=" * 60)
    print("  COMPARISON: OLD heuristic vs NEW heuristic")
    print("  " + "=" * 60)
    print("  OLD: font_size > 13 -> only 'ROSHAN KUMAR' (18pt) would be a heading")
    print("       All others -> 'paragraph' -> chunks get heading='ROSHAN KUMAR'")
    print("  NEW: ALL-CAPS detection catches SUMMARY, EDUCATION, EXPERIENCE, etc.")
    print("       -> chunks get correct section headings!")

    old_detected = []
    for h in results["headings"]:
        for _, block_text, spans in results["blocks"]:
            if h in block_text and max(s.get("size", 0) for s in spans) > 13:
                old_detected.append(h)
                break

    print("  OLD would detect as headings: {}".format(old_detected))
    print("  NEW detects as headings: {}".format(results["headings"]))

    newly_detected = set(results["headings"]) - set(old_detected)
    if newly_detected:
        print("  [NEW] Detected by ALL-CAPS heuristic: {}".format(list(newly_detected)))


if __name__ == "__main__":
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = f.name

    try:
        create_resume_pdf(pdf_path)
        results = extract_and_classify(pdf_path)
        run_comparison(results)

        if results["all_pass"]:
            print("\n  *** ALL CHECKS PASSED ***")
        else:
            print("\n  *** SOME CHECKS FAILED ***")
    finally:
        try:
            os.unlink(pdf_path)
        except Exception:
            pass
        print("\n  Cleaned up: {}".format(pdf_path))
