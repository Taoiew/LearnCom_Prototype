import hashlib
from pathlib import Path

from schemas.vision_contract import VisionRequest
from src.ingestion.pdf_ingestor import (
    AssetType,
    PageAsset,
    PageRenderResult,
)


class VisionRequestBuilder:
    PROMPT_VERSION = "vision-v1"

    def build(
        self,
        result: PageRenderResult,
    ) -> list[VisionRequest]:
        assets_by_id = {
            asset.asset_id: asset
            for asset in result.assets
        }

        requests: list[VisionRequest] = []

        for page in result.pages:
            if not page.requires_vision:
                continue

            page_asset = self._find_page_render_asset(
                image_ids=page.image_ids,
                assets_by_id=assets_by_id,
                page_number=page.page_number,
            )

            image_path = Path(page_asset.file_path)

            if not image_path.is_file():
                raise FileNotFoundError(
                    "Vision asset file not found: "
                    f"{image_path}"
                )

            request_id = self._create_request_id(
                material_id=page.material_id,
                page_number=page.page_number,
                asset_id=page_asset.asset_id,
            )

            requests.append(
                VisionRequest(
                    request_id=request_id,
                    material_id=page.material_id,
                    material_name=page.material_name,
                    page_number=page.page_number,
                    asset_id=page_asset.asset_id,
                    image_path=page_asset.file_path,
                    mime_type=page_asset.mime_type,
                    image_width_pixels=page_asset.width_pixels,
                    image_height_pixels=page_asset.height_pixels,
                    extracted_text=page.extracted_text,
                    prompt_version=self.PROMPT_VERSION,
                )
            )

        return requests

    @staticmethod
    def _find_page_render_asset(
        image_ids: tuple[str, ...],
        assets_by_id: dict[str, PageAsset],
        page_number: int,
    ) -> PageAsset:
        for asset_id in image_ids:
            asset = assets_by_id.get(asset_id)

            if (
                asset is not None
                and asset.asset_type is AssetType.PAGE_RENDER
            ):
                return asset

        raise ValueError(
            "No page-render asset found for "
            f"vision page {page_number}"
        )

    def _create_request_id(
        self,
        material_id: str,
        page_number: int,
        asset_id: str,
    ) -> str:
        source = (
            f"{material_id}:"
            f"{page_number}:"
            f"{asset_id}:"
            f"{self.PROMPT_VERSION}"
        )

        digest = hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()[:16]

        return f"vision-{digest}"