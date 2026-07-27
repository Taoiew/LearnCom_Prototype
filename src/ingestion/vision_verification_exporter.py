import json
from collections import Counter
from pathlib import Path

from schemas.kb_contract import ReviewStatus
from schemas.vision_contract import VisionRequest
from src.evaluation.multimodal_verifier import (
    MultimodalBatchIssue,
    MultimodalVerificationBatch,
    MultimodalVerificationResult,
)
from src.ingestion.vision_response_exporter import (
    VisionResponseExporter,
)


class VisionVerificationExporter:
    SCHEMA_VERSION = "v1"

    def export(
        self,
        requests: list[VisionRequest],
        batch: MultimodalVerificationBatch,
        output_dir: str | Path,
    ) -> Path:
        material_id = self._material_id_from_requests(
            requests
        )
        material_name = self._material_name_from_requests(
            requests
        )

        review_counts = Counter(
            result.review_status.value
            for result in batch.results
        )
        review_counts.update(
            issue.review_status.value
            for issue in batch.issues
        )

        export_dir = Path(output_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        output_path = export_dir / "vision_verifications.json"

        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "material_id": material_id,
            "material_name": material_name,
            "total_requests": len(requests),
            "total_results": len(batch.results),
            "verified_count": batch.verified_count,
            "needs_review_count": batch.needs_review_count,
            "rejected_count": batch.rejected_count,
            "review_status_counts": dict(review_counts),
            "verified": [
                self._serialize_result(result)
                for result in batch.results
                if result.review_status
                is ReviewStatus.VERIFIED
            ],
            "needs_review": [
                self._serialize_result(result)
                for result in batch.results
                if result.review_status
                is ReviewStatus.NEEDS_REVIEW
            ],
            "rejected": [
                self._serialize_result(result)
                for result in batch.results
                if result.review_status
                is ReviewStatus.REJECTED
            ],
            "batch_issues": [
                self._serialize_issue(issue)
                for issue in batch.issues
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
    def _serialize_result(
        result: MultimodalVerificationResult,
    ) -> dict:
        response = VisionResponseExporter._serialize_response(
            result.response
        )

        return {
            "request_id": result.response.request_id,
            "review_status": result.review_status.value,
            "is_verified": result.is_verified,
            "reasons": result.reasons,
            "response": response,
        }

    @staticmethod
    def _serialize_issue(
        issue: MultimodalBatchIssue,
    ) -> dict:
        return {
            "request_id": issue.request_id,
            "review_status": issue.review_status.value,
            "reasons": issue.reasons,
        }

    @staticmethod
    def _material_id_from_requests(
        requests: list[VisionRequest],
    ) -> str:
        if not requests:
            return ""

        material_ids = {
            request.material_id
            for request in requests
        }

        if len(material_ids) != 1:
            raise ValueError(
                "Vision verification requests must share "
                "one material_id"
            )

        return requests[0].material_id

    @staticmethod
    def _material_name_from_requests(
        requests: list[VisionRequest],
    ) -> str:
        if not requests:
            return ""

        material_names = {
            request.material_name
            for request in requests
        }

        if len(material_names) != 1:
            raise ValueError(
                "Vision verification requests must share "
                "one material_name"
            )

        return requests[0].material_name
