import argparse
import json
import os
import tempfile
from collections import defaultdict
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
from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.verified_kb_exporter import (
    VerifiedKBExporter,
)
from src.service.text_vision_fusion import (
    TextVisionFusion,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Review structurally verified multimodal "
            "responses, fuse them with source PDF text, "
            "and export an auditable Verified KB."
        )
    )

    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the source PDF.",
    )

    parser.add_argument(
        "--requests",
        type=Path,
        required=True,
        help="Path to vision_requests.json.",
    )

    parser.add_argument(
        "--responses",
        type=Path,
        required=True,
        help="Path to vision_responses.json.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory for reviewed artifacts and Verified KB.",
    )

    parser.add_argument(
        "--reviewer-id",
        required=True,
        help="Stable identifier of the human reviewer.",
    )

    parser.add_argument(
        "--rationale",
        required=True,
        help="Reason for semantic approval.",
    )

    parser.add_argument(
        "--kb-version",
        required=True,
        help="Version identifier for the resulting KB.",
    )

    parser.add_argument(
        "--exclude-relationship",
        action="append",
        default=[],
        metavar="REQUEST_ID:INDEX",
        help=(
            "Remove a relationship before approval. "
            "INDEX is one-based. May be supplied multiple times."
        ),
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
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Invalid JSON file: {path}"
        ) from error

    if not isinstance(payload, dict):
        raise ValueError(
            f"JSON root must be an object: {path}"
        )

    return payload


def parse_exclusions(
    specifications: list[str],
) -> dict[str, set[int]]:
    exclusions: dict[str, set[int]] = defaultdict(set)

    for specification in specifications:
        try:
            request_id, raw_index = specification.rsplit(
                ":",
                1,
            )
            index = int(raw_index)
        except (ValueError, AttributeError) as error:
            raise ValueError(
                "Relationship exclusion must use "
                "REQUEST_ID:INDEX"
            ) from error

        request_id = request_id.strip()

        if not request_id:
            raise ValueError(
                "Relationship exclusion request_id "
                "must not be empty"
            )

        if index < 1:
            raise ValueError(
                "Relationship exclusion INDEX "
                "must be at least 1"
            )

        exclusions[request_id].add(index)

    return dict(exclusions)


def validate_unique_ids(
    values: list[str],
    label: str,
) -> None:
    if len(values) != len(set(values)):
        raise ValueError(
            f"Duplicate {label} detected"
        )


def apply_relationship_corrections(
    responses: list[VisionResponse],
    exclusions: dict[str, set[int]],
) -> tuple[list[VisionResponse], list[dict]]:
    response_ids = {
        response.request_id
        for response in responses
    }

    unknown_request_ids = sorted(
        set(exclusions) - response_ids
    )

    if unknown_request_ids:
        raise ValueError(
            "Relationship exclusions reference "
            "unknown request_id: "
            + ", ".join(unknown_request_ids)
        )

    corrected_responses: list[VisionResponse] = []
    corrections: list[dict] = []

    for response in responses:
        excluded_indexes = exclusions.get(
            response.request_id,
            set(),
        )

        relationship_count = len(
            response.relationships
        )

        for index in excluded_indexes:
            if index > relationship_count:
                raise ValueError(
                    "Relationship exclusion index "
                    f"{index} exceeds relationship count "
                    f"for {response.request_id}"
                )

        retained_relationships = []
        removed_relationships = []

        for index, relationship in enumerate(
            response.relationships,
            start=1,
        ):
            if index in excluded_indexes:
                removed_relationships.append(
                    {
                        "index": index,
                        "relationship": (
                            relationship.model_dump(
                                mode="json"
                            )
                        ),
                    }
                )
            else:
                retained_relationships.append(
                    relationship
                )

        corrected_response = response.model_copy(
            update={
                "relationships": retained_relationships,
            }
        )

        corrected_responses.append(
            corrected_response
        )

        if removed_relationships:
            corrections.append(
                {
                    "request_id": response.request_id,
                    "action": "exclude_relationship",
                    "removed": removed_relationships,
                }
            )

    return corrected_responses, corrections


