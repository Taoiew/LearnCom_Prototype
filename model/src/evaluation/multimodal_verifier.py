from collections import Counter
from dataclasses import dataclass

from schemas.kb_contract import ReviewStatus
from schemas.vision_contract import (
    VisionRequest,
    VisionResponse,
    VisionResponseStatus,
)


@dataclass(frozen=True)
class MultimodalVerificationResult:
    response: VisionResponse
    review_status: ReviewStatus
    is_verified: bool
    reasons: list[str]


@dataclass(frozen=True)
class MultimodalBatchIssue:
    request_id: str
    review_status: ReviewStatus
    reasons: list[str]


@dataclass(frozen=True)
class MultimodalVerificationBatch:
    results: list[MultimodalVerificationResult]
    issues: list[MultimodalBatchIssue]

    @property
    def verified_count(self) -> int:
        return sum(
            1
            for result in self.results
            if result.review_status is ReviewStatus.VERIFIED
        )

    @property
    def needs_review_count(self) -> int:
        return sum(
            1
            for result in self.results
            if result.review_status is ReviewStatus.NEEDS_REVIEW
        )

    @property
    def rejected_count(self) -> int:
        rejected_results = sum(
            1
            for result in self.results
            if result.review_status is ReviewStatus.REJECTED
        )
        rejected_issues = sum(
            1
            for issue in self.issues
            if issue.review_status is ReviewStatus.REJECTED
        )

        return rejected_results + rejected_issues


class MultimodalVerifier:
    def __init__(
        self,
        minimum_confidence: float = 0.80,
    ) -> None:
        if not 0 <= minimum_confidence <= 1:
            raise ValueError(
                "minimum_confidence must be between 0 and 1"
            )

        self.minimum_confidence = minimum_confidence

    def verify(
        self,
        request: VisionRequest,
        response: VisionResponse,
    ) -> MultimodalVerificationResult:
        rejection_reasons: list[str] = []
        review_reasons: list[str] = []

        self._check_source_links(
            request=request,
            response=response,
            reasons=rejection_reasons,
        )

        if response.status is VisionResponseStatus.FAILED:
            rejection_reasons.append(
                "Multimodal agent returned failed status"
            )

        if response.status is VisionResponseStatus.PARTIAL:
            review_reasons.append(
                "Multimodal response is only partially complete"
            )

        if (
            response.status
            is VisionResponseStatus.NEEDS_REVIEW
        ):
            review_reasons.append(
                "Multimodal agent requested manual review"
            )

        if response.confidence < self.minimum_confidence:
            review_reasons.append(
                "Response confidence is below "
                f"{self.minimum_confidence:.2f}"
            )

        if response.agent_model == "demo-multimodal-agent":
            review_reasons.append(
                "Demo multimodal output cannot be verified"
            )

        if not self._has_structured_evidence(response):
            review_reasons.append(
                "Response contains no structured visual evidence"
            )

        if response.warnings:
            review_reasons.append(
                "Response contains multimodal warnings"
            )

        if rejection_reasons:
            review_status = ReviewStatus.REJECTED
            reasons = rejection_reasons + review_reasons
        elif review_reasons:
            review_status = ReviewStatus.NEEDS_REVIEW
            reasons = review_reasons
        else:
            review_status = ReviewStatus.VERIFIED
            reasons = []

        return MultimodalVerificationResult(
            response=response,
            review_status=review_status,
            is_verified=(
                review_status is ReviewStatus.VERIFIED
            ),
            reasons=reasons,
        )

    def verify_batch(
        self,
        requests: list[VisionRequest],
        responses: list[VisionResponse],
    ) -> MultimodalVerificationBatch:
        request_counts = Counter(
            request.request_id
            for request in requests
        )
        response_counts = Counter(
            response.request_id
            for response in responses
        )

        request_by_id = {
            request.request_id: request
            for request in requests
            if request_counts[request.request_id] == 1
        }
        response_by_id = {
            response.request_id: response
            for response in responses
            if response_counts[response.request_id] == 1
        }

        issues: list[MultimodalBatchIssue] = []

        for request_id, count in sorted(
            request_counts.items()
        ):
            if count > 1:
                issues.append(
                    MultimodalBatchIssue(
                        request_id=request_id,
                        review_status=ReviewStatus.REJECTED,
                        reasons=[
                            (
                                "Duplicate VisionRequest "
                                "request_id"
                            )
                        ],
                    )
                )

        for request_id, count in sorted(
            response_counts.items()
        ):
            if count > 1:
                issues.append(
                    MultimodalBatchIssue(
                        request_id=request_id,
                        review_status=ReviewStatus.REJECTED,
                        reasons=[
                            (
                                "Duplicate VisionResponse "
                                "request_id"
                            )
                        ],
                    )
                )

        for request_id in sorted(request_by_id):
            if request_id not in response_by_id:
                issues.append(
                    MultimodalBatchIssue(
                        request_id=request_id,
                        review_status=ReviewStatus.REJECTED,
                        reasons=[
                            (
                                "Missing VisionResponse for "
                                "VisionRequest"
                            )
                        ],
                    )
                )

        for request_id in sorted(response_by_id):
            if request_id not in request_by_id:
                issues.append(
                    MultimodalBatchIssue(
                        request_id=request_id,
                        review_status=ReviewStatus.REJECTED,
                        reasons=[
                            (
                                "VisionResponse has no matching "
                                "VisionRequest"
                            )
                        ],
                    )
                )

        results = [
            self.verify(
                request=request_by_id[request_id],
                response=response_by_id[request_id],
            )
            for request_id in sorted(
                set(request_by_id) & set(response_by_id)
            )
        ]

        return MultimodalVerificationBatch(
            results=results,
            issues=issues,
        )

    @staticmethod
    def _check_source_links(
        request: VisionRequest,
        response: VisionResponse,
        reasons: list[str],
    ) -> None:
        if response.request_id != request.request_id:
            reasons.append(
                "response request_id does not match request"
            )

        if response.material_id != request.material_id:
            reasons.append(
                "response material_id does not match request"
            )

        if response.material_name != request.material_name:
            reasons.append(
                "response material_name does not match request"
            )

        if response.page_number != request.page_number:
            reasons.append(
                "response page_number does not match request"
            )

        if response.asset_id != request.asset_id:
            reasons.append(
                "response asset_id does not match request"
            )

        if response.prompt_version != request.prompt_version:
            reasons.append(
                "response prompt_version does not match request"
            )

    @staticmethod
    def _has_structured_evidence(
        response: VisionResponse,
    ) -> bool:
        return bool(
            response.visual_elements
            or response.tables
            or response.relationships
            or response.ocr_text.strip()
        )
