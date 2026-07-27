from pathlib import Path

import fitz
import pytest

from src.ingestion.image_ingestor import ImageIngestor
from src.ingestion.pdf_ingestor import AssetType
from src.ingestion.vision_request_builder import (
    VisionRequestBuilder,
)


def create_image_bytes(
    tmp_path: Path,
    *,
    filename: str,
    width: int,
    height: int,
) -> bytes:
    pixmap = fitz.Pixmap(
        fitz.csRGB,
        fitz.IRect(0, 0, width, height),
        0,
    )
    pixmap.clear_with(240)

    image_path = tmp_path / filename
    pixmap.save(str(image_path))

    return image_path.read_bytes()


def test_png_ingestor_creates_single_visual_page(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.write_bytes(
        create_image_bytes(
            tmp_path,
            filename="source.png",
            width=7,
            height=5,
        )
    )

    result = ImageIngestor().render_image_as_page(
        image_path=image_path,
        material_id="material-001",
        mime_type="image/png",
    )

    assert len(result.pages) == 1
    assert len(result.assets) == 1

    page = result.pages[0]
    asset = result.assets[0]

    assert page.page_number == 1
    assert page.extracted_text == ""
    assert page.has_visual_content is True
    assert page.requires_vision is True
    assert page.rendered_image_path == str(image_path.resolve())

    assert asset.asset_type is AssetType.PAGE_RENDER
    assert asset.file_path == str(image_path.resolve())
    assert asset.mime_type == "image/png"
    assert asset.width_pixels == 7
    assert asset.height_pixels == 5
    assert page.image_ids == (asset.asset_id,)


def test_jpeg_ingestor_preserves_mime_and_dimensions(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "photo.jpg"
    image_path.write_bytes(
        create_image_bytes(
            tmp_path,
            filename="source.jpg",
            width=9,
            height=4,
        )
    )

    result = ImageIngestor().render_image_as_page(
        image_path=image_path,
        material_id="material-001",
        mime_type="image/jpeg",
    )

    asset = result.assets[0]

    assert asset.mime_type == "image/jpeg"
    assert asset.width_pixels == 9
    assert asset.height_pixels == 4


def test_image_asset_and_request_ids_are_deterministic(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "diagram.png"
    image_path.write_bytes(
        create_image_bytes(
            tmp_path,
            filename="source.png",
            width=3,
            height=2,
        )
    )

    ingestor = ImageIngestor()
    first = ingestor.render_image_as_page(
        image_path=image_path,
        material_id="material-001",
        mime_type="image/png",
    )
    second = ingestor.render_image_as_page(
        image_path=image_path,
        material_id="material-001",
        mime_type="image/png",
    )

    first_request = VisionRequestBuilder().build(first)[0]
    second_request = VisionRequestBuilder().build(second)[0]

    assert first.assets[0].asset_id == second.assets[0].asset_id
    assert first_request.request_id == second_request.request_id


def test_image_ingestor_rejects_corrupted_image(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "corrupted.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\nnot-a-real-png")

    with pytest.raises(
        ValueError,
        match="not readable",
    ):
        ImageIngestor().render_image_as_page(
            image_path=image_path,
            material_id="material-001",
            mime_type="image/png",
        )
