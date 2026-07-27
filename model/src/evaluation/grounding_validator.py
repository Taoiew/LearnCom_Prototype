import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from difflib import SequenceMatcher

from schemas.vision_contract import (
    BoundingBoxSpace,
    VisionResponse,
)


@dataclass(frozen=True)
class GroundingValidationResult:
    rejection_reasons: list[str]
    review_reasons: list[str]

    @property
    def is_structurally_valid(self) -> bool:
        return not self.rejection_reasons

    @property
    def requires_review(self) -> bool:
        return bool(self.review_reasons)


class GroundingValidator:
    BOUNDING_BOX_PIXEL_TOLERANCE = 32
    BOUNDING_BOX_RELATIVE_TOLERANCE = 0.05

    def __init__(
        self,
        minimum_evidence_confidence: float = 0.70,
        ocr_echo_similarity_threshold: float = 0.95,
    ) -> None:
        if not 0 <= minimum_evidence_confidence <= 1:
            raise ValueError(
                "minimum_evidence_confidence must be "
                "between 0 and 1"
            )

        if not 0 <= ocr_echo_similarity_threshold <= 1:
            raise ValueError(
                "ocr_echo_similarity_threshold must be "
                "between 0 and 1"
            )

        self.minimum_evidence_confidence = (
            minimum_evidence_confidence
        )
        self.ocr_echo_similarity_threshold = (
            ocr_echo_similarity_threshold
        )

    def validate(
        self,
        response: VisionResponse,
        image_width_pixels: int | None = None,
        image_height_pixels: int | None = None,
        source_extracted_text: str = "",
    ) -> GroundingValidationResult:
        rejection_reasons: list[str] = []
        review_reasons: list[str] = []

        self._validate_image_dimensions(
            image_width_pixels=image_width_pixels,
            image_height_pixels=image_height_pixels,
        )

        self._check_duplicate_element_ids(
            response=response,
            reasons=rejection_reasons,
        )
        self._check_duplicate_table_ids(
            response=response,
            reasons=rejection_reasons,
        )
        self._check_relationship_references(
            response=response,
            reasons=rejection_reasons,
        )
        self._check_bounding_box_bounds(
            response=response,
            image_width_pixels=image_width_pixels,
            image_height_pixels=image_height_pixels,
            reasons=rejection_reasons,
        )
        self._check_ocr_grounding(
            response=response,
            source_extracted_text=source_extracted_text,
            reasons=review_reasons,
        )
        self._check_evidence_confidence(
            response=response,
            reasons=review_reasons,
        )

        return GroundingValidationResult(
            rejection_reasons=rejection_reasons,
            review_reasons=review_reasons,
        )

    @staticmethod
    def _validate_image_dimensions(
        image_width_pixels: int | None,
        image_height_pixels: int | None,
    ) -> None:
        width_missing = image_width_pixels is None
        height_missing = image_height_pixels is None

        if width_missing != height_missing:
            raise ValueError(
                "image_width_pixels and "
                "image_height_pixels must be supplied together"
            )

        if (
            image_width_pixels is not None
            and image_width_pixels <= 0
        ):
            raise ValueError(
                "image_width_pixels must be greater than zero"
            )

        if (
            image_height_pixels is not None
            and image_height_pixels <= 0
        ):
            raise ValueError(
                "image_height_pixels must be greater than zero"
            )

    @staticmethod
    def _check_duplicate_element_ids(
        response: VisionResponse,
        reasons: list[str],
    ) -> None:
        counts = Counter(
            element.element_id
            for element in response.visual_elements
        )

        duplicate_ids = sorted(
            element_id
            for element_id, count in counts.items()
            if count > 1
        )

        for element_id in duplicate_ids:
            reasons.append(
                "Duplicate visual element_id: "
                f"{element_id}"
            )

    @staticmethod
    def _check_duplicate_table_ids(
        response: VisionResponse,
        reasons: list[str],
    ) -> None:
        counts = Counter(
            table.table_id
            for table in response.tables
        )

        duplicate_ids = sorted(
            table_id
            for table_id, count in counts.items()
            if count > 1
        )

        for table_id in duplicate_ids:
            reasons.append(
                f"Duplicate table_id: {table_id}"
            )

    @staticmethod
    def _check_relationship_references(
        response: VisionResponse,
        reasons: list[str],
    ) -> None:
        evidence_ids = {
            element.element_id
            for element in response.visual_elements
        }
        evidence_ids.update(
            table.table_id
            for table in response.tables
        )

        for index, relationship in enumerate(
            response.relationships
        ):
            relationship_number = index + 1

            if (
                relationship.source_element_id
                not in evidence_ids
            ):
                reasons.append(
                    "Relationship "
                    f"{relationship_number} references "
                    "unknown source_element_id: "
                    f"{relationship.source_element_id}"
                )

            if (
                relationship.target_element_id
                not in evidence_ids
            ):
                reasons.append(
                    "Relationship "
                    f"{relationship_number} references "
                    "unknown target_element_id: "
                    f"{relationship.target_element_id}"
                )

            if not relationship.relation.strip():
                reasons.append(
                    "Relationship "
                    f"{relationship_number} has empty relation"
                )

    @staticmethod
    def _check_bounding_box_bounds(
        response: VisionResponse,
        image_width_pixels: int | None,
        image_height_pixels: int | None,
        reasons: list[str],
    ) -> None:
        if (
            image_width_pixels is None
            or image_height_pixels is None
        ):
            return

        for element in response.visual_elements:
            bounding_box = element.bounding_box

            if (
                bounding_box is None
                or element.bounding_box_space
                is BoundingBoxSpace.NORMALIZED
            ):
                continue

            _, _, x2, y2 = bounding_box

            if x2 > GroundingValidator._max_allowed_bound(
                image_width_pixels
            ):
                reasons.append(
                    "Visual element bounding_box exceeds "
                    "image width: "
                    f"{element.element_id}"
                )

            if y2 > GroundingValidator._max_allowed_bound(
                image_height_pixels
            ):
                reasons.append(
                    "Visual element bounding_box exceeds "
                    "image height: "
                    f"{element.element_id}"
                )

        for table in response.tables:
            bounding_box = table.bounding_box

            if (
                bounding_box is None
                or table.bounding_box_space
                is BoundingBoxSpace.NORMALIZED
            ):
                continue

            _, _, x2, y2 = bounding_box

            if x2 > GroundingValidator._max_allowed_bound(
                image_width_pixels
            ):
                reasons.append(
                    "Table bounding_box exceeds image width: "
                    f"{table.table_id}"
                )

            if y2 > GroundingValidator._max_allowed_bound(
                image_height_pixels
            ):
                reasons.append(
                    "Table bounding_box exceeds image height: "
                    f"{table.table_id}"
                )

    @staticmethod
    def _max_allowed_bound(
        image_pixels: int,
    ) -> float:
        return image_pixels + max(
            GroundingValidator.BOUNDING_BOX_PIXEL_TOLERANCE,
            image_pixels
            * GroundingValidator.BOUNDING_BOX_RELATIVE_TOLERANCE,
        )

    def _check_ocr_grounding(
        self,
        response: VisionResponse,
        source_extracted_text: str,
        reasons: list[str],
    ) -> None:
        normalized_ocr = self._normalize_text(
            response.ocr_text
        )
        normalized_source = self._normalize_text(
            source_extracted_text
        )

        if not normalized_ocr or not normalized_source:
            return

        has_non_ocr_visual_evidence = bool(
            response.visual_elements
            or response.tables
            or response.relationships
        )

        if has_non_ocr_visual_evidence:
            return

        similarity = SequenceMatcher(
            None,
            normalized_ocr,
            normalized_source,
            autojunk=False,
        ).ratio()

        if (
            similarity
            >= self.ocr_echo_similarity_threshold
        ):
            reasons.append(
                "OCR text substantially duplicates the "
                "source text layer and provides no "
                "independent visual evidence"
            )

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize(
            "NFKC",
            text,
        )
        normalized = normalized.casefold()
        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        return normalized.strip()

    def _check_evidence_confidence(
        self,
        response: VisionResponse,
        reasons: list[str],
    ) -> None:
        threshold = self.minimum_evidence_confidence

        low_element_ids = sorted(
            element.element_id
            for element in response.visual_elements
            if element.confidence < threshold
        )

        if low_element_ids:
            reasons.append(
                "Visual evidence confidence is below "
                f"{threshold:.2f}: "
                + ", ".join(low_element_ids)
            )

        low_table_ids = sorted(
            table.table_id
            for table in response.tables
            if table.confidence < threshold
        )

        if low_table_ids:
            reasons.append(
                "Table evidence confidence is below "
                f"{threshold:.2f}: "
                + ", ".join(low_table_ids)
            )

        low_relationship_numbers = [
            str(index + 1)
            for index, relationship in enumerate(
                response.relationships
            )
            if relationship.confidence < threshold
        ]

        if low_relationship_numbers:
            reasons.append(
                "Relationship evidence confidence is below "
                f"{threshold:.2f} at positions: "
                + ", ".join(low_relationship_numbers)
            )
