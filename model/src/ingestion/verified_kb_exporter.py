import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from schemas.fusion_contract import FusedKnowledge
from schemas.kb_contract import ReviewStatus


class VerifiedKBExporter:
    SCHEMA_VERSION = "v1"
    FILE_NAME = "verified_kb.json"

    def export(
        self,
        records: list[FusedKnowledge],
        material_id: str,
        material_name: str,
        kb_version: str,
        output_dir: str | Path,
    ) -> Path:
        material_id = material_id.strip()
        material_name = material_name.strip()
        kb_version = kb_version.strip()

        if not material_id:
            raise ValueError(
                "material_id must not be empty"
            )

        if not material_name:
            raise ValueError(
                "material_name must not be empty"
            )

        if not kb_version:
            raise ValueError(
                "kb_version must not be empty"
            )

        self._validate_records(
            records=records,
            material_id=material_id,
            material_name=material_name,
        )

        ordered_records = sorted(
            records,
            key=lambda record: (
                record.page_number,
                record.knowledge_id,
            ),
        )

        serialized_records = [
            record.model_dump(mode="json")
            for record in ordered_records
        ]

        content_sha256 = self._create_content_hash(
            records=serialized_records,
        )

        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "kb_version": kb_version,
            "material_id": material_id,
            "material_name": material_name,
            "generated_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "total_records": len(serialized_records),
            "content_sha256": content_sha256,
            "records": serialized_records,
        }

        export_dir = Path(output_dir)
        export_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = export_dir / self.FILE_NAME

        self._write_json_atomically(
            output_path=output_path,
            payload=payload,
        )

        return output_path

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
            raise ValueError(
                "Verified KB contains duplicate knowledge_id"
            )

        for record in records:
            if record.material_id != material_id:
                raise ValueError(
                    "Verified KB record material_id does "
                    "not match export material_id"
                )

            if record.material_name != material_name:
                raise ValueError(
                    "Verified KB record material_name does "
                    "not match export material_name"
                )

            if (
                record.review_status
                is not ReviewStatus.VERIFIED
            ):
                raise ValueError(
                    "Verified KB accepts only verified records"
                )

    @staticmethod
    def _create_content_hash(
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
    def _write_json_atomically(
        output_path: Path,
        payload: dict,
    ) -> None:
        temporary_path: Path | None = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=output_path.parent,
                prefix=".verified-kb-",
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