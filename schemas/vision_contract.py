import math
from enum import Enum
from typing import Self

from pydantic import BaseModel, Field, model_validator


BoundingBox = tuple[float, float, float, float]


class VisionTask(str, Enum):
    DESCRIBE_VISUALS = "describe_visuals"
    EXTRACT_TEXT = "extract_text"
    EXTRACT_TABLES = "extract_tables"
    EXPLAIN_RELATIONSHIPS = "explain_relationships"


class VisualElementType(str, Enum):
    IMAGE = "image"
    DIAGRAM = "diagram"
    CHART = "chart"
    TABLE = "table"
    EQUATION = "equation"
    CODE_BLOCK = "code_block"
    OTHER = "other"


class BoundingBoxSpace(str, Enum):
    PIXELS = "pixels"
    NORMALIZED = "normalized"


class VisionResponseStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class VisionRequest(BaseModel):
    request_id: str
    material_id: str
    material_name: str
    page_number: int = Field(ge=1)

    asset_id: str
    image_path: str
    mime_type: str = "image/png"

    image_width_pixels: int | None = Field(
        default=None,
        ge=1,
    )
    image_height_pixels: int | None = Field(
        default=None,
        ge=1,
    )

    extracted_text: str = ""

    tasks: list[VisionTask] = Field(
        default_factory=lambda: [
            VisionTask.DESCRIBE_VISUALS,
            VisionTask.EXTRACT_TEXT,
            VisionTask.EXTRACT_TABLES,
            VisionTask.EXPLAIN_RELATIONSHIPS,
        ]
    )

    prompt_version: str = "vision-v1"

    @model_validator(mode="after")
    def validate_image_dimensions(self) -> Self:
        width_missing = self.image_width_pixels is None
        height_missing = self.image_height_pixels is None

        if width_missing != height_missing:
            raise ValueError(
                "image_width_pixels and "
                "image_height_pixels must be supplied together"
            )

        return self

class GroundedRegion(BaseModel):
    bounding_box: BoundingBox | None = None
    bounding_box_space: BoundingBoxSpace = (
        BoundingBoxSpace.PIXELS
    )

    @model_validator(mode="after")
    def validate_bounding_box(self) -> Self:
        if self.bounding_box is None:
            return self

        x1, y1, x2, y2 = self.bounding_box
        coordinates = (x1, y1, x2, y2)

        if not all(
            math.isfinite(value)
            for value in coordinates
        ):
            raise ValueError(
                "bounding_box coordinates must be finite"
            )

        if any(value < 0 for value in coordinates):
            raise ValueError(
                "bounding_box coordinates must not be negative"
            )

        if x1 >= x2:
            raise ValueError(
                "bounding_box must satisfy x1 < x2"
            )

        if y1 >= y2:
            raise ValueError(
                "bounding_box must satisfy y1 < y2"
            )

        if (
            self.bounding_box_space
            is BoundingBoxSpace.NORMALIZED
            and any(value > 1 for value in coordinates)
        ):
            raise ValueError(
                "normalized bounding_box coordinates "
                "must be between 0 and 1"
            )

        return self


class VisualElement(GroundedRegion):
    element_id: str
    element_type: VisualElementType

    title: str = ""
    description: str
    extracted_text: str = ""

    confidence: float = Field(ge=0, le=1)


class ExtractedTable(GroundedRegion):
    table_id: str
    title: str = ""

    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    confidence: float = Field(ge=0, le=1)


class VisualRelationship(BaseModel):
    source_element_id: str
    target_element_id: str
    relation: str
    confidence: float = Field(ge=0, le=1)


class VisionResponse(BaseModel):
    request_id: str
    material_id: str
    material_name: str
    page_number: int = Field(ge=1)
    asset_id: str

    status: VisionResponseStatus
    page_summary: str
    ocr_text: str = ""

    visual_elements: list[VisualElement] = Field(
        default_factory=list
    )
    tables: list[ExtractedTable] = Field(
        default_factory=list
    )
    relationships: list[VisualRelationship] = Field(
        default_factory=list
    )
    warnings: list[str] = Field(default_factory=list)

    confidence: float = Field(ge=0, le=1)
    agent_model: str
    prompt_version: str = "vision-v1"