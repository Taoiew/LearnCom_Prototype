from pathlib import Path

import fitz

from src.ingestion.pdf_ingestor import PDFIngestor


def create_two_page_pdf(pdf_path: Path) -> None:
    """
    Create a two-page PDF for testing.

    Page 1 contains an extractable text layer.
    Page 2 intentionally contains no text layer.
    """
    with fitz.open() as document:
        first_page = document.new_page()
        first_page.insert_text(
            (72, 72),
            "Introduction to Cloud Computing",
        )

        document.new_page()

        document.save(pdf_path)


def test_render_pages_creates_png_for_every_pdf_page(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"
    output_dir = tmp_path / "rendered"

    create_two_page_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=100)

    pages = ingestor.render_pages(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=output_dir,
    )

    assert len(pages) == 2

    first_page = pages[0]
    second_page = pages[1]

    assert first_page.material_id == "material-001"
    assert first_page.material_name == "lesson.pdf"
    assert first_page.page_number == 1
    assert first_page.extracted_text == (
        "Introduction to Cloud Computing"
    )

    assert second_page.material_id == "material-001"
    assert second_page.material_name == "lesson.pdf"
    assert second_page.page_number == 2
    assert second_page.extracted_text == ""

    assert first_page.rendered_image_path is not None
    assert second_page.rendered_image_path is not None

    first_image_path = Path(first_page.rendered_image_path)
    second_image_path = Path(second_page.rendered_image_path)

    assert first_image_path.exists()
    assert second_image_path.exists()

    assert first_image_path.is_file()
    assert second_image_path.is_file()

    assert first_image_path.name == "page-0001.png"
    assert second_image_path.name == "page-0002.png"

    assert first_image_path.parent.name == "material-001"
    assert second_image_path.parent.name == "material-001"

    assert first_image_path.stat().st_size > 0
    assert second_image_path.stat().st_size > 0

    assert first_image_path.read_bytes().startswith(b"\x89PNG")
    assert second_image_path.read_bytes().startswith(b"\x89PNG")


def test_render_pages_sanitizes_material_directory_name(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"
    output_dir = tmp_path / "rendered"

    create_two_page_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=100)

    pages = ingestor.render_pages(
        pdf_path=pdf_path,
        material_id="cloud/class 01",
        output_dir=output_dir,
    )

    first_image_path = Path(pages[0].rendered_image_path or "")

    assert first_image_path.parent.name == "cloud-class-01"
    assert first_image_path.exists()