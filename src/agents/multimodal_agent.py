import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from schemas.vision_contract import (
    ExtractedTable,
    VisionRequest,
    VisionResponse,
    VisionResponseStatus,
    VisualElement,
    VisualElementType,
    VisualRelationship,
)
from src.agents.multimodal_client import (
    MultimodalResponseError,
)


class MultimodalJSONClient(Protocol):
    def chat_json(
        self,
        request: VisionRequest,
        system_prompt: str,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        ...


class ExternalVisionPayload(BaseModel):
    status: VisionResponseStatus
    page_summary: str = Field(min_length=1)
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


class MultimodalAgent(ABC):
    @abstractmethod
    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        """Analyze one rendered material page."""


class DemoMultimodalAgent(MultimodalAgent):
    AGENT_MODEL = "demo-multimodal-agent"
    PROMPT_VERSION = "vision-v1"

    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        image_path = Path(request.image_path)

        if not image_path.is_file():
            raise FileNotFoundError(
                "Vision request image not found: "
                f"{image_path}"
            )

        element_id = self._create_element_id(
            request_id=request.request_id,
            asset_id=request.asset_id,
        )

        page_summary = (
            request.extracted_text
            if request.extracted_text
            else (
                "The page contains visual content that "
                "requires multimodal analysis."
            )
        )

        return VisionResponse(
            request_id=request.request_id,
            material_id=request.material_id,
            material_name=request.material_name,
            page_number=request.page_number,
            asset_id=request.asset_id,
            status=VisionResponseStatus.NEEDS_REVIEW,
            page_summary=page_summary,
            ocr_text=request.extracted_text,
            visual_elements=[
                VisualElement(
                    element_id=element_id,
                    element_type=VisualElementType.IMAGE,
                    title="Rendered material page",
                    description=(
                        "Demo placeholder for a rendered PDF "
                        "page. No image-pixel inference was "
                        "performed."
                    ),
                    confidence=0.50,
                )
            ],
            tables=[],
            relationships=[],
            warnings=[
                (
                    "DemoMultimodalAgent does not inspect image "
                    "pixels. Replace it with an external "
                    "multimodal implementation."
                )
            ],
            confidence=0.50,
            agent_model=self.AGENT_MODEL,
            prompt_version=self.PROMPT_VERSION,
        )

    @staticmethod
    def _create_element_id(
        request_id: str,
        asset_id: str,
    ) -> str:
        source = f"{request_id}:{asset_id}:demo-element"
        digest = hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()[:16]

        return f"element-{digest}"


class ExternalMultimodalAgent(MultimodalAgent):
    PROMPT_VERSION = "vision-v1"

    SYSTEM_PROMPT = """
You are a multimodal knowledge extraction agent for an educational
learning companion.

Analyze only the supplied rendered material page and supplied text
layer. Do not add facts that are not visible in the page or present
in the supplied text.

Return exactly one JSON object with this structure:

{
  "status": "success | partial | needs_review | failed",
  "page_summary": "grounded summary of the page",
  "ocr_text": "text visible in the image but missing from text layer",
  "visual_elements": [
    {
      "element_id": "stable local identifier",
      "element_type": "image | diagram | chart | table | equation | code_block | other",
      "title": "optional title",
      "description": "grounded visual description",
      "extracted_text": "text inside this visual element",
      "bounding_box": [x1, y1, x2, y2] or null,
      "confidence": 0.0
    }
  ],
  "tables": [
    {
      "table_id": "stable local identifier",
      "title": "optional title",
      "headers": ["header"],
      "rows": [["cell"]],
      "notes": ["uncertainty or interpretation note"],
      "bounding_box": [x1, y1, x2, y2] or null,
      "confidence": 0.0
    }
  ],
  "relationships": [
    {
      "source_element_id": "element identifier",
      "target_element_id": "element identifier",
      "relation": "visible relationship",
      "confidence": 0.0
    }
  ],
  "warnings": ["unclear or unsupported portion"],
  "confidence": 0.0
}

Rules:
- Confidence values must be between 0 and 1.
- Use status "partial" when only part of the page is readable.
- Use status "needs_review" when visual interpretation is uncertain.
- Use status "failed" when the image cannot be analyzed.
- Do not infer invisible labels or relationships.
- Do not repeat the supplied text layer in ocr_text.
- Return no Markdown and no text outside the JSON object.
""".strip()

    def __init__(
        self,
        client: MultimodalJSONClient,
        agent_model: str,
        prompt_version: str = PROMPT_VERSION,
    ) -> None:
        if not agent_model.strip():
            raise ValueError(
                "agent_model must not be empty"
            )

        if not prompt_version.strip():
            raise ValueError(
                "prompt_version must not be empty"
            )

        self.client = client
        self.agent_model = agent_model
        self.prompt_version = prompt_version

    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        raw_result = self.client.chat_json(
            request=request,
            system_prompt=self.SYSTEM_PROMPT,
            temperature=0.0,
        )

        try:
            payload = ExternalVisionPayload.model_validate(
                raw_result
            )
        except ValidationError as error:
            raise MultimodalResponseError(
                "External multimodal payload does not "
                "match VisionResponse schema"
            ) from error

        return VisionResponse(
            request_id=request.request_id,
            material_id=request.material_id,
            material_name=request.material_name,
            page_number=request.page_number,
            asset_id=request.asset_id,
            status=payload.status,
            page_summary=payload.page_summary,
            ocr_text=payload.ocr_text,
            visual_elements=payload.visual_elements,
            tables=payload.tables,
            relationships=payload.relationships,
            warnings=payload.warnings,
            confidence=payload.confidence,
            agent_model=self.agent_model,
            prompt_version=self.prompt_version,
        )