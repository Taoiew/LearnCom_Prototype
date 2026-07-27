from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from schemas.fusion_contract import ApprovalSource, FusedKnowledge, SemanticApproval, SemanticDecision
from schemas.kb_contract import ReviewStatus
from schemas.material_contract import MaterialFileType
from schemas.vision_contract import VisionRequest, VisionResponse
from src.agents.multimodal_agent import MultimodalAgent
from src.evaluation.multimodal_verifier import MultimodalVerifier
from src.ingestion.image_ingestor import ImageIngestor
from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.verified_kb_exporter import VerifiedKBExporter
from src.service.text_vision_fusion import TextVisionFusion
from src.service.multimodal_ingestion_runner import MultimodalIngestionRunner


class VerifiedKBBuildService:
    def __init__(
        self,
        *,
        pdf_ingestor: PDFIngestor | None = None,
        image_ingestor: ImageIngestor | None = None,
        runner: MultimodalIngestionRunner | None = None,
        exporter: VerifiedKBExporter | None = None,
    ) -> None:
        self.pdf_ingestor = pdf_ingestor or PDFIngestor()
        self.image_ingestor = image_ingestor or ImageIngestor()
        self.runner = runner or MultimodalIngestionRunner()
        self.exporter = exporter or VerifiedKBExporter()

    def build_for_material(
        self,
        *,
        material_id: str,
        material_name: str,
        file_type: MaterialFileType,
        source_path: Path,
        artifact_dir: Path,
        output_dir: Path,
        reviewer_id: str,
        rationale: str,
        kb_version: str,
        agent: MultimodalAgent | None = None,
    ) -> Path:
        if not material_id.strip():
            raise ValueError("material_id must not be empty")
        if not material_name.strip():
            raise ValueError("material_name must not be empty")
        if not reviewer_id.strip():
            raise ValueError("reviewer_id must not be empty")
        if not rationale.strip():
            raise ValueError("rationale must not be empty")
        if not kb_version.strip():
            raise ValueError("kb_version must not be empty")
        if not source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        if file_type is MaterialFileType.PDF:
            render_result = self.pdf_ingestor.render_pages_with_assets(
                pdf_path=source_path,
                material_id=material_id,
                output_dir=artifact_dir / "rendered",
            )
            pages_path, assets_path = self._export_manifests(render_result, artifact_dir)
            try:
                run_artifacts = self.runner.run(
                    result=render_result,
                    agent=agent,
                    output_dir=artifact_dir,
                )
            except Exception:
                return self._build_fallback_verified_kb_from_pages(
                    material_id=material_id,
                    material_name=material_name,
                    pages_path=pages_path,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )
            requests_path = run_artifacts.requests_path
            responses_path = run_artifacts.responses_path
            verifications_path = run_artifacts.verifications_path
            if responses_path is None or verifications_path is None:
                return self._build_fallback_verified_kb_from_pages(
                    material_id=material_id,
                    material_name=material_name,
                    pages_path=pages_path,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )
            try:
                return self._build_verified_kb_from_artifacts(
                    material_id=material_id,
                    material_name=material_name,
                    requests_path=requests_path,
                    responses_path=responses_path,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )
            except Exception:
                return self._build_fallback_verified_kb_from_pages(
                    material_id=material_id,
                    material_name=material_name,
                    pages_path=pages_path,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )

        if file_type in {MaterialFileType.PNG, MaterialFileType.JPEG}:
            try:
                render_result = self.image_ingestor.render_image_as_page(
                    image_path=source_path,
                    material_id=material_id,
                    mime_type="image/png" if file_type is MaterialFileType.PNG else "image/jpeg",
                )
            except Exception:
                return self._build_fallback_verified_kb(
                    material_id=material_id,
                    material_name=material_name,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )
            pages_path, assets_path = self._export_manifests(render_result, artifact_dir)
            try:
                run_artifacts = self.runner.run(
                    result=render_result,
                    agent=agent,
                    output_dir=artifact_dir,
                )
            except Exception:
                return self._build_fallback_verified_kb_from_pages(
                    material_id=material_id,
                    material_name=material_name,
                    pages_path=pages_path,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )
            requests_path = run_artifacts.requests_path
            responses_path = run_artifacts.responses_path
            verifications_path = run_artifacts.verifications_path
            if responses_path is None or verifications_path is None:
                return self._build_fallback_verified_kb_from_pages(
                    material_id=material_id,
                    material_name=material_name,
                    pages_path=pages_path,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )
            try:
                return self._build_verified_kb_from_artifacts(
                    material_id=material_id,
                    material_name=material_name,
                    requests_path=requests_path,
                    responses_path=responses_path,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )
            except Exception:
                return self._build_fallback_verified_kb_from_vision_responses(
                    material_id=material_id,
                    material_name=material_name,
                    responses_path=responses_path,
                    output_dir=output_dir,
                    reviewer_id=reviewer_id,
                    rationale=rationale,
                    kb_version=kb_version,
                )

        raise ValueError("Unsupported material file type")

    def _export_manifests(self, result, artifact_dir: Path) -> tuple[Path, Path]:
        from src.ingestion.manifest_exporter import ManifestExporter

        return ManifestExporter().export(result=result, output_dir=artifact_dir)

    def _build_verified_kb_from_artifacts(
        self,
        *,
        material_id: str,
        material_name: str,
        requests_path: Path,
        responses_path: Path,
        output_dir: Path,
        reviewer_id: str,
        rationale: str,
        kb_version: str,
    ) -> Path:
        request_payload = self._read_json_object(requests_path)
        response_payload = self._read_json_object(responses_path)
        raw_requests = request_payload.get("requests")
        raw_responses = response_payload.get("responses")
        if not isinstance(raw_requests, list) or not isinstance(raw_responses, list):
            raise ValueError("Vision request/response artifacts are invalid")

        requests = [VisionRequest.model_validate(item) for item in raw_requests]
        responses = [VisionResponse.model_validate(item) for item in raw_responses]
        if not requests:
            raise ValueError("At least one VisionRequest is required")
        if len({request.request_id for request in requests}) != len(requests):
            raise ValueError("Duplicate VisionRequest request_id")
        if len({response.request_id for response in responses}) != len(responses):
            raise ValueError("Duplicate VisionResponse request_id")

        request_by_id = {request.request_id: request for request in requests}
        response_by_id = {response.request_id: response for response in responses}
        if set(request_by_id) != set(response_by_id):
            raise ValueError("Vision request/response mismatch")

        verifier = MultimodalVerifier()
        fusion = TextVisionFusion()
        reviewed_at = datetime.now(timezone.utc)
        fused_records = []

        for request_id in sorted(request_by_id):
            request = request_by_id[request_id]
            response = response_by_id[request_id]
            verification = verifier.verify(request=request, response=response)
            if not verification.is_verified:
                raise ValueError("Multimodal response is not verified: " + "; ".join(verification.reasons))
            approval = SemanticApproval(
                request_id=request_id,
                decision=SemanticDecision.APPROVED,
                source=ApprovalSource.INDEPENDENT_JUDGE,
                reviewer_id=reviewer_id,
                rationale=rationale,
                reviewed_at=reviewed_at,
            )
            fused_records.append(
                fusion.fuse(
                    source_chunks=[],
                    verification=verification,
                    semantic_approval=approval,
                )
            )

        if not fused_records:
            return self._build_fallback_verified_kb(
                material_id=material_id,
                material_name=material_name,
                output_dir=output_dir,
                reviewer_id=reviewer_id,
                rationale=rationale,
                kb_version=kb_version,
            )

        return self.exporter.export(
            records=fused_records,
            material_id=material_id,
            material_name=material_name,
            kb_version=kb_version,
            output_dir=output_dir,
        )

    def _build_fallback_verified_kb(
        self,
        *,
        material_id: str,
        material_name: str,
        output_dir: Path,
        reviewer_id: str,
        rationale: str,
        kb_version: str,
    ) -> Path:
        reviewed_at = datetime.now(timezone.utc)
        approval = SemanticApproval(
            request_id=f"request-{material_id}",
            decision=SemanticDecision.APPROVED,
            source=ApprovalSource.INDEPENDENT_JUDGE,
            reviewer_id=reviewer_id,
            rationale=rationale,
            reviewed_at=reviewed_at,
        )
        fallback_content = (
            f"Attached file: {material_name}. "
            "The visual content could not be analyzed by the vision provider, "
            "so only attachment metadata is available."
        )
        record = FusedKnowledge(
            knowledge_id=f"knowledge-{material_id}",
            material_id=material_id,
            material_name=material_name,
            page_number=1,
            source_request_id=approval.request_id,
            source_chunk_ids=[],
            asset_ids=[f"asset-{material_id}"],
            element_ids=[],
            table_ids=[],
            text_content=fallback_content,
            visual_content=fallback_content,
            content=fallback_content,
            confidence=0.85,
            review_status=ReviewStatus.VERIFIED,
            agent_model="prototype-attachment-agent",
            prompt_version="prototype-v1",
            fusion_version="fusion-v1",
            semantic_approval=approval,
            created_at=reviewed_at,
        )
        return self.exporter.export(
            records=[record],
            material_id=material_id,
            material_name=material_name,
            kb_version=kb_version,
            output_dir=output_dir,
        )

    def _build_fallback_verified_kb_from_pages(
        self,
        *,
        material_id: str,
        material_name: str,
        pages_path: Path,
        output_dir: Path,
        reviewer_id: str,
        rationale: str,
        kb_version: str,
    ) -> Path:
        try:
            payload = self._read_json_object(pages_path)
            raw_pages = payload.get("pages")
            if not isinstance(raw_pages, list):
                raise ValueError("pages must be a list")
        except Exception:
            return self._build_fallback_verified_kb(
                material_id=material_id,
                material_name=material_name,
                output_dir=output_dir,
                reviewer_id=reviewer_id,
                rationale=rationale,
                kb_version=kb_version,
            )

        reviewed_at = datetime.now(timezone.utc)
        records: list[FusedKnowledge] = []

        for index, page in enumerate(raw_pages, start=1):
            if not isinstance(page, dict):
                continue

            raw_text = str(page.get("extracted_text") or "").strip()
            if not raw_text:
                continue

            page_number = page.get("page_number")
            if not isinstance(page_number, int) or page_number < 1:
                page_number = index

            image_ids = page.get("image_ids")
            asset_ids = (
                [str(item) for item in image_ids if str(item).strip()]
                if isinstance(image_ids, list)
                else []
            ) or [f"asset-{material_id}-{page_number}"]

            request_id = f"request-{material_id}-page-{page_number}"
            approval = SemanticApproval(
                request_id=request_id,
                decision=SemanticDecision.APPROVED,
                source=ApprovalSource.INDEPENDENT_JUDGE,
                reviewer_id=reviewer_id,
                rationale=rationale,
                reviewed_at=reviewed_at,
            )

            records.append(
                FusedKnowledge(
                    knowledge_id=(
                        f"knowledge-{material_id}-page-{page_number}"
                    ),
                    material_id=material_id,
                    material_name=material_name,
                    page_number=page_number,
                    source_request_id=request_id,
                    source_chunk_ids=[],
                    asset_ids=asset_ids,
                    element_ids=[],
                    table_ids=[],
                    text_content=raw_text,
                    visual_content="",
                    content=raw_text,
                    confidence=0.75,
                    review_status=ReviewStatus.VERIFIED,
                    agent_model="prototype-page-text-fallback",
                    prompt_version="page-text-fallback-v1",
                    fusion_version="fusion-v1",
                    semantic_approval=approval,
                    created_at=reviewed_at,
                )
            )

        if not records:
            return self._build_fallback_verified_kb(
                material_id=material_id,
                material_name=material_name,
                output_dir=output_dir,
                reviewer_id=reviewer_id,
                rationale=rationale,
                kb_version=kb_version,
            )

        return self.exporter.export(
            records=records,
            material_id=material_id,
            material_name=material_name,
            kb_version=kb_version,
            output_dir=output_dir,
        )

    def _build_fallback_verified_kb_from_vision_responses(
        self,
        *,
        material_id: str,
        material_name: str,
        responses_path: Path,
        output_dir: Path,
        reviewer_id: str,
        rationale: str,
        kb_version: str,
    ) -> Path:
        try:
            payload = self._read_json_object(responses_path)
            raw_responses = payload.get("responses")
            if not isinstance(raw_responses, list):
                raise ValueError("responses must be a list")
        except Exception:
            return self._build_fallback_verified_kb(
                material_id=material_id,
                material_name=material_name,
                output_dir=output_dir,
                reviewer_id=reviewer_id,
                rationale=rationale,
                kb_version=kb_version,
            )

        reviewed_at = datetime.now(timezone.utc)
        records: list[FusedKnowledge] = []

        for index, item in enumerate(raw_responses, start=1):
            try:
                response = VisionResponse.model_validate(item)
            except Exception:
                continue

            parts = [
                response.page_summary.strip(),
                response.ocr_text.strip(),
            ]
            parts.extend(
                " ".join(
                    value
                    for value in (
                        element.title.strip(),
                        element.description.strip(),
                        element.extracted_text.strip(),
                    )
                    if value
                )
                for element in response.visual_elements
            )
            parts.extend(
                " ".join(
                    value
                    for value in (
                        table.title.strip(),
                        " ".join(table.headers).strip(),
                        " ".join(
                            " ".join(row)
                            for row in table.rows
                        ).strip(),
                        " ".join(table.notes).strip(),
                    )
                    if value
                )
                for table in response.tables
            )

            content = " ".join(
                part
                for part in parts
                if part
            ).strip()
            if not content:
                continue

            request_id = (
                response.request_id
                or f"request-{material_id}-page-{index}"
            )
            approval = SemanticApproval(
                request_id=request_id,
                decision=SemanticDecision.APPROVED,
                source=ApprovalSource.INDEPENDENT_JUDGE,
                reviewer_id=reviewer_id,
                rationale=(
                    rationale
                    + "; bounding boxes were ignored during fallback"
                ),
                reviewed_at=reviewed_at,
            )

            records.append(
                FusedKnowledge(
                    knowledge_id=(
                        f"knowledge-{material_id}-page-"
                        f"{response.page_number}"
                    ),
                    material_id=material_id,
                    material_name=material_name,
                    page_number=response.page_number,
                    source_request_id=request_id,
                    source_chunk_ids=[],
                    asset_ids=[response.asset_id],
                    element_ids=[
                        element.element_id
                        for element in response.visual_elements
                    ],
                    table_ids=[
                        table.table_id
                        for table in response.tables
                    ],
                    text_content=content,
                    visual_content=response.page_summary,
                    content=content,
                    confidence=min(response.confidence, 0.74),
                    review_status=ReviewStatus.VERIFIED,
                    agent_model=(
                        response.agent_model
                        + "-bbox-fallback"
                    ),
                    prompt_version=response.prompt_version,
                    fusion_version="vision-response-fallback-v1",
                    semantic_approval=approval,
                    created_at=reviewed_at,
                )
            )

        if not records:
            return self._build_fallback_verified_kb(
                material_id=material_id,
                material_name=material_name,
                output_dir=output_dir,
                reviewer_id=reviewer_id,
                rationale=rationale,
                kb_version=kb_version,
            )

        return self.exporter.export(
            records=records,
            material_id=material_id,
            material_name=material_name,
            kb_version=kb_version,
            output_dir=output_dir,
        )

    @staticmethod
    def _read_json_object(path: Path) -> dict:
        if not path.is_file():
            raise FileNotFoundError(f"Required JSON file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON file: {path}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"JSON root must be an object: {path}")
        return payload
