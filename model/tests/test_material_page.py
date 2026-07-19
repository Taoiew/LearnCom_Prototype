from src.ingestion.pdf_ingestor import (
    ChunkType,
    MaterialChunk,
    MaterialPage,
    SourceType,
)


def test_material_page_supports_visual_content():
    page = MaterialPage(
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=5,
        extracted_text="ข้อความที่ดึงได้จากหน้า",
        rendered_image_path=(
            "data/processed/material-001/pages/page-0005.png"
        ),
        image_ids=("image-005-001",),
        has_visual_content=True,
        requires_vision=True,
    )

    assert page.page_number == 5
    assert page.has_visual_content is True
    assert page.requires_vision is True
    assert page.image_ids == ("image-005-001",)


def test_existing_text_chunk_remains_compatible():
    chunk = MaterialChunk(
        chunk_id="chunk-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=5,
        chunk_index=0,
        text="Gradient descent reduces loss.",
    )

    assert chunk.chunk_type == ChunkType.TEXT
    assert chunk.source_type == SourceType.TEXT_LAYER
    assert chunk.image_ids == ()
    assert chunk.bounding_box is None