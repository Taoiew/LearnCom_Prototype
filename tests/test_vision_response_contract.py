import pytest
from pydantic import ValidationError

from schemas.vision_contract import (
    ExtractedTable,
    VisionResponse,
    VisionResponseStatus,
    VisualElement,
    VisualElementType,
    VisualRelationship,
)


def test_vision_response_supports_structured_visual_data() -> None:
    response = VisionResponse(
        request_id="vision-request-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-18d318946af49d31",
        status=VisionResponseStatus.SUCCESS,
        page_summary=(
            "The page defines required custom exceptions "
            "and shows their role in inventory operations."
        ),
        ocr_text="Custom Exceptions (Required)",
        visual_elements=[
            VisualElement(
                element_id="element-flowchart-001",
                element_type=VisualElementType.DIAGRAM,
                title="Exception flow",
                description=(
                    "A flowchart connects invalid inventory "
                    "operations to their exceptions."
                ),
                confidence=0.95,
            )
        ],
        tables=[
            ExtractedTable(
                table_id="table-001",
                title="Required exceptions",
                headers=["Exception", "Condition"],
                rows=[
                    [
                        "ProductExistsError",
                        "Adding an existing product",
                    ],
                    [
                        "ProductNotFoundError",
                        "Accessing a missing product",
                    ],
                ],
                confidence=0.93,
            )
        ],
        relationships=[
            VisualRelationship(
                source_element_id="operation-add",
                target_element_id="ProductExistsError",
                relation="raises",
                confidence=0.94,
            )
        ],
        confidence=0.94,
        agent_model="demo-multimodal-agent",
    )

    assert response.status is VisionResponseStatus.SUCCESS
    assert response.page_number == 2
    assert len(response.visual_elements) == 1
    assert len(response.tables) == 1
    assert len(response.relationships) == 1

    assert (
        response.visual_elements[0].element_type
        is VisualElementType.DIAGRAM
    )
    assert response.tables[0].headers == [
        "Exception",
        "Condition",
    ]
    assert response.relationships[0].relation == "raises"


def test_vision_response_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        VisionResponse(
            request_id="vision-request-invalid",
            material_id="material-001",
            material_name="lesson.pdf",
            page_number=2,
            asset_id="asset-invalid",
            status=VisionResponseStatus.SUCCESS,
            page_summary="Invalid confidence example",
            confidence=1.5,
            agent_model="demo-multimodal-agent",
        )