from dataclasses import dataclass
from pathlib import Path

from src.agents.multimodal_agent import (
    MultimodalAgent,
)
from src.evaluation.multimodal_verifier import (
    MultimodalVerificationBatch,
    MultimodalVerifier,
)
from src.ingestion.pdf_ingestor import PageRenderResult
from src.ingestion.vision_request_builder import (
    VisionRequestBuilder,
)
from src.ingestion.vision_request_exporter import (
    VisionRequestExporter,
)
from src.ingestion.vision_response_exporter import (
    VisionResponseExporter,
)
from src.ingestion.vision_verification_exporter import (
    VisionVerificationExporter,
)
from src.service.multimodal_pipeline import (
    MultimodalPipeline,
)


@dataclass(frozen=True)
class MultimodalRunArtifacts:
    requests_path: Path
    responses_path: Path | None
    verifications_path: Path | None

    total_requests: int
    total_responses: int
    verified_count: int
    needs_review_count: int
    rejected_count: int


class MultimodalIngestionRunner:
    def __init__(
        self,
        verifier: MultimodalVerifier | None = None,
    ) -> None:
        self.verifier = verifier or MultimodalVerifier()

    def run(
        self,
        result: PageRenderResult,
        agent: MultimodalAgent | None,
        output_dir: str | Path,
    ) -> MultimodalRunArtifacts:
        requests = VisionRequestBuilder().build(result)

        requests_path = VisionRequestExporter().export(
            result=result,
            requests=requests,
            output_dir=output_dir,
        )

        if agent is None or not requests:
            return MultimodalRunArtifacts(
                requests_path=requests_path,
                responses_path=None,
                verifications_path=None,
                total_requests=len(requests),
                total_responses=0,
                verified_count=0,
                needs_review_count=0,
                rejected_count=0,
            )

        responses = MultimodalPipeline(
            agent=agent
        ).process(requests)

        responses_path = VisionResponseExporter().export(
            result=result,
            responses=responses,
            output_dir=output_dir,
        )

        verification_batch = self.verifier.verify_batch(
            requests=requests,
            responses=responses,
        )

        verifications_path = (
            VisionVerificationExporter().export(
                requests=requests,
                batch=verification_batch,
                output_dir=output_dir,
            )
        )

        return self._create_artifacts(
            requests_path=requests_path,
            responses_path=responses_path,
            verifications_path=verifications_path,
            total_requests=len(requests),
            total_responses=len(responses),
            batch=verification_batch,
        )

    @staticmethod
    def _create_artifacts(
        requests_path: Path,
        responses_path: Path,
        verifications_path: Path,
        total_requests: int,
        total_responses: int,
        batch: MultimodalVerificationBatch,
    ) -> MultimodalRunArtifacts:
        return MultimodalRunArtifacts(
            requests_path=requests_path,
            responses_path=responses_path,
            verifications_path=verifications_path,
            total_requests=total_requests,
            total_responses=total_responses,
            verified_count=batch.verified_count,
            needs_review_count=(
                batch.needs_review_count
            ),
            rejected_count=batch.rejected_count,
        )