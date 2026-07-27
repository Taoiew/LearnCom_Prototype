import hashlib
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
import json

from schemas.material_contract import (
    MaterialFileType,
    MaterialUploadResponse,
    MaterialUploadStatus,
)


class MaterialStorageError(ValueError):
    pass


@dataclass(frozen=True)
class DetectedMaterialType:
    file_type: MaterialFileType
    mime_type: str
    extension: str


class MaterialStorage:
    DEFAULT_MAX_FILE_BYTES = 20 * 1024 * 1024

    _ALLOWED_CONTENT_TYPES = {
        "application/pdf": DetectedMaterialType(
            file_type=MaterialFileType.PDF,
            mime_type="application/pdf",
            extension=".pdf",
        ),
        "image/png": DetectedMaterialType(
            file_type=MaterialFileType.PNG,
            mime_type="image/png",
            extension=".png",
        ),
        "image/jpeg": DetectedMaterialType(
            file_type=MaterialFileType.JPEG,
            mime_type="image/jpeg",
            extension=".jpg",
        ),
    }

    def __init__(
        self,
        storage_root: str | Path,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    ) -> None:
        if max_file_bytes <= 0:
            raise ValueError(
                "max_file_bytes must be greater than zero"
            )

        self.storage_root = Path(storage_root)
        self.max_file_bytes = max_file_bytes

    def store(
        self,
        *,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> MaterialUploadResponse:
        if not filename.strip():
            raise MaterialStorageError(
                "Upload filename must not be empty"
            )

        if not content:
            raise MaterialStorageError(
                "Uploaded material must not be empty"
            )

        if len(content) > self.max_file_bytes:
            raise MaterialStorageError(
                "Uploaded material exceeds maximum size of "
                f"{self.max_file_bytes} bytes"
            )

        normalized_content_type = (
            content_type
            .split(";", maxsplit=1)[0]
            .strip()
            .lower()
        )

        declared_type = self._ALLOWED_CONTENT_TYPES.get(
            normalized_content_type
        )

        if declared_type is None:
            raise MaterialStorageError(
                "Unsupported material content type: "
                f"{normalized_content_type or 'missing'}"
            )

        detected_type = self._detect_file_type(content)

        if detected_type.file_type is not declared_type.file_type:
            raise MaterialStorageError(
                "Uploaded file content does not match "
                "the declared content type"
            )

        original_filename = Path(
            filename.replace("\\", "/")
        ).name

        safe_stem = self._sanitize_stem(
            Path(original_filename).stem
        )

        content_sha256 = hashlib.sha256(
            content
        ).hexdigest()

        material_id = (
            f"material-{content_sha256[:16]}"
        )

        stored_filename = (
            f"{safe_stem}-{content_sha256[:12]}"
            f"{detected_type.extension}"
        )

        material_directory = (
            self.storage_root / material_id
        )
        material_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        destination = (
            material_directory / stored_filename
        )

        self._write_atomically(
            destination=destination,
            content=content,
        )

        response = MaterialUploadResponse(
            material_id=material_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            stored_path=str(destination.resolve()),
            file_type=detected_type.file_type,
            mime_type=detected_type.mime_type,
            size_bytes=len(content),
            sha256=content_sha256,
            status=MaterialUploadStatus.STORED,
        )

        metadata_path = material_directory / "metadata.json"

        metadata_content = (
            response.model_dump_json(indent=2)
            .encode("utf-8")
        )

        self._write_atomically(
            destination=metadata_path,
            content=metadata_content,
        )

        return response

    def get(
        self,
        material_id: str,
    ) -> MaterialUploadResponse:
        normalized_id = material_id.strip()

        if not re.fullmatch(
            r"material-[0-9a-f]{16}",
            normalized_id,
        ):
            raise MaterialStorageError(
                "Invalid material_id"
            )

        metadata_path = (
            self.storage_root
            / normalized_id
            / "metadata.json"
        )

        if not metadata_path.is_file():
            raise MaterialStorageError(
                f"Stored material not found: {normalized_id}"
            )

        try:
            response = (
                MaterialUploadResponse.model_validate_json(
                    metadata_path.read_text(
                        encoding="utf-8",
                    )
                )
            )
        except Exception as exc:
            raise MaterialStorageError(
                "Stored material metadata is invalid"
            ) from exc

        if response.material_id != normalized_id:
            raise MaterialStorageError(
                "Stored material metadata does not "
                "match material_id"
            )

        stored_path = Path(response.stored_path)

        if not stored_path.is_file():
            raise MaterialStorageError(
                "Stored material file is missing"
            )

        content = stored_path.read_bytes()
        actual_sha256 = hashlib.sha256(
            content
        ).hexdigest()

        if actual_sha256 != response.sha256:
            raise MaterialStorageError(
                "Stored material checksum mismatch"
            )

        if len(content) != response.size_bytes:
            raise MaterialStorageError(
                "Stored material size mismatch"
            )

        return response

    @staticmethod
    def _detect_file_type(
        content: bytes,
    ) -> DetectedMaterialType:
        if content.startswith(b"%PDF-"):
            return DetectedMaterialType(
                file_type=MaterialFileType.PDF,
                mime_type="application/pdf",
                extension=".pdf",
            )

        if content.startswith(
            b"\x89PNG\r\n\x1a\n"
        ):
            return DetectedMaterialType(
                file_type=MaterialFileType.PNG,
                mime_type="image/png",
                extension=".png",
            )

        if content.startswith(b"\xff\xd8\xff"):
            return DetectedMaterialType(
                file_type=MaterialFileType.JPEG,
                mime_type="image/jpeg",
                extension=".jpg",
            )

        raise MaterialStorageError(
            "Uploaded material is not a valid "
            "PDF, PNG, or JPEG file"
        )

    @staticmethod
    def _sanitize_stem(stem: str) -> str:
        sanitized = re.sub(
            r"[^a-zA-Z0-9._-]+",
            "-",
            stem.strip(),
        )
        sanitized = sanitized.strip(".-_")

        if not sanitized:
            return "material"

        return sanitized[:80]

    @staticmethod
    def _write_atomically(
        *,
        destination: Path,
        content: bytes,
    ) -> None:
        if destination.exists():
            if destination.read_bytes() != content:
                raise MaterialStorageError(
                    "Stored material path already exists "
                    "with different content"
                )

            return

        temporary_path = destination.with_name(
            f".{destination.name}.{uuid.uuid4().hex}.tmp"
        )

        try:
            with temporary_path.open("xb") as file:
                file.write(content)
                file.flush()
                os.fsync(file.fileno())

            temporary_path.replace(destination)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()