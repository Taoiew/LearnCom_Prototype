import json
from pathlib import Path

from schemas.material_contract import MaterialFileType
from schemas.vision_contract import (
    VisionRequest,
    VisionResponse,
    VisionResponseStatus,
    VisionTask,
    VisualElement,
    VisualElementType,
)
from src.ingestion.pdf_ingestor import (
    AssetType,
    MaterialPage,
    PageAsset,
    PageRenderResult,
)
from src.service.multimodal_ingestion_runner import MultimodalRunArtifacts
from src.service.verified_kb_build_service import VerifiedKBBuildService


class FakeImageIngestor:
    def render_image_as_page(
        self,
        *,
        image_path: Path,
        material_id: str,
        mime_type: str,
    ) -> PageRenderResult:
        material_name = image_path.name
        return PageRenderResult(
            pages=(
                MaterialPage(
                    material_id=material_id,
                    material_name=material_name,
                    page_number=1,
                    extracted_text="Similarities between AWS and traditional IT",
                    rendered_image_path=str(image_path),
                    image_ids=("asset-slide-1",),
                    has_visual_content=True,
                    requires_vision=True,
                ),
            ),
            assets=(
                PageAsset(
                    asset_id="asset-slide-1",
                    material_id=material_id,
                    material_name=material_name,
                    page_number=1,
                    asset_type=AssetType.PAGE_RENDER,
                    file_path=str(image_path),
                    mime_type=mime_type,
                    width_pixels=640,
                    height_pixels=320,
                ),
            ),
        )


class FakeRunnerWithOverflowingBoundingBox:
    def run(self, result, agent, output_dir: Path) -> MultimodalRunArtifacts:
        output_dir.mkdir(parents=True, exist_ok=True)
        requests_path = output_dir / "vision_requests.json"
        responses_path = output_dir / "vision_responses.json"
        verifications_path = output_dir / "vision_verifications.json"

        request = VisionRequest(
            request_id="vision-slide-1",
            material_id="material-slide",
            material_name="slide.png",
            page_number=1,
            asset_id="asset-slide-1",
            image_path="slide.png",
            image_width_pixels=640,
            image_height_pixels=320,
            extracted_text="Similarities between AWS and traditional IT",
            tasks=[VisionTask.DESCRIBE_VISUALS],
        )
        response = VisionResponse(
            request_id="vision-slide-1",
            material_id="material-slide",
            material_name="slide.png",
            page_number=1,
            asset_id="asset-slide-1",
            status=VisionResponseStatus.SUCCESS,
            page_summary=(
                "The slide compares traditional on-premises IT with AWS "
                "cloud services."
            ),
            ocr_text="Similarities between AWS and traditional IT",
            visual_elements=[
                VisualElement(
                    element_id="comparison_diagram",
                    element_type=VisualElementType.DIAGRAM,
                    title="Comparison diagram",
                    description=(
                        "Security groups, VPC, EC2, S3, EFS, EBS, and RDS "
                        "are mapped to traditional networking, compute, "
                        "and storage components."
                    ),
                    extracted_text="AWS cloud service mapping",
                    confidence=0.92,
                    bounding_box=(20, 20, 620, 420),
                )
            ],
            confidence=0.91,
            agent_model="gemini-test",
        )

        requests_path.write_text(
            json.dumps(
                {"requests": [request.model_dump(mode="json")]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        responses_path.write_text(
            json.dumps(
                {"responses": [response.model_dump(mode="json")]},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        verifications_path.write_text(
            json.dumps({"results": []}),
            encoding="utf-8",
        )

        return MultimodalRunArtifacts(
            requests_path=requests_path,
            responses_path=responses_path,
            verifications_path=verifications_path,
            total_requests=1,
            total_responses=1,
            verified_count=0,
            needs_review_count=0,
            rejected_count=1,
        )


def test_image_build_uses_vision_response_fallback_when_bounding_boxes_are_invalid(
    tmp_path: Path,
) -> None:
    source_path = tmp_path / "slide.png"
    source_path.write_bytes(b"fake-image")

    service = VerifiedKBBuildService(
        image_ingestor=FakeImageIngestor(),
        runner=FakeRunnerWithOverflowingBoundingBox(),
    )

    kb_path = service.build_for_material(
        material_id="material-slide",
        material_name="slide.png",
        file_type=MaterialFileType.PNG,
        source_path=source_path,
        artifact_dir=tmp_path / "artifacts",
        output_dir=tmp_path / "kb",
        reviewer_id="system",
        rationale="Automated test approval",
        kb_version="kb-test-v1",
    )

    payload = json.loads(kb_path.read_text(encoding="utf-8"))
    assert payload["total_records"] == 1

    record = payload["records"][0]
    assert "compares traditional on-premises IT with AWS" in record["content"]
    assert "Security groups, VPC, EC2" in record["content"]
    assert record["agent_model"] == "gemini-test-bbox-fallback"
    assert record["fusion_version"] == "vision-response-fallback-v1"
