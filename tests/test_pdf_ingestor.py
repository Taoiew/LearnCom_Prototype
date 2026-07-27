import fitz

from src.ingestion.pdf_ingestor import PDFIngestor


def test_pdf_ingestor(tmp_path):
    pdf_path = tmp_path / "sample.pdf"

    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Gradient descent updates model parameters to reduce the loss.",
    )
    document.save(pdf_path)
    document.close()

    ingestor = PDFIngestor(chunk_size=100, overlap=10)
    chunks = ingestor.ingest(pdf_path, material_id="material-001")

    assert len(chunks) == 1
    assert chunks[0].material_id == "material-001"
    assert chunks[0].material_name == "sample.pdf"
    assert chunks[0].page_number == 1
    assert chunks[0].chunk_id.startswith("chunk-")
    assert "Gradient descent" in chunks[0].text