import pytest

from schemas.vision_contract import (
    ExtractedTable,
    VisualElement,
    VisualElementType,
    VisualRelationship,
    VisionResponse,
    VisionResponseStatus,
)
from src.evaluation.grounding_validator import (
    GroundingValidator,
)


def create_element(
    element_id: str,
    confidence: float = 0.95,
) -> VisualElement:
    return VisualElement(
        element_id=element_id,
        element_type=VisualElementType.DIAGRAM,
        title="Pipeline node",
        description="A node in the learning pipeline.",
        bounding_box=(10.0, 20.0, 100.0, 120.0),
        confidence=confidence,
    )


def create_table(
    table_id: str,
    confidence: float = 0.95,
) -> ExtractedTable:
    return ExtractedTable(
        table_id=table_id,
        title="Results",
        headers=["Metric", "Value"],
        rows=[["Accuracy", "0.95"]],
        bounding_box=(20.0, 150.0, 300.0, 400.0),
        confidence=confidence,
    )


def create_response(
    *,
    elements: list[VisualElement] | None = None,
    tables: list[ExtractedTable] | None = None,
    relationships: list[VisualRelationship] | None = None,
) -> VisionResponse:
    return VisionResponse(
        request_id="vision-request-001",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-001",
        status=VisionResponseStatus.SUCCESS,
        page_summary="A structured learning pipeline.",
        visual_elements=elements or [],
        tables=tables or [],
        relationships=relationships or [],
        confidence=0.95,
        agent_model="external-vision-model",
    )


def test_valid_grounding_structure_passes() -> None:
    response = create_response(
        elements=[
            create_element("element-source"),
            create_element("element-target"),
        ],
        tables=[
            create_table("table-001"),
        ],
        relationships=[
            VisualRelationship(
                source_element_id="element-source",
                target_element_id="element-target",
                relation="flows_to",
                confidence=0.95,
            )
        ],
    )

    result = GroundingValidator().validate(response)

    assert result.is_structurally_valid is True
    assert result.requires_review is False
    assert result.rejection_reasons == []
    assert result.review_reasons == []


def test_duplicate_element_id_is_rejected() -> None:
    response = create_response(
        elements=[
            create_element("element-duplicate"),
            create_element("element-duplicate"),
        ],
    )

    result = GroundingValidator().validate(response)

    assert result.is_structurally_valid is False
    assert (
        "Duplicate visual element_id: element-duplicate"
        in result.rejection_reasons
    )


def test_duplicate_table_id_is_rejected() -> None:
    response = create_response(
        tables=[
            create_table("table-duplicate"),
            create_table("table-duplicate"),
        ],
    )

    result = GroundingValidator().validate(response)

    assert result.is_structurally_valid is False
    assert (
        "Duplicate table_id: table-duplicate"
        in result.rejection_reasons
    )


@pytest.mark.parametrize(
    ("source_id", "target_id", "expected_text"),
    [
        (
            "missing-source",
            "element-target",
            "unknown source_element_id",
        ),
        (
            "element-source",
            "missing-target",
            "unknown target_element_id",
        ),
    ],
)
def test_unknown_relationship_reference_is_rejected(
    source_id: str,
    target_id: str,
    expected_text: str,
) -> None:
    response = create_response(
        elements=[
            create_element("element-source"),
            create_element("element-target"),
        ],
        relationships=[
            VisualRelationship(
                source_element_id=source_id,
                target_element_id=target_id,
                relation="flows_to",
                confidence=0.95,
            )
        ],
    )

    result = GroundingValidator().validate(response)

    assert result.is_structurally_valid is False
    assert any(
        expected_text in reason
        for reason in result.rejection_reasons
    )


def test_empty_relationship_is_rejected() -> None:
    response = create_response(
        elements=[
            create_element("element-source"),
            create_element("element-target"),
        ],
        relationships=[
            VisualRelationship(
                source_element_id="element-source",
                target_element_id="element-target",
                relation="   ",
                confidence=0.95,
            )
        ],
    )

    result = GroundingValidator().validate(response)

    assert result.is_structurally_valid is False
    assert (
        "Relationship 1 has empty relation"
        in result.rejection_reasons
    )


def test_low_child_confidence_requires_review() -> None:
    response = create_response(
        elements=[
            create_element(
                "element-low-confidence",
                confidence=0.50,
            ),
        ],
        tables=[
            create_table(
                "table-low-confidence",
                confidence=0.60,
            ),
        ],
    )

    result = GroundingValidator(
        minimum_evidence_confidence=0.70,
    ).validate(response)

    assert result.is_structurally_valid is True
    assert result.requires_review is True
    assert len(result.review_reasons) == 2


