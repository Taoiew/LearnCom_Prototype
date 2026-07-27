import json
from pathlib import Path

from schemas.vision_contract import VisionRequest
from src.ingestion.pdf_ingestor import PageRenderResult


class VisionRequestExporter:
    SCHEMA_VERSION = "v1"

    def export(
        self,
        result: PageRenderResult,
        requests: list[VisionRequest],
        output_dir: str | Path,
    ) -> Path:
        if not result.pages:
            raise ValueError(
                "Cannot export requests without material pages"
            )

        material_id = result.pages[0].material_id
        material_name = result.pages[0].material_name

        self._validate_requests(
            requests=requests,
            material_id=material_id,
        )

        export_dir = Path(output_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        output_path = export_dir / "vision_requests.json"

        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "material_id": material_id,
            "material_name": material_name,
            "total_requests": len(requests),
            "page_numbers": [
                request.page_number
                for request in requests
            ],
            "requests": [
                {
                    "request_id": request.request_id,
                    "material_id": request.material_id,
                    "material_name": request.material_name,
                    "page_number": request.page_number,
                    "asset_id": request.asset_id,
                    "image_path": request.image_path,
                    "mime_type": request.mime_type,
                    "image_width_pixels": (
                        request.image_width_pixels
                    ),
                    "image_height_pixels": (
                        request.image_height_pixels
                    ),
                    "extracted_text": request.extracted_text,
                    "tasks": [
                        task.value
                        for task in request.tasks
                    ],
                    "prompt_version": request.prompt_version,
                }
                for request in requests
            ],
        }

        with output_path.open(
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

        return output_path

    @staticmethod
    def _validate_requests(
        requests: list[VisionRequest],
        material_id: str,
    ) -> None:
        for request in requests:
            if request.material_id != material_id:
                raise ValueError(
                    "Vision request material_id does not "
                    "match the rendered material"
                )