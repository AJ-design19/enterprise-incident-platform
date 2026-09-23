from ingestion.pdf_loader import load_sop_directory


def test_load_sop_directory_finds_markdown_files(sample_sops_dir):
    docs = load_sop_directory(sample_sops_dir)
    assert len(docs) > 0
    assert all(d.doc_type in ("md", "pdf", "docx", "txt") for d in docs)


def test_load_sop_directory_missing_dir_returns_empty(tmp_path):
    docs = load_sop_directory(tmp_path / "does_not_exist")
    assert docs == []


def test_sop_chunks_have_source_metadata(sample_sops_dir):
    docs = load_sop_directory(sample_sops_dir)
    for doc in docs:
        assert doc.source
        assert "source_path" in doc.metadata
        assert "chunk_index" in doc.metadata


def test_chunking_respects_size_bounds(sample_sops_dir):
    docs = load_sop_directory(sample_sops_dir, chunk_size=300, chunk_overlap=50)
    # Allow some slack since the splitter breaks on natural boundaries
    assert all(len(d.content) <= 400 for d in docs)
