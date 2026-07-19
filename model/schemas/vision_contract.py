from enum import Enum

from pydantic import BaseModel, Field


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


class VisualElement(BaseModel):
    element_id: str
    element_type: VisualElementType

    title: str = ""
    description: str
    extracted_text: str = ""

    bounding_box: (
        tuple[float, float, float, float] | None
    ) = None

    confidence: float = Field(ge=0, le=1)


class ExtractedTable(BaseModel):
    table_id: str
    title: str = ""

    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    bounding_box: (
        tuple[float, float, float, float] | None
    ) = None

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