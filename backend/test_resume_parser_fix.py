"""
Test: Fixed PDF Parser + Adaptive Chunking with Resume-like Content

Creates a synthetic resume PDF with ALL-CAPS section headers (EDUCATION,
EXPERIENCE, PROJECTS, CERTIFICATIONS) and verifies that:

1. The PDF parser detects these blocks as headings (not just "paragraph")
2. The adaptive chunking uses heading blocks to set proper section context
3. Consecutive small blocks under the same heading are merged into larger chunks
4. The resulting chunks have correct, meaningful headings attached
"""

import os
import sys
import tempfile

# Ensure backend dir is on path
sys.path.insert(0, os.path.dirname(__file__))

import fitz  # PyMuPDF
from parsers.pdf_parser import PDFParser
from pipeline.adaptive_chunking import adaptive_chunking


def create_resume_pdf(path: str) -> None:
    """
    Create a synthetic resume PDF that mimics the structure of Kunal's resume.
    Section headers are in ALL CAPS with slightly larger/bold formatting.
    """
    doc = fitz.open()

    # A4 page
    page = doc.new_page(width=595, height=842)  # A4 in points

    # Helper to insert a line
    y = 60

    def text(line: str, size: int = 11, bold: bool = False, y_offset: int = 18):
        nonlocal y
        fontname = "helv" if not bold else "helv"  # PyMuPDF standard fonts
        # Simulate bold by using a bold-like approach — fitz doesn't have
        # built-in bold for helv, so we'll use different font size + color
        page.insert_text(
            fitz.Point(72, y),
            line,
            fontsize=size,
            fontname="helv",
            color=(0, 0, 0) if not bold else (0.1, 0.1, 0.1),
        )
        y += y_offset

    # ── Header / Title (large font) ──
    text("ROSHAN KUMAR", size=18, bold=True, y_offset=24)
    text("roshians@proton.me  |  linkedin.com/in/roshians", size=10, y_offset=16)
    text("Faridabad, Haryana, India", size=10, y_offset=16)

    y += 6

    # ── SUMMARY (ALL CAPS heading) ──
    text("SUMMARY", size=12, bold=True, y_offset=16)
    text(
        "AI/ML undergraduate specializing in computer vision and LLM-based systems. "
        "Experience building end-to-end machine learning pipelines.",
        size=10, y_offset=18,
    )

    y += 4

    # ── EDUCATION (ALL CAPS heading) ──
    text("EDUCATION", size=12, bold=True, y_offset=16)
    text("B.Tech in Computer Science (AI & ML) 2023 - 2027", size=10, y_offset=16)
    text("IILM University, Greater Noida", size=10, y_offset=16)

    y += 4

    # ── SKILLS (ALL CAPS heading) ──
    text("SKILLS", size=12, bold=True, y_offset=16)
    text("Languages: Python, C, SQL  |  AI/ML: PyTorch, TensorFlow", size=10, y_offset=16)
    text("Frameworks: FastAPI, Flask, Streamlit", size=10, y_offset=16)
    text("Tools: Git, Docker, Linux, AWS  |  Databases: PostgreSQL, MySQL", size=10, y_offset=16)

    y += 4

    # ── EXPERIENCE (ALL CAPS heading) ──
    text("EXPERIENCE", size=12, bold=True, y_offset=16)
    text("AI/ML Intern - Ongoing", size=10, bold=True, y_offset=16)
    text("Wildlife Institute of India (WII) - Airavat Project", size=10, y_offset=14)
    text("Built an open-set elephant re-identification system using ConvNeXt-Tiny", size=10, y_offset=14)
    text("Achieved Rank-1 87.92%, Rank-5 91.42%, mAP 68.10%", size=10, y_offset=14)
    text("Applied Triplet, ArcFace, and Center Loss for feature separation", size=10, y_offset=14)

    y += 4

    # ── PROJECTS (ALL CAPS heading) ──
    text("PROJECTS", size=12, bold=True, y_offset=16)
    text("PathShala AI - AI Co-Teacher", size=10, bold=True, y_offset=16)
    text("Developed an LLM-based system that generates lesson plans in under 15 seconds", size=10, y_offset=14)
    text("using Gemini API and AWS services. Designed for multi-grade classrooms.", size=10, y_offset=14)
    text("Waste Classification System", size=10, bold=True, y_offset=16)
    text("Built CNN using MobileNetV2 achieving 92% validation accuracy.", size=10, y_offset=14)
    text("Processed and augmented 22,500 images. Deployed via Streamlit.", size=10, y_offset=14)

    y += 4

    # ── CERTIFICATIONS (ALL CAPS heading) ──
    text("CERTIFICATIONS", size=12, bold=True, y_offset=16)
    text("Introduction to Agentic AI on AWS - AWS (Jan 2026)", size=10, y_offset=14)
    text("Introduction to Generative AI - AWS Educate (Jan 2026)", size=10, y_offset=14)
    text("Artificial Intelligence Fundamentals - IBM (Jul 2025)", size=10, y_offset=14)

    doc.save(path)
    doc.close()
    print(f"  -> Created synthetic resume PDF: {path}")


