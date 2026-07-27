import math

import pytest
from pydantic import ValidationError

from schemas.vision_contract import (
    BoundingBoxSpace,
    ExtractedTable,
    VisualElement,
    VisualElementType,
)


def create_visual_element(
    bounding_box: tuple[
        float,
        float,
        float,
        float,
    ],
    bounding_box_space: BoundingBoxSpace = (
        BoundingBoxSpace.PIXELS
    ),
) -> VisualElement:
    return VisualElement(
        element_id="element-001",
        element_type=VisualElementType.DIAGRAM,
        title="Learning pipeline",
        description="A visual learning pipeline.",
        bounding_box=bounding_box,
        bounding_box_space=bounding_box_space,
        confidence=0.95,
    )


def test_pixel_bounding_box_is_supported() -> None:
    element = create_visual_element(
        bounding_box=(20.0, 30.0, 600.0, 400.0),
    )

    assert element.bounding_box == (
        20.0,
        30.0,
        600.0,
        400.0,
    )
    assert (
        element.bounding_box_space
        is BoundingBoxSpace.PIXELS
    )


@pytest.mark.parametrize(
    "bounding_box",
    [
        (100.0, 20.0, 50.0, 200.0),
        (20.0, 200.0, 100.0, 50.0),
        (20.0, 20.0, 20.0, 100.0),
        (20.0, 20.0, 100.0, 20.0),
        (-1.0, 20.0, 100.0, 200.0),
        (20.0, math.nan, 100.0, 200.0),
        (20.0, 30.0, math.inf, 200.0),
    ],
)
def test_invalid_pixel_bounding_box_is_rejected(
    bounding_box: tuple[
        float,
        float,
        float,
        float,
    ],
) -> None:
    with pytest.raises(ValidationError):
        create_visual_element(
            bounding_box=bounding_box,
        )


def test_valid_normalized_bounding_box_is_supported() -> None:
    table = ExtractedTable(
        table_id="table-001",
        title="Results",
        headers=["Metric", "Value"],
        rows=[["Accuracy", "0.95"]],
        bounding_box=(0.1, 0.2, 0.8, 0.9),
        bounding_box_space=(
            BoundingBoxSpace.NORMALIZED
        ),
        confidence=0.95,
    )

    assert table.bounding_box == (
        0.1,
        0.2,
        0.8,
        0.9,
    )
    assert (
        table.bounding_box_space
        is BoundingBoxSpace.NORMALIZED
    )


def test_out_of_range_normalized_box_is_rejected() -> None:
    with pytest.raises(
        ValidationError,
        match="must be between 0 and 1",
    ):
        create_visual_element(
            bounding_box=(0.1, 0.2, 1.2, 0.9),
            bounding_box_space=(
                BoundingBoxSpace.NORMALIZED
            ),
        )