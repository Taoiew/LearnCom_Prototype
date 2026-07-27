from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.ingestion.material_storage import MaterialStorage
from src.service.api import create_app


PDF_CONTENT = (
    b"%PDF-1.4\n"
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


class FakePipeline:
    def run(self, **kwargs: Any) -> None:
        raise AssertionError(
            "Chat pipeline must not run during material upload"
        )


def create_client(
    tmp_path: Path,
    *,
    max_file_bytes: int = 1024 * 1024,
) -> TestClient:
    storage = MaterialStorage(
        storage_root=tmp_path / "uploads",
        max_file_bytes=max_file_bytes,
    )

    app = create_app(
        pipeline=FakePipeline(),
        material_storage=storage,
    )

    return TestClient(app)


def test_upload_pdf_material(
    tmp_path: Path,
) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "lesson.pdf",
                PDF_CONTENT,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201

    payload = response.json()

    assert payload["material_id"].startswith("material-")
    assert payload["original_filename"] == "lesson.pdf"
    assert payload["file_type"] == "pdf"
    assert payload["mime_type"] == "application/pdf"
    assert payload["size_bytes"] == len(PDF_CONTENT)
    assert payload["status"] == "stored"
    assert Path(payload["stored_path"]).is_file()


def test_upload_png_material(
    tmp_path: Path,
) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "diagram.png",
                PNG_CONTENT,
                "image/png",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["file_type"] == "png"


def test_upload_jpeg_material(
    tmp_path: Path,
) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "photo.jpeg",
                JPEG_CONTENT,
                "image/jpeg",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["file_type"] == "jpeg"


def test_upload_removes_path_traversal(
    tmp_path: Path,
) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "../../lesson.pdf",
                PDF_CONTENT,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    assert (
        response.json()["original_filename"]
        == "lesson.pdf"
    )


def test_upload_rejects_empty_file(
    tmp_path: Path,
) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert "must not be empty" in response.json()["detail"]


def test_upload_rejects_unsupported_type(
    tmp_path: Path,
) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "notes.txt",
                b"plain text",
                "text/plain",
            )
        },
    )

    assert response.status_code == 415
    assert (
        "Unsupported material content type"
        in response.json()["detail"]
    )


def test_upload_rejects_mismatched_content(
    tmp_path: Path,
) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "fake.pdf",
                PNG_CONTENT,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert (
        "does not match"
        in response.json()["detail"]
    )


def test_upload_rejects_invalid_file_signature(
    tmp_path: Path,
) -> None:
    client = create_client(tmp_path)

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "fake.png",
                b"not-a-real-image",
                "image/png",
            )
        },
    )

    assert response.status_code == 400
    assert (
        "not a valid PDF, PNG, or JPEG"
        in response.json()["detail"]
    )


def test_upload_rejects_oversized_file(
    tmp_path: Path,
) -> None:
    client = create_client(
        tmp_path,
        max_file_bytes=10,
    )

    response = client.post(
        "/v1/materials/upload",
        files={
            "file": (
                "lesson.pdf",
                PDF_CONTENT,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert (
        "exceeds maximum size"
        in response.json()["detail"]
    )