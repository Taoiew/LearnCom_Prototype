from src.ingestion.pdf_ingestor import AssetType, PageAsset


def test_page_render_asset_contract() -> None:
    asset = PageAsset(
        asset_id="asset-page-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_type=AssetType.PAGE_RENDER,
        file_path="rendered/material-001/page-0002.png",
        mime_type="image/png",
        width_pixels=1240,
        height_pixels=1755,
    )

    assert asset.asset_id == "asset-page-001"
    assert asset.material_id == "material-001"
    assert asset.material_name == "lesson.pdf"
    assert asset.page_number == 2
    assert asset.asset_type is AssetType.PAGE_RENDER
    assert asset.file_path.endswith("page-0002.png")
    assert asset.mime_type == "image/png"
    assert asset.width_pixels == 1240
    assert asset.height_pixels == 1755
    assert asset.bounding_box is None


def test_cropped_visual_asset_supports_bounding_box() -> None:
    asset = PageAsset(
        asset_id="asset-table-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_type=AssetType.TABLE,
        file_path="rendered/material-001/table-001.png",
        mime_type="image/png",
        width_pixels=600,
        height_pixels=320,
        bounding_box=(50.0, 80.0, 650.0, 400.0),
    )

    assert asset.asset_type is AssetType.TABLE
    assert asset.bounding_box == (
        50.0,
        80.0,
        650.0,
        400.0,
    )