def test_invalid_confidence_threshold_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="must be between 0 and 1",
    ):
        GroundingValidator(
            minimum_evidence_confidence=1.1,
        )

def test_pixel_element_box_inside_image_passes() -> None:
    response = create_response(
        elements=[
            create_element("element-inside"),
        ],
    )

    result = GroundingValidator().validate(
        response=response,
        image_width_pixels=500,
        image_height_pixels=500,
    )

    assert result.is_structurally_valid is True
    assert result.rejection_reasons == []


def test_pixel_element_box_outside_image_is_rejected() -> None:
    element = VisualElement(
        element_id="element-outside",
        element_type=VisualElementType.DIAGRAM,
        title="Outside element",
        description="Element exceeds the page image.",
        bounding_box=(10.0, 20.0, 600.0, 700.0),
        confidence=0.95,
    )

    response = create_response(
        elements=[element],
    )

    result = GroundingValidator().validate(
        response=response,
        image_width_pixels=500,
        image_height_pixels=600,
    )

    assert result.is_structurally_valid is False
    assert (
        "Visual element bounding_box exceeds "
        "image width: element-outside"
        in result.rejection_reasons
    )
    assert (
        "Visual element bounding_box exceeds "
        "image height: element-outside"
        in result.rejection_reasons
    )


def test_pixel_table_box_outside_image_is_rejected() -> None:
    table = ExtractedTable(
        table_id="table-outside",
        title="Outside table",
        headers=["A", "B"],
        rows=[["1", "2"]],
        bounding_box=(20.0, 30.0, 900.0, 400.0),
        confidence=0.95,
    )

    response = create_response(
        tables=[table],
    )

    result = GroundingValidator().validate(
        response=response,
        image_width_pixels=800,
        image_height_pixels=600,
    )

    assert result.is_structurally_valid is False
    assert (
        "Table bounding_box exceeds image width: "
        "table-outside"
        in result.rejection_reasons
    )


def test_dimensions_must_be_supplied_together() -> None:
    response = create_response(
        elements=[
            create_element("element-001"),
        ],
    )

    with pytest.raises(
        ValueError,
        match="must be supplied together",
    ):
        GroundingValidator().validate(
            response=response,
            image_width_pixels=500,
            image_height_pixels=None,
        )

def test_ocr_echo_without_visual_evidence_requires_review() -> None:
    response = VisionResponse(
        request_id="vision-request-ocr-echo",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-001",
        status=VisionResponseStatus.SUCCESS,
        page_summary="Text copied from the page.",
        ocr_text=(
            "Custom Exceptions must use the exact "
            "required class names."
        ),
        confidence=0.95,
        agent_model="external-vision-model",
    )

    result = GroundingValidator().validate(
        response=response,
        source_extracted_text=(
            "Custom Exceptions must use the exact "
            "required class names."
        ),
    )

    assert result.is_structurally_valid is True
    assert result.requires_review is True
    assert (
        "OCR text substantially duplicates the "
        "source text layer and provides no "
        "independent visual evidence"
        in result.review_reasons
    )


def test_distinct_ocr_text_is_independent_evidence() -> None:
    response = VisionResponse(
        request_id="vision-request-distinct-ocr",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-001",
        status=VisionResponseStatus.SUCCESS,
        page_summary="Text found inside the diagram.",
        ocr_text=(
            "Input flows to validation and then "
            "to persistent storage."
        ),
        confidence=0.95,
        agent_model="external-vision-model",
    )

    result = GroundingValidator().validate(
        response=response,
        source_extracted_text=(
            "Custom Exceptions must use the exact "
            "required class names."
        ),
    )

    assert result.is_structurally_valid is True
    assert result.requires_review is False
    assert result.review_reasons == []


def test_ocr_echo_with_visual_elements_is_allowed() -> None:
    response = VisionResponse(
        request_id="vision-request-ocr-with-visual",
        material_id="material-001",
        material_name="lesson.pdf",
        page_number=2,
        asset_id="asset-001",
        status=VisionResponseStatus.SUCCESS,
        page_summary="A grounded diagram.",
        ocr_text="Learning pipeline",
        visual_elements=[
            create_element("element-grounded"),
        ],
        confidence=0.95,
        agent_model="external-vision-model",
    )

    result = GroundingValidator().validate(
        response=response,
        source_extracted_text="Learning pipeline",
    )

    assert result.is_structurally_valid is True
    assert result.requires_review is False
    assert result.review_reasons == []