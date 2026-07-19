import json
from collections import Counter
from pathlib import Path

from schemas.vision_contract import VisionResponse
from src.ingestion.pdf_ingestor import PageRenderResult


class VisionResponseExporter:
    SCHEMA_VERSION = "v1"

    def export(
        self,
        result: PageRenderResult,
        responses: list[VisionResponse],
        output_dir: str | Path,
    ) -> Path:
        if not result.pages:
            raise ValueError(
                "Cannot export responses without material pages"
            )

        material_id = result.pages[0].material_id
        material_name = result.pages[0].material_name

        self._validate_responses(
            responses=responses,
            material_id=material_id,
        )

        status_counts = Counter(
            response.status.value
            for response in responses
        )

        export_dir = Path(output_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        output_path = export_dir / "vision_responses.json"

        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "material_id": material_id,
            "material_name": material_name,
            "total_responses": len(responses),
            "page_numbers": [
                response.page_number
                for response in responses
            ],
            "status_counts": dict(status_counts),
            "responses": [
                self._serialize_response(response)
                for response in responses
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

    @classmethod
    def _serialize_response(
        cls,
        response: VisionResponse,
    ) -> dict:
        return {
            "request_id": response.request_id,
            "material_id": response.material_id,
            "material_name": response.material_name,
            "page_number": response.page_number,
            "asset_id": response.asset_id,
            "status": response.status.value,
            "page_summary": response.page_summary,
            "ocr_text": response.ocr_text,
            "visual_elements": [
                {
                    "element_id": element.element_id,
                    "element_type": element.element_type.value,
                    "title": element.title,
                    "description": element.description,
                    "extracted_text": element.extracted_text,
                    "bounding_box": cls._serialize_box(
                        element.bounding_box
                    ),
                    "confidence": element.confidence,
                }
                for element in response.visual_elements
            ],
            "tables": [
                {
                    "table_id": table.table_id,
                    "title": table.title,
                    "headers": table.headers,
                    "rows": table.rows,
                    "notes": table.notes,
                    "bounding_box": cls._serialize_box(
                        table.bounding_box
                    ),
                    "confidence": table.confidence,
                }
                for table in response.tables
            ],
            "relationships": [
                {
                    "source_element_id": (
                        relationship.source_element_id
                    ),
                    "target_element_id": (
                        relationship.target_element_id
                    ),
                    "relation": relationship.relation,
                    "confidence": relationship.confidence,
                }
                for relationship in response.relationships
            ],
            "warnings": response.warnings,
            "confidence": response.confidence,
            "agent_model": response.agent_model,
            "prompt_version": response.prompt_version,
        }

    @staticmethod
    def _serialize_box(
        bounding_box: (
            tuple[float, float, float, float] | None
        ),
    ) -> list[float] | None:
        if bounding_box is None:
            return None

        return list(bounding_box)

    @staticmethod
    def _validate_responses(
        responses: list[VisionResponse],
        material_id: str,
    ) -> None:
        request_ids = [
            response.request_id
            for response in responses
        ]

        if len(request_ids) != len(set(request_ids)):
            raise ValueError(
                "Duplicate VisionResponse request_id"
            )

        for response in responses:
            if response.material_id != material_id:
                raise ValueError(
                    "Vision response material_id does not "
                    "match the rendered material"
                )