import hashlib
from pathlib import Path

import fitz

from src.ingestion.pdf_ingestor import (
    AssetType,
    MaterialPage,
    PageAsset,
    PageRenderResult,
)


class ImageIngestor:
    def render_image_as_page(
        self,
        image_path: str | Path,
        *,
        material_id: str,
        mime_type: str,
    ) -> PageRenderResult:
        path = self._validate_image_path(image_path)

        if not material_id.strip():
            raise ValueError("material_id must not be empty")

        if mime_type not in {"image/png", "image/jpeg"}:
            raise ValueError(
                "Expected PNG or JPEG image MIME type"
            )

        try:
            pixmap = fitz.Pixmap(str(path))
        except Exception as exc:
            raise ValueError(
                f"Image file is not readable: {path}"
            ) from exc

        asset_id = self._create_asset_id(
            material_id=material_id,
            page_number=1,
            asset_type=AssetType.PAGE_RENDER,
        )
        resolved_image_path = str(path.resolve())

        page = MaterialPage(
            material_id=material_id,
            material_name=path.name,
            page_number=1,
            extracted_text="",
            rendered_image_path=resolved_image_path,
            image_ids=(asset_id,),
            has_visual_content=True,
            requires_vision=True,
        )

        asset = PageAsset(
            asset_id=asset_id,
            material_id=material_id,
            material_name=path.name,
            page_number=1,
            asset_type=AssetType.PAGE_RENDER,
            file_path=resolved_image_path,
            mime_type=mime_type,
            width_pixels=pixmap.width,
            height_pixels=pixmap.height,
        )

        return PageRenderResult(
            pages=(page,),
            assets=(asset,),
        )

    @staticmethod
    def _validate_image_path(
        image_path: str | Path,
    ) -> Path:
        path = Path(image_path)

        if not path.exists():
            raise FileNotFoundError(
                f"Image not found: {path}"
            )

        if not path.is_file():
            raise ValueError(
                f"Image path is not a file: {path}"
            )

        if path.suffix.lower() not in {
            ".png",
            ".jpg",
            ".jpeg",
        }:
            raise ValueError(
                f"Expected a PNG or JPEG image file: {path}"
            )

        return path

    @staticmethod
    def _create_asset_id(
        material_id: str,
        page_number: int,
        asset_type: AssetType,
    ) -> str:
        source = (
            f"{material_id}:"
            f"{page_number}:"
            f"{asset_type.value}"
        )
        digest = hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()[:16]

        return f"asset-{digest}"
