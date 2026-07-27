from pathlib import Path

import pytest

from schemas.material_contract import (
    MaterialFileType,
    MaterialUploadStatus,
)
from src.ingestion.material_storage import (
    MaterialStorage,
    MaterialStorageError,
)


PDF_CONTENT = (
    b"%PDF-1.7\n"
    b"1 0 obj\n"
    b"<< /Type /Catalog >>\n"
    b"endobj\n"
    b"%%EOF\n"
)

PNG_CONTENT = (
    b"\x89PNG\r\n\x1a\n"
    b"prototype-png-content"
)

JPEG_CONTENT = (
    b"\xff\xd8\xff\xe0"
    b"prototype-jpeg-content"
    b"\xff\xd9"
)


def test_store_pdf_material(
    tmp_path: Path,
) -> None:
    storage = MaterialStorage(tmp_path)

    result = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=PDF_CONTENT,
    )

    stored_path = Path(result.stored_path)

    assert result.material_id.startswith("material-")
    assert result.original_filename == "lesson.pdf"
    assert result.file_type is MaterialFileType.PDF
    assert result.mime_type == "application/pdf"
    assert result.size_bytes == len(PDF_CONTENT)
    assert len(result.sha256) == 64
    assert result.status is MaterialUploadStatus.STORED
    assert stored_path.is_file()
    assert stored_path.read_bytes() == PDF_CONTENT


@pytest.mark.parametrize(
    (
        "filename",
        "content_type",
        "content",
        "expected_type",
        "expected_suffix",
    ),
    [
        (
            "diagram.png",
            "image/png",
            PNG_CONTENT,
            MaterialFileType.PNG,
            ".png",
        ),
        (
            "photo.jpeg",
            "image/jpeg",
            JPEG_CONTENT,
            MaterialFileType.JPEG,
            ".jpg",
        ),
    ],
)
def test_store_image_material(
    tmp_path: Path,
    filename: str,
    content_type: str,
    content: bytes,
    expected_type: MaterialFileType,
    expected_suffix: str,
) -> None:
    result = MaterialStorage(tmp_path).store(
        filename=filename,
        content_type=content_type,
        content=content,
    )

    assert result.file_type is expected_type
    assert result.stored_filename.endswith(
        expected_suffix
    )
    assert Path(result.stored_path).read_bytes() == content


def test_store_removes_path_traversal(
    tmp_path: Path,
) -> None:
    result = MaterialStorage(tmp_path).store(
        filename="../../private/lesson.pdf",
        content_type="application/pdf",
        content=PDF_CONTENT,
    )

    stored_path = Path(result.stored_path)

    assert result.original_filename == "lesson.pdf"
    assert stored_path.is_relative_to(
        tmp_path.resolve()
    )


def test_store_is_idempotent_for_same_content(
    tmp_path: Path,
) -> None:
    storage = MaterialStorage(tmp_path)

    first = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=PDF_CONTENT,
    )
    second = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=PDF_CONTENT,
    )

    assert first.material_id == second.material_id
    assert first.sha256 == second.sha256
    assert first.stored_path == second.stored_path


def test_store_rejects_empty_content(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        MaterialStorageError,
        match="must not be empty",
    ):
        MaterialStorage(tmp_path).store(
            filename="lesson.pdf",
            content_type="application/pdf",
            content=b"",
        )


def test_store_rejects_unsupported_content_type(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        MaterialStorageError,
        match="Unsupported material content type",
    ):
        MaterialStorage(tmp_path).store(
            filename="notes.txt",
            content_type="text/plain",
            content=b"plain text",
        )


def test_store_rejects_mismatched_content_type(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        MaterialStorageError,
        match="does not match",
    ):
        MaterialStorage(tmp_path).store(
            filename="fake.pdf",
            content_type="application/pdf",
            content=PNG_CONTENT,
        )


def test_store_rejects_oversized_material(
    tmp_path: Path,
) -> None:
    storage = MaterialStorage(
        tmp_path,
        max_file_bytes=10,
    )

    with pytest.raises(
        MaterialStorageError,
        match="exceeds maximum size",
    ):
        storage.store(
            filename="lesson.pdf",
            content_type="application/pdf",
            content=PDF_CONTENT,
        )

def test_get_returns_stored_material(
    tmp_path: Path,
) -> None:
    storage = MaterialStorage(tmp_path)

    stored = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=PDF_CONTENT,
    )

    loaded = storage.get(stored.material_id)

    assert loaded == stored
    assert Path(loaded.stored_path).is_file()


def test_store_writes_metadata(
    tmp_path: Path,
) -> None:
    storage = MaterialStorage(tmp_path)

    stored = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=PDF_CONTENT,
    )

    metadata_path = (
        tmp_path
        / stored.material_id
        / "metadata.json"
    )

    assert metadata_path.is_file()


def test_get_rejects_unknown_material(
    tmp_path: Path,
) -> None:
    storage = MaterialStorage(tmp_path)

    with pytest.raises(
        MaterialStorageError,
        match="not found",
    ):
        storage.get(
            "material-0000000000000000"
        )


def test_get_rejects_invalid_material_id(
    tmp_path: Path,
) -> None:
    storage = MaterialStorage(tmp_path)

    with pytest.raises(
        MaterialStorageError,
        match="Invalid material_id",
    ):
        storage.get("../../secret")


def test_get_rejects_tampered_file(
    tmp_path: Path,
) -> None:
    storage = MaterialStorage(tmp_path)

    stored = storage.store(
        filename="lesson.pdf",
        content_type="application/pdf",
        content=PDF_CONTENT,
    )

    Path(stored.stored_path).write_bytes(
        b"tampered"
    )

    with pytest.raises(
        MaterialStorageError,
        match="checksum mismatch",
    ):
        storage.get(stored.material_id)