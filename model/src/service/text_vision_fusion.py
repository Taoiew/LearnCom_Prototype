import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from difflib import SequenceMatcher

from schemas.fusion_contract import (
    FusedKnowledge,
    SemanticApproval,
    SemanticDecision,
)
from schemas.kb_contract import ReviewStatus
from schemas.vision_contract import VisionResponse
from src.evaluation.multimodal_verifier import (
    MultimodalVerificationResult,
)
from src.ingestion.pdf_ingestor import MaterialChunk


class TextVisionFusion:
    FUSION_VERSION = "fusion-v1"
    OCR_DUPLICATION_THRESHOLD = 0.95

    def fuse(
        self,
        source_chunks: list[MaterialChunk],
        verification: MultimodalVerificationResult,
        semantic_approval: SemanticApproval,
    ) -> FusedKnowledge:
        self._validate_verification(
            verification=verification,
        )

        response = verification.response

        self._validate_semantic_approval(
            response=response,
            semantic_approval=semantic_approval,
        )

        self._validate_source_chunks(
            source_chunks=source_chunks,
            response=response,
        )

        text_content = self._create_text_content(
            source_chunks=source_chunks,
        )

        visual_content = self._create_visual_content(
            response=response,
            text_content=text_content,
        )

        content = self._join_unique_sections(
            text_content,
            visual_content,
        )

        if not content:
            raise ValueError(
                "Fusion requires text or visual content"
            )

        knowledge_id = self._create_knowledge_id(
            response=response,
            source_chunks=source_chunks,
        )

        return FusedKnowledge(
            knowledge_id=knowledge_id,
            material_id=response.material_id,
            material_name=response.material_name,
            page_number=response.page_number,
            source_request_id=response.request_id,
            source_chunk_ids=sorted(
                chunk.chunk_id
                for chunk in source_chunks
            ),
            asset_ids=[response.asset_id],
            element_ids=sorted(
                element.element_id
                for element in response.visual_elements
            ),
            table_ids=sorted(
                table.table_id
                for table in response.tables
            ),
            text_content=text_content,
            visual_content=visual_content,
            content=content,
            confidence=self._calculate_confidence(
                response=response,
            ),
            review_status=ReviewStatus.VERIFIED,
            agent_model=response.agent_model,
            prompt_version=response.prompt_version,
            fusion_version=self.FUSION_VERSION,
            semantic_approval=semantic_approval,
            created_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _validate_verification(
        verification: MultimodalVerificationResult,
    ) -> None:
        if (
            not verification.is_verified
            or verification.review_status
            is not ReviewStatus.VERIFIED
        ):
            raise ValueError(
                "Fusion requires structurally verified "
                "multimodal evidence"
            )

    @staticmethod
    def _validate_semantic_approval(
        response: VisionResponse,
        semantic_approval: SemanticApproval,
    ) -> None:
        if (
            semantic_approval.request_id
            != response.request_id
        ):
            raise ValueError(
                "Semantic approval request_id does not "
                "match VisionResponse"
            )

        if (
            semantic_approval.decision
            is not SemanticDecision.APPROVED
        ):
            raise ValueError(
                "Fusion requires explicit semantic approval"
            )

    @staticmethod
    def _validate_source_chunks(
        source_chunks: list[MaterialChunk],
        response: VisionResponse,
    ) -> None:
        chunk_ids = [
            chunk.chunk_id
            for chunk in source_chunks
        ]

        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError(
                "Fusion source chunks contain duplicate "
                "chunk_id"
            )

        for chunk in source_chunks:
            if chunk.material_id != response.material_id:
                raise ValueError(
                    "Fusion source chunk material_id does "
                    "not match VisionResponse"
                )

            if chunk.page_number != response.page_number:
                raise ValueError(
                    "Fusion source chunk page_number does "
                    "not match VisionResponse"
                )

    @staticmethod
    def _create_text_content(
        source_chunks: list[MaterialChunk],
    ) -> str:
        ordered_chunks = sorted(
            source_chunks,
            key=lambda chunk: (
                chunk.chunk_index,
                chunk.chunk_id,
            ),
        )

        return " ".join(
            chunk.text.strip()
            for chunk in ordered_chunks
            if chunk.text.strip()
        ).strip()

    def _create_visual_content(
        self,
        response: VisionResponse,
        text_content: str,
    ) -> str:
        sections: list[str] = []

        self._append_unique(
            sections=sections,
            value=response.page_summary,
        )

        if (
            response.ocr_text.strip()
            and not self._is_duplicate_text(
                candidate=response.ocr_text,
                reference=text_content,
            )
        ):
            self._append_unique(
                sections=sections,
                value=response.ocr_text,
            )

        for element in sorted(
            response.visual_elements,
            key=lambda item: item.element_id,
        ):
            element_text = self._join_unique_sections(
                element.title,
                element.description,
                element.extracted_text,
            )

            self._append_unique(
                sections=sections,
                value=element_text,
            )

        for table in sorted(
            response.tables,
            key=lambda item: item.table_id,
        ):
            table_text = self._serialize_table(table)

            self._append_unique(
                sections=sections,
                value=table_text,
            )

        for relationship in response.relationships:
            relationship_text = (
                f"{relationship.source_element_id} "
                f"{relationship.relation.strip()} "
                f"{relationship.target_element_id}"
            )

            self._append_unique(
                sections=sections,
                value=relationship_text,
            )

        return "\n\n".join(sections).strip()

    @classmethod
    def _serialize_table(
        cls,
        table,
    ) -> str:
        sections: list[str] = []

        cls._append_unique(
            sections=sections,
            value=table.title,
        )

        if table.headers:
            sections.append(
                " | ".join(
                    header.strip()
                    for header in table.headers
                )
            )

        for row in table.rows:
            sections.append(
                " | ".join(
                    str(cell).strip()
                    for cell in row
                )
            )

        for note in table.notes:
            cls._append_unique(
                sections=sections,
                value=note,
            )

        return "\n".join(
            section
            for section in sections
            if section.strip()
        ).strip()

    @classmethod
    def _append_unique(
        cls,
        sections: list[str],
        value: str,
    ) -> None:
        cleaned = value.strip()

        if not cleaned:
            return

        normalized = cls._normalize_text(cleaned)

        if any(
            cls._normalize_text(existing) == normalized
            for existing in sections
        ):
            return

        sections.append(cleaned)

    @classmethod
    def _join_unique_sections(
        cls,
        *values: str,
    ) -> str:
        sections: list[str] = []

        for value in values:
            cls._append_unique(
                sections=sections,
                value=value,
            )

        return "\n\n".join(sections).strip()

    @classmethod
    def _is_duplicate_text(
        cls,
        candidate: str,
        reference: str,
    ) -> bool:
        normalized_candidate = cls._normalize_text(
            candidate
        )
        normalized_reference = cls._normalize_text(
            reference
        )

        if (
            not normalized_candidate
            or not normalized_reference
        ):
            return False

        similarity = SequenceMatcher(
            None,
            normalized_candidate,
            normalized_reference,
            autojunk=False,
        ).ratio()

        return (
            similarity
            >= cls.OCR_DUPLICATION_THRESHOLD
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

    @staticmethod
    def _calculate_confidence(
        response: VisionResponse,
    ) -> float:
        evidence_confidences = [
            element.confidence
            for element in response.visual_elements
        ]
        evidence_confidences.extend(
            table.confidence
            for table in response.tables
        )
        evidence_confidences.extend(
            relationship.confidence
            for relationship in response.relationships
        )

        if not evidence_confidences:
            return response.confidence

        return min(
            response.confidence,
            *evidence_confidences,
        )

    @classmethod
    def _create_knowledge_id(
        cls,
        response: VisionResponse,
        source_chunks: list[MaterialChunk],
    ) -> str:
        chunk_ids = ",".join(
            sorted(
                chunk.chunk_id
                for chunk in source_chunks
            )
        )

        source = (
            f"{response.material_id}:"
            f"{response.page_number}:"
            f"{response.request_id}:"
            f"{response.asset_id}:"
            f"{chunk_ids}:"
            f"{cls.FUSION_VERSION}"
        )

        digest = hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()[:16]

        return f"fused-{digest}"