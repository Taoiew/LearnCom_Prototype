import json
from pathlib import Path

from src.ingestion.pdf_ingestor import PageRenderResult


class ManifestExporter:
    SCHEMA_VERSION = "v1"

    def export(
        self,
        result: PageRenderResult,
        output_dir: str | Path,
    ) -> tuple[Path, Path]:
        if not result.pages:
            raise ValueError("Cannot export an empty page manifest")

        if not result.assets:
            raise ValueError("Cannot export an empty asset manifest")

        material_ids = {
            page.material_id for page in result.pages
        }

        if len(material_ids) != 1:
            raise ValueError(
                "All pages must belong to the same material"
            )

        material_id = result.pages[0].material_id
        material_name = result.pages[0].material_name

        manifest_dir = Path(output_dir)
        manifest_dir.mkdir(parents=True, exist_ok=True)

        pages_path = manifest_dir / "pages.json"
        assets_path = manifest_dir / "assets.json"

        pages_payload = {
            "schema_version": self.SCHEMA_VERSION,
            "material_id": material_id,
            "material_name": material_name,
            "total_pages": len(result.pages),
            "vision_page_numbers": [
                page.page_number
                for page in result.pages
                if page.requires_vision
            ],
            "pages": [
                {
                    "material_id": page.material_id,
                    "material_name": page.material_name,
                    "page_number": page.page_number,
                    "extracted_text": page.extracted_text,
                    "rendered_image_path": (
                        page.rendered_image_path
                    ),
                    "image_ids": list(page.image_ids),
                    "has_visual_content": (
                        page.has_visual_content
                    ),
                    "requires_vision": page.requires_vision,
                }
                for page in result.pages
            ],
        }

        assets_payload = {
            "schema_version": self.SCHEMA_VERSION,
            "material_id": material_id,
            "material_name": material_name,
            "total_assets": len(result.assets),
            "assets": [
                {
                    "asset_id": asset.asset_id,
                    "material_id": asset.material_id,
                    "material_name": asset.material_name,
                    "page_number": asset.page_number,
                    "asset_type": asset.asset_type.value,
                    "file_path": asset.file_path,
                    "mime_type": asset.mime_type,
                    "width_pixels": asset.width_pixels,
                    "height_pixels": asset.height_pixels,
                    "bounding_box": (
                        list(asset.bounding_box)
                        if asset.bounding_box is not None
                        else None
                    ),
                }
                for asset in result.assets
            ],
        }

        self._write_json(pages_path, pages_payload)
        self._write_json(assets_path, assets_payload)

        return pages_path, assets_path

    @staticmethod
    def _write_json(
        file_path: Path,
        payload: dict,
    ) -> None:
        with file_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                payload,
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")