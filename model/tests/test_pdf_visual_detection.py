import base64
from pathlib import Path

import fitz

from src.ingestion.pdf_ingestor import PDFIngestor


ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwC"
    "AAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def create_visual_detection_pdf(pdf_path: Path) -> None:
    """
    Create a three-page PDF:

    Page 1: text only
    Page 2: text and vector diagram
    Page 3: full-page raster image, similar to a scanned page
    """
    with fitz.open() as document:
        text_page = document.new_page()
        text_page.insert_text(
            (72, 72),
            "This page contains only a text layer.",
        )

        diagram_page = document.new_page()
        diagram_page.insert_text(
            (72, 72),
            "Learning pipeline",
        )
        diagram_page.draw_rect(
            fitz.Rect(72, 100, 220, 160),
            color=(0, 0, 0),
            width=1,
        )
        diagram_page.draw_line(
            fitz.Point(220, 130),
            fitz.Point(320, 130),
            color=(0, 0, 0),
            width=1,
        )
        diagram_page.draw_rect(
            fitz.Rect(320, 100, 468, 160),
            color=(0, 0, 0),
            width=1,
        )

        scanned_page = document.new_page()
        scanned_page.insert_image(
            scanned_page.rect,
            stream=ONE_PIXEL_PNG,
        )

        document.save(pdf_path)


def render_detection_pages(tmp_path: Path):
    pdf_path = tmp_path / "visual-detection.pdf"
    output_dir = tmp_path / "rendered"

    create_visual_detection_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)

    return ingestor.render_pages(
        pdf_path=pdf_path,
        material_id="visual-test",
        output_dir=output_dir,
    )


def test_text_only_page_does_not_require_vision(
    tmp_path: Path,
) -> None:
    pages = render_detection_pages(tmp_path)
    text_page = pages[0]

    assert text_page.page_number == 1
    assert text_page.extracted_text != ""
    assert text_page.has_visual_content is False
    assert text_page.requires_vision is False


def test_vector_diagram_page_requires_vision(
    tmp_path: Path,
) -> None:
    pages = render_detection_pages(tmp_path)
    diagram_page = pages[1]

    assert diagram_page.page_number == 2
    assert diagram_page.extracted_text == "Learning pipeline"
    assert diagram_page.has_visual_content is True
    assert diagram_page.requires_vision is True


def test_scanned_image_page_requires_vision(
    tmp_path: Path,
) -> None:
    pages = render_detection_pages(tmp_path)
    scanned_page = pages[2]

    assert scanned_page.page_number == 3
    assert scanned_page.extracted_text == ""
    assert scanned_page.has_visual_content is True
    assert scanned_page.requires_vision is True