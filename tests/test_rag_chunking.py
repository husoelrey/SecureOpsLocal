from src.rag.chunking import chunk_document, split_text_with_overlap

def test_split_text_with_overlap():
    text = "word " * 100
    chunks = split_text_with_overlap(text, max_words=60, overlap=10)
    # 100 words total.
    # chunk 1: 0 to 60 (60 words)
    # chunk 2: start at 60 - 10 = 50. 50 to 110 (50 words)
    assert len(chunks) == 2
    assert len(chunks[0].split()) == 60
    assert len(chunks[1].split()) == 50

def test_chunk_document_basic():
    content = """# Introduction
This is the intro section. It has some words.

# Details
Here are some details.
"""
    chunks = chunk_document(content, "doc_1", "Test Doc", max_words=100)
    # The first section (# Introduction) only has ~10 words, which is < 15 words.
    # Therefore, the chunker will buffer it and NOT split the section until it accumulates more than 15 words.
    # Wait, the threshold is > 15 words. Since neither section has > 15 words, they will be combined into a single section named "Details" (the last heading).
    assert len(chunks) == 1
    assert chunks[0].section_or_page == "Details"
    assert "intro section" in chunks[0].content
    assert "some details" in chunks[0].content

def test_chunk_document_large_sections():
    content = """# Section A
""" + "word " * 20 + """
# Section B
""" + "test " * 20
    
    chunks = chunk_document(content, "doc_2", "Test Large")
    
    # Section A has > 15 words, so it should trigger a flush when hitting `# Section B`.
    # Therefore, we should have 2 chunks.
    assert len(chunks) == 2
    assert chunks[0].section_or_page == "Section A"
    assert chunks[1].section_or_page == "Section B"
    assert chunks[0].word_count == 23 # "# Section A" (3) + 20 words = 23
    assert chunks[0].word_count > 10

def test_chunk_document_pdf_pages():
    content = """--- Page 1 ---
This is page one content.
""" + "page " * 20 + """
--- Page 2 ---
This is page two.
"""
    chunks = chunk_document(content, "doc_3", "PDF Doc")
    assert len(chunks) == 2
    assert chunks[0].section_or_page == "Page 1"
    assert chunks[1].section_or_page == "Page 2"