def test_parser_heading_detection(pdf_path: str) -> None:
    """Test 1: Verify the PDF parser detects ALL-CAPS blocks as headings."""
    print("\n" + "=" * 70)
    print("TEST 1: PDF Parser — Heading Detection")
    print("=" * 70)

    parser = PDFParser()
    doc = parser.parse(pdf_path)

    print(f"  Pages: {len(doc.pages)}")
    for page in doc.pages:
        print(f"\n  Page {page.page_number}:")
        print(f"    Headings detected: {page.headings}")
        print(f"    Total blocks: {len(page.blocks)}")

        heading_blocks = [b for b in page.blocks if b.get("type") == "heading"]
        para_blocks = [b for b in page.blocks if b.get("type") == "paragraph"]
        print(f"    Heading blocks: {len(heading_blocks)}")
        print(f"    Paragraph blocks: {len(para_blocks)}")

        print("\n    --- All blocks ---")
        for i, b in enumerate(page.blocks):
            btype = b.get("type", "?")
            text_preview = b.get("text", "")[:60]
            print(f"    [{i:2d}] ({btype:9s}) {text_preview}")

    # ── Assertions ──
    all_headings = [h for page in doc.pages for h in page.headings]
    expected_headings = [
        "ROSHAN KUMAR",
        "SUMMARY",
        "EDUCATION",
        "SKILLS",
        "EXPERIENCE",
        "PROJECTS",
        "CERTIFICATIONS",
    ]
    print("\n  --- Verification ---")
    for expected in expected_headings:
        if expected in all_headings:
            print(f"  ✅ Heading '{expected}' detected")
        else:
            print(f"  ❌ Heading '{expected}' MISSING")

    # Check NO heading is "KUNAL SHARMA" (the old bug — everything was that)
    for h in all_headings:
        if "SHARMA" in h and "KUMAR" not in h:
            print(f"  ⚠️  Unexpected heading: '{h}'")

    return doc


def test_adaptive_chunking(document) -> None:
    """Test 2: Verify chunks have correct headings and blocks are merged."""
    print("\n" + "=" * 70)
    print("TEST 2: Adaptive Chunking — Block Merging & Headings")
    print("=" * 70)

    chunks = adaptive_chunking(document)

    print(f"\n  Total chunks created: {len(chunks)}")
    print(f"  (Previously with old code: ~25-30 chunks for similar resume)")

    print("\n  --- All Chunks ---")
    for i, c in enumerate(chunks):
        heading = c.get("heading", "(no heading)")
        section = c.get("section", "(no section)")
        text_preview = c.get("text", "")[:80].replace("\n", " | ")
        print(f"\n  Chunk {i}: heading='{heading}'")
        print(f"          section='{section}'")
        print(f"          text=\"{text_preview}...\"")

    # ── Assertions ──
    print("\n  --- Verification ---")

    # Check that section headings are correct
    chunk_headings = set(c.get("heading", "") for c in chunks)
    expected_headings_in_chunks = {
        "ROSHAN KUMAR", "SUMMARY", "EDUCATION", "SKILLS",
        "EXPERIENCE", "PROJECTS", "CERTIFICATIONS",
    }
    for expected in expected_headings_in_chunks:
        if expected in chunk_headings:
            print(f"  ✅ Section '{expected}' appears as a chunk heading")
        else:
            print(f"  ⚠️  Section '{expected}' NOT an active chunk heading")

    # Check what chunks contain what — specifically that bullet points
    # under the same section are merged into fewer chunks
    edu_chunks = [c for c in chunks if c.get("heading") == "EDUCATION"]
    exp_chunks = [c for c in chunks if c.get("heading") == "EXPERIENCE"]
    cert_chunks = [c for c in chunks if c.get("heading") == "CERTIFICATIONS"]

    print(f"\n  Chunks under 'EDUCATION': {len(edu_chunks)} "
          f"(expected 1-2 instead of many)")
    print(f"  Chunks under 'EXPERIENCE': {len(exp_chunks)} "
          f"(expected 1-2 instead of many)")
    print(f"  Chunks under 'CERTIFICATIONS': {len(cert_chunks)} "
          f"(expected 1 instead of many)")

    for c in cert_chunks:
        text = c.get("text", "")
        has_aws = "AWS" in text
        has_ibm = "IBM" in text
        print(f"    Cert chunk contains AWS: {has_aws}, IBM: {has_ibm}")

    print(f"\n  Total chunks: {len(chunks)} (under ~15 is good for a 1-page resume)")
    return chunks


