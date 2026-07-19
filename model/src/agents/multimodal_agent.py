import hashlib
from abc import ABC, abstractmethod
from pathlib import Path

from schemas.vision_contract import (
    VisionRequest,
    VisionResponse,
    VisionResponseStatus,
    VisualElement,
    VisualElementType,
)


class MultimodalAgent(ABC):
    @abstractmethod
    def analyze(
        self,
        request: VisionRequest,
    ) -> VisionResponse:
        """
        Analyze one rendered material page.

        Implementations must return structured data conforming
        to VisionResponse.
        """


class DemoMultimodalAgent(MultimodalAgent):
    """
    Deterministic demo implementation.

    This agent does not inspect image pixels and does not call an
    external model. It is used to verify orchestration and contracts.
    """

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
                        "Demo placeholder for a rendered PDF page. "
                        "No image-pixel inference was performed."
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