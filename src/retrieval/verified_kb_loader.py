import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from schemas.fusion_contract import FusedKnowledge
from src.ingestion.pdf_ingestor import (
    ChunkType,
    MaterialChunk,
    SourceType,
)


class VerifiedKBLoadError(ValueError):
    """Raised when a Verified KB artifact is invalid."""


@dataclass(frozen=True)
class LoadedVerifiedKB:
    schema_version: str
    kb_version: str

    material_id: str
    material_name: str

    generated_at: datetime
    content_sha256: str

    records: tuple[FusedKnowledge, ...]

    def to_material_chunks(
        self,
    ) -> list[MaterialChunk]:
        chunks: list[MaterialChunk] = []

        ordered_records = sorted(
            self.records,
            key=lambda record: (
                record.page_number,
                record.knowledge_id,
            ),
        )

        for chunk_index, record in enumerate(
            ordered_records
        ):
            has_text = bool(record.text_content.strip())
            has_visual = bool(
                record.visual_content.strip()
            )

            if has_visual:
                chunk_type = ChunkType.MIXED
            else:
                chunk_type = ChunkType.TEXT

            if has_text and has_visual:
                source_type = SourceType.MIXED
            elif has_visual:
                source_type = SourceType.VISION
            else:
                source_type = SourceType.TEXT_LAYER

            chunks.append(
                MaterialChunk(
                    chunk_id=record.knowledge_id,
                    material_id=record.material_id,
                    material_name=record.material_name,
                    page_number=record.page_number,
                    chunk_index=chunk_index,
                    text=record.content,
                    chunk_type=chunk_type,
                    source_type=source_type,
                    image_ids=tuple(record.asset_ids),
                    source_chunk_ids=tuple(
                        record.source_chunk_ids
                    ),
                )
            )

        return chunks


class VerifiedKBLoader:
    SUPPORTED_SCHEMA_VERSION = "v1"

    def load(
        self,
        verified_kb_path: str | Path,
    ) -> LoadedVerifiedKB:
        path = Path(verified_kb_path)

        if not path.is_file():
            raise FileNotFoundError(
                f"Verified KB not found: {path}"
            )

        payload = self._read_payload(path)

        self._validate_top_level_payload(payload)
        self._validate_content_hash(payload)

        records = self._parse_records(
            raw_records=payload["records"],
        )

        self._validate_records(
            records=records,
            material_id=payload["material_id"],
            material_name=payload["material_name"],
        )

        generated_at = self._parse_generated_at(
            payload["generated_at"]
        )

        return LoadedVerifiedKB(
            schema_version=payload["schema_version"],
            kb_version=payload["kb_version"],
            material_id=payload["material_id"],
            material_name=payload["material_name"],
            generated_at=generated_at,
            content_sha256=payload["content_sha256"],
            records=tuple(records),
        )

    @staticmethod
    def _read_payload(path: Path) -> dict:
        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                payload = json.load(file)
        except json.JSONDecodeError as error:
            raise VerifiedKBLoadError(
                "Verified KB contains invalid JSON"
            ) from error

        if not isinstance(payload, dict):
            raise VerifiedKBLoadError(
                "Verified KB root must be a JSON object"
            )

        return payload

    def _validate_top_level_payload(
        self,
        payload: dict,
    ) -> None:
        required_fields = {
            "schema_version",
            "kb_version",
            "material_id",
            "material_name",
            "generated_at",
            "total_records",
            "content_sha256",
            "records",
        }

        missing_fields = sorted(
            required_fields - payload.keys()
        )

        if missing_fields:
            raise VerifiedKBLoadError(
                "Verified KB is missing required fields: "
                + ", ".join(missing_fields)
            )

        if (
            payload["schema_version"]
            != self.SUPPORTED_SCHEMA_VERSION
        ):
            raise VerifiedKBLoadError(
                "Unsupported Verified KB schema_version: "
                f"{payload['schema_version']}"
            )

        for field_name in (
            "kb_version",
            "material_id",
            "material_name",
            "generated_at",
            "content_sha256",
        ):
            value = payload[field_name]

            if (
                not isinstance(value, str)
                or not value.strip()
            ):
                raise VerifiedKBLoadError(
                    f"{field_name} must be a non-empty string"
                )

        records = payload["records"]

        if not isinstance(records, list):
            raise VerifiedKBLoadError(
                "Verified KB records must be a list"
            )

        total_records = payload["total_records"]

        if (
            not isinstance(total_records, int)
            or isinstance(total_records, bool)
            or total_records < 0
        ):
            raise VerifiedKBLoadError(
                "total_records must be a "
                "non-negative integer"
            )

        if total_records != len(records):
            raise VerifiedKBLoadError(
                "total_records does not match "
                "the number of records"
            )

        content_sha256 = payload["content_sha256"]

        if (
            len(content_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in content_sha256.lower()
            )
        ):
            raise VerifiedKBLoadError(
                "content_sha256 must be a valid "
                "SHA-256 hexadecimal digest"
            )

    @staticmethod
    def _validate_content_hash(
        payload: dict,
    ) -> None:
        actual_hash = VerifiedKBLoader.create_content_hash(
            payload["records"]
        )

        expected_hash = payload[
            "content_sha256"
        ].lower()

        if actual_hash != expected_hash:
            raise VerifiedKBLoadError(
                "Verified KB content_sha256 mismatch"
            )

    @staticmethod
    def create_content_hash(
        records: list[dict],
    ) -> str:
        canonical_json = json.dumps(
            records,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            canonical_json.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _parse_records(
        raw_records: list,
    ) -> list[FusedKnowledge]:
        records: list[FusedKnowledge] = []

        for index, raw_record in enumerate(
            raw_records
        ):
            if not isinstance(raw_record, dict):
                raise VerifiedKBLoadError(
                    "Verified KB record "
                    f"{index + 1} must be an object"
                )

            try:
                record = FusedKnowledge.model_validate(
                    raw_record
                )
            except ValidationError as error:
                raise VerifiedKBLoadError(
                    "Verified KB record "
                    f"{index + 1} failed validation: "
                    f"{error}"
                ) from error

            records.append(record)

        return records

    @staticmethod
    def _validate_records(
        records: list[FusedKnowledge],
        material_id: str,
        material_name: str,
    ) -> None:
        knowledge_ids = [
            record.knowledge_id
            for record in records
        ]

        if len(knowledge_ids) != len(set(knowledge_ids)):
            raise VerifiedKBLoadError(
                "Verified KB contains duplicate knowledge_id"
            )

        for record in records:
            if record.material_id != material_id:
                raise VerifiedKBLoadError(
                    "Verified KB record material_id does "
                    "not match manifest material_id"
                )

            if record.material_name != material_name:
                raise VerifiedKBLoadError(
                    "Verified KB record material_name does "
                    "not match manifest material_name"
                )

    @staticmethod
    def _parse_generated_at(
        value: str,
    ) -> datetime:
        normalized_value = value.replace(
            "Z",
            "+00:00",
        )

        try:
            generated_at = datetime.fromisoformat(
                normalized_value
            )
        except ValueError as error:
            raise VerifiedKBLoadError(
                "generated_at must be a valid "
                "ISO-8601 datetime"
            ) from error

        if generated_at.tzinfo is None:
            raise VerifiedKBLoadError(
                "generated_at must include timezone information"
            )

        return generated_at