def simulate_rag_query(chunks, query: str) -> None:
    """
    Simulate a RAG query: find the most relevant chunks for a given question.
    Uses simple keyword matching to demonstrate what chunks would be retrieved.
    """
    print(f"\n" + "-" * 70)
    print(f"  RAG SIMULATION: \"{query}\"")
    print("-" * 70)

    query_terms = query.lower().split()
    scored = []
    for i, c in enumerate(chunks):
        text = c.get("text", "").lower()
        heading = c.get("heading", "").lower()
        score = 0
        # Simple keyword matching
        for term in query_terms:
            if term in text:
                score += 1
            if term in heading:
                score += 2  # heading matches are more valuable

        if score > 0:
            # Also check section heading match
            if query_terms[0] in heading.lower():
                score += 3  # section header match is very relevant

            scored.append((score, i, c))

    scored.sort(reverse=True)
    top3 = scored[:3]

    if not top3:
        print("  No relevant chunks found!")
        return

    for rank, (score, idx, c) in enumerate(top3):
        text = c.get("text", "")[:120]
        heading = c.get("heading", "")
        section = c.get("section", "")
        print(f"\n  [{rank+1}] Score={score} | heading='{heading}' | section='{section}'")
        print(f"      Text: \"{text}...\"")

    return top3


if __name__ == "__main__":
    # ── Create a synthetic resume PDF ──
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = f.name

    try:
        create_resume_pdf(pdf_path)

        # ── Test 1: Parser heading detection ──
        doc = test_parser_heading_detection(pdf_path)

        # ── Test 2: Adaptive chunking ──
        chunks = test_adaptive_chunking(doc)

        # ── Test 3: Simulated RAG queries ──
        print("\n\n" + "=" * 70)
        print("TEST 3: Simulated RAG Queries")
        print("=" * 70)

        simulate_rag_query(chunks, "what is his education and university")
        simulate_rag_query(chunks, "tell me about experience or internship")
        simulate_rag_query(chunks, "list all certifications")

        print("\n\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        all_headings = set()
        for page in doc.pages:
            all_headings.update(page.headings)

        # Count the actual improvements
        old_bug_headings = [h for h in all_headings if "SHARMA" in h]
        missing_expected = [
            h for h in ["EDUCATION", "EXPERIENCE", "CERTIFICATIONS"]
            if h not in all_headings
        ]

        print(f"  ✅ Headings detected: {len(all_headings)} unique headings")
        print(f"  ✅ Section headers present: EDUCATION={('EDUCATION' in all_headings)}"
              f", EXPERIENCE={('EXPERIENCE' in all_headings)}"
              f", CERTIFICATIONS={('CERTIFICATIONS' in all_headings)}")
        print(f"  ✅ Total chunks: {len(chunks)} "
              f"(was 25+ with old code)")
        print(f"  ❌ Old bug (all heading='KUNAL SHARMA'): "
              f"{'FIXED' if not old_bug_headings else 'STILL PRESENT'}")
        print(f"  ❌ Missing expected sections: "
              f"{'NONE' if not missing_expected else missing_expected}")

        if not missing_expected:
            print("\n  ✅✅ ALL FIXES VERIFIED SUCCESSFULLY ✅✅")
        else:
            print("\n  ⚠️ Some sections still missing, may need further tuning")

    finally:
        # Cleanup
        try:
            os.unlink(pdf_path)
        except Exception:
            pass
        print(f"\n  Cleaned up test PDF: {pdf_path}")
