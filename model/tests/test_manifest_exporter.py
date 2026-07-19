import json
from pathlib import Path

import fitz

from src.ingestion.manifest_exporter import ManifestExporter
from src.ingestion.pdf_ingestor import PDFIngestor


def create_manifest_test_pdf(pdf_path: Path) -> None:
    with fitz.open() as document:
        text_page = document.new_page()
        text_page.insert_text(
            (72, 72),
            "Text-only page",
        )

        visual_page = document.new_page()
        visual_page.insert_text(
            (72, 72),
            "Page with a diagram",
        )
        visual_page.draw_rect(
            fitz.Rect(72, 100, 250, 180),
            color=(0, 0, 0),
            width=1,
        )

        document.save(pdf_path)


def test_export_pages_and_assets_manifests(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "lesson.pdf"
    render_dir = tmp_path / "rendered"
    manifest_dir = tmp_path / "manifests"

    create_manifest_test_pdf(pdf_path)

    ingestor = PDFIngestor(render_dpi=72)

    result = ingestor.render_pages_with_assets(
        pdf_path=pdf_path,
        material_id="material-001",
        output_dir=render_dir,
    )

    exporter = ManifestExporter()

    pages_path, assets_path = exporter.export(
        result=result,
        output_dir=manifest_dir,
    )

    assert pages_path.exists()
    assert assets_path.exists()

    pages_payload = json.loads(
        pages_path.read_text(encoding="utf-8")
    )
    assets_payload = json.loads(
        assets_path.read_text(encoding="utf-8")
    )

    assert pages_payload["schema_version"] == "v1"
    assert pages_payload["material_id"] == "material-001"
    assert pages_payload["material_name"] == "lesson.pdf"
    assert pages_payload["total_pages"] == 2
    assert pages_payload["vision_page_numbers"] == [2]

    assert len(pages_payload["pages"]) == 2
    assert pages_payload["pages"][0]["requires_vision"] is False
    assert pages_payload["pages"][1]["requires_vision"] is True

    assert assets_payload["schema_version"] == "v1"
    assert assets_payload["material_id"] == "material-001"
    assert assets_payload["total_assets"] == 2

    first_asset = assets_payload["assets"][0]
    second_asset = assets_payload["assets"][1]

    assert first_asset["asset_type"] == "page_render"
    assert second_asset["asset_type"] == "page_render"

    assert first_asset["asset_id"].startswith("asset-")
    assert second_asset["asset_id"].startswith("asset-")

    assert (
        pages_payload["pages"][0]["image_ids"][0]
        == first_asset["asset_id"]
    )
    assert (
        pages_payload["pages"][1]["image_ids"][0]
        == second_asset["asset_id"]
    )


def test_export_rejects_empty_result(
    tmp_path: Path,
) -> None:
    from src.ingestion.pdf_ingestor import PageRenderResult

    empty_result = PageRenderResult(
        pages=(),
        assets=(),
    )

    exporter = ManifestExporter()

    try:
        exporter.export(
            result=empty_result,
            output_dir=tmp_path,
        )
    except ValueError as error:
        assert str(error) == (
            "Cannot export an empty page manifest"
        )
    else:
        raise AssertionError(
            "Expected empty manifest export to fail"
        )