def write_json_atomically(
    output_path: Path,
    payload: dict,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f".{output_path.stem}-",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(
                temporary_file.name
            )

            json.dump(
                payload,
                temporary_file,
                ensure_ascii=False,
                indent=2,
            )
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        temporary_path.replace(output_path)

    except Exception:
        if (
            temporary_path is not None
            and temporary_path.exists()
        ):
            temporary_path.unlink()

        raise


def build_verified_kb(
    *,
    pdf_path: Path,
    requests_path: Path,
    responses_path: Path,
    output_dir: Path,
    reviewer_id: str,
    rationale: str,
    kb_version: str,
    exclusion_specs: list[str],
) -> tuple[Path, Path, Path]:
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

    raw_requests = request_payload.get(
        "requests"
    )
    raw_responses = response_payload.get(
        "responses"
    )

    if not isinstance(raw_requests, list):
        raise ValueError(
            "vision_requests.json requests "
            "must be a list"
        )

    if not isinstance(raw_responses, list):
        raise ValueError(
            "vision_responses.json responses "
            "must be a list"
        )

    requests = [
        VisionRequest.model_validate(item)
        for item in raw_requests
    ]

    responses = [
        VisionResponse.model_validate(item)
        for item in raw_responses
    ]

    validate_unique_ids(
        [
            request.request_id
            for request in requests
        ],
        "VisionRequest request_id",
    )

    validate_unique_ids(
        [
            response.request_id
            for response in responses
        ],
        "VisionResponse request_id",
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
        missing_responses = sorted(
            set(request_by_id) - set(response_by_id)
        )
        unexpected_responses = sorted(
            set(response_by_id) - set(request_by_id)
        )

        raise ValueError(
            "Vision request/response mismatch. "
            f"Missing responses: {missing_responses}. "
            f"Unexpected responses: {unexpected_responses}."
        )

    if not requests:
        raise ValueError(
            "At least one VisionRequest is required"
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

    exclusions = parse_exclusions(
        exclusion_specs
    )

    corrected_responses, corrections = (
        apply_relationship_corrections(
            responses=responses,
            exclusions=exclusions,
        )
    )

    corrected_response_by_id = {
        response.request_id: response
        for response in corrected_responses
    }

    verifier = MultimodalVerifier()

    verifications = []

    for request_id in sorted(request_by_id):
        verification = verifier.verify(
            request=request_by_id[request_id],
            response=corrected_response_by_id[
                request_id
            ],
        )

        if not verification.is_verified:
            raise ValueError(
                "Corrected multimodal response "
                f"{request_id} is not structurally "
                "verified: "
                + "; ".join(verification.reasons)
            )

        verifications.append(verification)

    source_chunks = PDFIngestor().ingest(
        pdf_path=pdf_path,
        material_id=material_id,
    )

    chunks_by_page = defaultdict(list)

    for chunk in source_chunks:
        chunks_by_page[
            chunk.page_number
        ].append(chunk)

    reviewed_at = datetime.now(
        timezone.utc
    )

    approvals = []
    fused_records = []

    fusion = TextVisionFusion()

    for verification in verifications:
        response = verification.response

        page_chunks = chunks_by_page.get(
            response.page_number,
            [],
        )

        if not page_chunks:
            raise ValueError(
                "No source text chunks found for "
                f"page {response.page_number}"
            )

        approval = SemanticApproval(
            request_id=response.request_id,
            decision=SemanticDecision.APPROVED,
            source=ApprovalSource.HUMAN,
            reviewer_id=reviewer_id,
            rationale=rationale,
            reviewed_at=reviewed_at,
        )

        approvals.append(approval)

        fused_records.append(
            fusion.fuse(
                source_chunks=page_chunks,
                verification=verification,
                semantic_approval=approval,
            )
        )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    reviewed_responses_path = (
        output_dir / "vision_responses_reviewed.json"
    )

    approvals_path = (
        output_dir / "semantic_approvals.json"
    )

    reviewed_payload = {
        "schema_version": "v1",
        "material_id": material_id,
        "material_name": material_name,
        "reviewed_at": reviewed_at.isoformat(),
        "reviewer_id": reviewer_id,
        "total_responses": len(
            corrected_responses
        ),
        "corrections": corrections,
        "responses": [
            response.model_dump(mode="json")
            for response in corrected_responses
        ],
    }

    approval_payload = {
        "schema_version": "v1",
        "material_id": material_id,
        "material_name": material_name,
        "total_approvals": len(approvals),
        "approvals": [
            approval.model_dump(mode="json")
            for approval in approvals
        ],
    }

    write_json_atomically(
        reviewed_responses_path,
        reviewed_payload,
    )

    write_json_atomically(
        approvals_path,
        approval_payload,
    )

    verified_kb_path = VerifiedKBExporter().export(
        records=fused_records,
        material_id=material_id,
        material_name=material_name,
        kb_version=kb_version,
        output_dir=output_dir,
    )

    return (
        reviewed_responses_path,
        approvals_path,
        verified_kb_path,
    )


def main() -> None:
    args = parse_arguments()

    (
        reviewed_responses_path,
        approvals_path,
        verified_kb_path,
    ) = build_verified_kb(
        pdf_path=args.pdf_path,
        requests_path=args.requests,
        responses_path=args.responses,
        output_dir=args.output_dir,
        reviewer_id=args.reviewer_id,
        rationale=args.rationale,
        kb_version=args.kb_version,
        exclusion_specs=(
            args.exclude_relationship
        ),
    )

    print()
    print("Verified KB build completed.")
    print(
        "Reviewed responses: "
        f"{reviewed_responses_path.resolve()}"
    )
    print(
        "Semantic approvals: "
        f"{approvals_path.resolve()}"
    )
    print(
        "Verified KB: "
        f"{verified_kb_path.resolve()}"
    )


if __name__ == "__main__":
    main()