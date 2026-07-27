import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from schemas.fusion_contract import (
    ApprovalSource,
    SemanticApproval,
    SemanticDecision,
)
from schemas.vision_contract import (
    VisionRequest,
    VisionResponse,
)
from src.evaluation.multimodal_verifier import (
    MultimodalVerifier,
)
from src.ingestion.verified_kb_exporter import (
    VerifiedKBExporter,
)
from src.service.text_vision_fusion import (
    TextVisionFusion,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build Verified KB from an uploaded PNG/JPEG "
            "and its multimodal artifacts."
        )
    )

    parser.add_argument(
        "--requests",
        type=Path,
        required=True,
        help="Path to vision_requests.json",
    )

    parser.add_argument(
        "--responses",
        type=Path,
        required=True,
        help="Path to vision_responses.json",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for verified_kb.json",
    )

    parser.add_argument(
        "--reviewer-id",
        required=True,
    )

    parser.add_argument(
        "--rationale",
        required=True,
    )

    parser.add_argument(
        "--kb-version",
        required=True,
    )

    return parser.parse_args()


def read_json_object(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(
            f"Required JSON file not found: {path}"
        )

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON file: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError(
            f"JSON root must be an object: {path}"
        )

    return payload


def build_verified_kb_from_image(
    *,
    requests_path: Path,
    responses_path: Path,
    output_dir: Path,
    reviewer_id: str,
    rationale: str,
    kb_version: str,
) -> Path:
    reviewer_id = reviewer_id.strip()
    rationale = rationale.strip()
    kb_version = kb_version.strip()

    if not reviewer_id:
        raise ValueError(
            "reviewer_id must not be empty"
        )

    if not rationale:
        raise ValueError(
            "rationale must not be empty"
        )

    if not kb_version:
        raise ValueError(
            "kb_version must not be empty"
        )

    request_payload = read_json_object(
        requests_path
    )
    response_payload = read_json_object(
        responses_path
    )

    raw_requests = request_payload.get("requests")
    raw_responses = response_payload.get("responses")

    if not isinstance(raw_requests, list):
        raise ValueError(
            "vision_requests.json requests must be a list"
        )

    if not isinstance(raw_responses, list):
        raise ValueError(
            "vision_responses.json responses must be a list"
        )

    requests = [
        VisionRequest.model_validate(item)
        for item in raw_requests
    ]

    responses = [
        VisionResponse.model_validate(item)
        for item in raw_responses
    ]

    if not requests:
        raise ValueError(
            "At least one VisionRequest is required"
        )

    request_ids = [
        request.request_id
        for request in requests
    ]

    response_ids = [
        response.request_id
        for response in responses
    ]

    if len(request_ids) != len(set(request_ids)):
        raise ValueError(
            "Duplicate VisionRequest request_id"
        )

    if len(response_ids) != len(set(response_ids)):
        raise ValueError(
            "Duplicate VisionResponse request_id"
        )

    request_by_id = {
        request.request_id: request
        for request in requests
    }

    response_by_id = {
        response.request_id: response
        for response in responses
    }

    if set(request_by_id) != set(response_by_id):
        missing = sorted(
            set(request_by_id) - set(response_by_id)
        )
        unexpected = sorted(
            set(response_by_id) - set(request_by_id)
        )

        raise ValueError(
            "Vision request/response mismatch. "
            f"Missing responses: {missing}. "
            f"Unexpected responses: {unexpected}."
        )

    material_ids = {
        request.material_id
        for request in requests
    }

    material_names = {
        request.material_name
        for request in requests
    }

    if len(material_ids) != 1:
        raise ValueError(
            "Requests must belong to one material_id"
        )

    if len(material_names) != 1:
        raise ValueError(
            "Requests must belong to one material_name"
        )

    material_id = next(iter(material_ids))
    material_name = next(iter(material_names))

    verifier = MultimodalVerifier()
    fusion = TextVisionFusion()

    reviewed_at = datetime.now(timezone.utc)
    fused_records = []

    for request_id in sorted(request_by_id):
        request = request_by_id[request_id]
        response = response_by_id[request_id]

        verification = verifier.verify(
            request=request,
            response=response,
        )

        if not verification.is_verified:
            raise ValueError(
                "Multimodal response is not verified: "
                + "; ".join(verification.reasons)
            )

        approval = SemanticApproval(
            request_id=request_id,
            decision=SemanticDecision.APPROVED,
            source=ApprovalSource.HUMAN,
            reviewer_id=reviewer_id,
            rationale=rationale,
            reviewed_at=reviewed_at,
        )

        # Image-only material has no PDF text chunks.
        # TextVisionFusion supports visual-only knowledge.
        fused_record = fusion.fuse(
            source_chunks=[],
            verification=verification,
            semantic_approval=approval,
        )

        fused_records.append(fused_record)

    return VerifiedKBExporter().export(
        records=fused_records,
        material_id=material_id,
        material_name=material_name,
        kb_version=kb_version,
        output_dir=output_dir,
    )


def main() -> None:
    args = parse_arguments()

    verified_kb_path = build_verified_kb_from_image(
        requests_path=args.requests,
        responses_path=args.responses,
        output_dir=args.output_dir,
        reviewer_id=args.reviewer_id,
        rationale=args.rationale,
        kb_version=args.kb_version,
    )

    print()
    print("Image Verified KB build completed.")
    print(
        f"Verified KB: {verified_kb_path.resolve()}"
    )


if __name__ == "__main__":
    main()