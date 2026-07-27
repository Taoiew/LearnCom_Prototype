from dataclasses import dataclass

from schemas.kb_contract import EnrichedKnowledge, ReviewStatus
from src.ingestion.pdf_ingestor import MaterialChunk


@dataclass(frozen=True)
class VerificationResult:
    knowledge: EnrichedKnowledge
    is_verified: bool
    reasons: list[str]


class KBVerifier:
    def verify(
        self,
        knowledge: EnrichedKnowledge,
        source_chunks: list[MaterialChunk],
    ) -> VerificationResult:
        reasons: list[str] = []

        matching_chunks = [
            chunk
            for chunk in source_chunks
            if chunk.chunk_id in knowledge.source_chunk_ids
        ]

        if not matching_chunks:
            reasons.append("ไม่พบ source chunk ที่ Agent อ้างอิง")

        if any(
            chunk.material_id != knowledge.material_id
            for chunk in matching_chunks
        ):
            reasons.append("material_id ไม่ตรงกับ Source KB")

        source_pages = {chunk.page_number for chunk in matching_chunks}

        if not set(knowledge.page_numbers).issubset(source_pages):
            reasons.append("เลขหน้าไม่ตรงกับ Source KB")

        source_text = " ".join(chunk.text for chunk in matching_chunks)

        if knowledge.source_quote not in source_text:
            reasons.append("ไม่พบ source_quote ใน Material ต้นฉบับ")

        is_verified = len(reasons) == 0

        verified_knowledge = knowledge.model_copy(
            update={
                "review_status": (
                    ReviewStatus.VERIFIED
                    if is_verified
                    else ReviewStatus.REJECTED
                )
            }
        )

        return VerificationResult(
            knowledge=verified_knowledge,
            is_verified=is_verified,
            reasons=reasons,
        )