from pathlib import Path

import fitz

from src.ingestion.pdf_ingestor import AssetType, PDFIngestor


def create_test_pdf(pdf_path: Path) -> None:
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "Page asset integration test",
        )
        document.save(pdf_path)


def test_render_pages_with_assets_links_page_and_asset(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"
    output_dir = tmp_path / "rendered"

    create_test_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)

    result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=output_dir,
    )

    assert len(result.pages) == 1
    assert len(result.assets) == 1

    page = result.pages[0]
    asset = result.assets[0]

    assert page.image_ids == (asset.asset_id,)
    assert page.rendered_image_path == asset.file_path

    assert asset.asset_id.startswith("asset-")
    assert asset.material_id == page.material_id
    assert asset.material_name == page.material_name
    assert asset.page_number == page.page_number
    assert asset.asset_type is AssetType.PAGE_RENDER
    assert asset.mime_type == "image/png"

    assert asset.width_pixels > 0
    assert asset.height_pixels > 0
    assert Path(asset.file_path).exists()


def test_asset_id_is_stable_across_output_directories(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"

    create_test_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)

    first_result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=tmp_path / "first-output",
    )

    second_result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=tmp_path / "second-output",
    )

    first_asset = first_result.assets[0]
    second_asset = second_result.assets[0]

    assert first_asset.asset_id == second_asset.asset_id
    assert first_asset.file_path != second_asset.file_path


def test_legacy_render_pages_still_returns_list(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"

    create_test_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)

    pages = ingestor.render_pages(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=tmp_path / "rendered",
    )

    assert isinstance(pages, list)
    assert len(pages) == 1
    assert len(pages[0].image_ids) == 1