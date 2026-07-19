import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import fitz


class ChunkType(str, Enum):
    TEXT = "text"
    OCR_TEXT = "ocr_text"
    DIAGRAM = "diagram"
    CHART = "chart"
    TABLE = "table"
    EQUATION = "equation"
    MIXED = "mixed"


class SourceType(str, Enum):
    TEXT_LAYER = "text_layer"
    OCR = "ocr"
    VISION = "vision"
    MIXED = "mixed"

class AssetType(str, Enum):
    PAGE_RENDER = "page_render"
    EMBEDDED_IMAGE = "embedded_image"
    DIAGRAM = "diagram"
    CHART = "chart"
    TABLE = "table"
    EQUATION = "equation"

@dataclass(frozen=True)
class PageAsset:
    asset_id: str
    material_id: str
    material_name: str
    page_number: int

    asset_type: AssetType
    file_path: str
    mime_type: str

    width_pixels: int
    height_pixels: int

    bounding_box: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class MaterialPage:
    material_id: str
    material_name: str
    page_number: int
    extracted_text: str

    rendered_image_path: str | None = None
    image_ids: tuple[str, ...] = ()
    has_visual_content: bool = False
    requires_vision: bool = False

@dataclass(frozen=True)
class PageRenderResult:
    pages: tuple[MaterialPage, ...]
    assets: tuple[PageAsset, ...]

@dataclass(frozen=True)
class MaterialChunk:
    chunk_id: str
    material_id: str
    material_name: str
    page_number: int
    chunk_index: int
    text: str

    chunk_type: ChunkType = ChunkType.TEXT
    source_type: SourceType = SourceType.TEXT_LAYER
    image_ids: tuple[str, ...] = ()
    bounding_box: tuple[float, float, float, float] | None = None


class PDFIngestor:
    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 150,
        render_dpi: int = 150,
    ):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero")

        if overlap < 0 or overlap >= chunk_size:
            raise ValueError("overlap must be between 0 and chunk_size")

        if render_dpi <= 0:
            raise ValueError("render_dpi must be greater than zero")

        self.chunk_size = chunk_size
        self.overlap = overlap
        self.render_dpi = render_dpi

    def ingest(
        self,
        pdf_path: str | Path,
        material_id: str,
    ) -> list[MaterialChunk]:
        path = self._validate_pdf_path(pdf_path)

        chunks: list[MaterialChunk] = []

        with fitz.open(path) as document:
            for page_index, page in enumerate(document):
                text = self._clean_text(page.get_text("text"))

                if not text:
                    continue

                page_chunks = self._split_text(text)

                for chunk_index, chunk_text in enumerate(page_chunks):
                    chunk_id = self._create_chunk_id(
                        material_id=material_id,
                        page_number=page_index + 1,
                        chunk_index=chunk_index,
                        text=chunk_text,
                    )

                    chunks.append(
                        MaterialChunk(
                            chunk_id=chunk_id,
                            material_id=material_id,
                            material_name=path.name,
                            page_number=page_index + 1,
                            chunk_index=chunk_index,
                            text=chunk_text,
                        )
                    )

        return chunks

    def render_pages(
        self,
        pdf_path: str | Path,
        material_id: str,
        output_dir: str | Path,
    ) -> list[MaterialPage]:
        """
        Backward-compatible page rendering interface.

        Existing callers continue receiving list[MaterialPage].
        Use render_pages_with_assets() when PageAsset records are needed.
        """
        result = self.render_pages_with_assets(
            pdf_path=pdf_path,
            material_id=material_id,
            output_dir=output_dir,
        )

        return list(result.pages)

    def render_pages_with_assets(
        self,
        pdf_path: str | Path,
        material_id: str,
        output_dir: str | Path,
    ) -> PageRenderResult:
        """
        Render every PDF page and return linked pages and page assets.
        """
        path = self._validate_pdf_path(pdf_path)

        if not material_id.strip():
            raise ValueError("material_id must not be empty")

        output_root = Path(output_dir)
        safe_material_id = self._sanitize_path_component(material_id)
        material_output_dir = output_root / safe_material_id
        material_output_dir.mkdir(parents=True, exist_ok=True)

        rendered_pages: list[MaterialPage] = []
        page_assets: list[PageAsset] = []

        with fitz.open(path) as document:
            for page_index, page in enumerate(document):
                page_number = page_index + 1

                image_path = (
                    material_output_dir / f"page-{page_number:04d}.png"
                )

                pixmap = page.get_pixmap(
                    dpi=self.render_dpi,
                    alpha=False,
                )
                pixmap.save(str(image_path))

                resolved_image_path = str(image_path.resolve())

                extracted_text = self._clean_text(
                    page.get_text("text")
                )

                has_visual_content = self._has_visual_content(page)

                asset_id = self._create_asset_id(
                    material_id=material_id,
                    page_number=page_number,
                    asset_type=AssetType.PAGE_RENDER,
                )

                page_asset = PageAsset(
                    asset_id=asset_id,
                    material_id=material_id,
                    material_name=path.name,
                    page_number=page_number,
                    asset_type=AssetType.PAGE_RENDER,
                    file_path=resolved_image_path,
                    mime_type="image/png",
                    width_pixels=pixmap.width,
                    height_pixels=pixmap.height,
                )

                material_page = MaterialPage(
                    material_id=material_id,
                    material_name=path.name,
                    page_number=page_number,
                    extracted_text=extracted_text,
                    rendered_image_path=resolved_image_path,
                    image_ids=(asset_id,),
                    has_visual_content=has_visual_content,
                    requires_vision=has_visual_content,
                )

                page_assets.append(page_asset)
                rendered_pages.append(material_page)

        return PageRenderResult(
            pages=tuple(rendered_pages),
            assets=tuple(page_assets),
        )
    
    @staticmethod
    def _has_visual_content(page: fitz.Page) -> bool:
        """
        Detect whether a PDF page contains visual information.

        Embedded images cover scanned pages and raster illustrations.
        Vector drawings cover shapes, chart lines, table borders, arrows,
        and flowchart components.
        """
        embedded_images = page.get_images(full=True)

        if embedded_images:
            return True

        vector_drawings = page.get_drawings()

        if vector_drawings:
            return True

        return False

    @staticmethod
    def _validate_pdf_path(pdf_path: str | Path) -> Path:
        path = Path(pdf_path)

        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {path}")

        if not path.is_file():
            raise ValueError(f"PDF path is not a file: {path}")

        if path.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF file: {path}")

        return path

    @staticmethod
    def _sanitize_path_component(value: str) -> str:
        """
        Convert material_id into a safe directory name.

        Example:
            "cloud/class 01" -> "cloud-class-01"
        """
        sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
        sanitized = sanitized.strip(".-_")

        if not sanitized:
            raise ValueError(
                "material_id must contain at least one valid character"
            )

        return sanitized

    @staticmethod
    def _clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def _split_text(self, text: str) -> list[str]:
        chunks: list[str] = []
        start = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunks.append(text[start:end].strip())

            if end == len(text):
                break

            start = end - self.overlap

        return [chunk for chunk in chunks if chunk]
    
    @staticmethod
    def _create_asset_id(
        material_id: str,
        page_number: int,
        asset_type: AssetType,
    ) -> str:
        source = (
            f"{material_id}:"
            f"{page_number}:"
            f"{asset_type.value}"
        )
        digest = hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest()[:16]

        return f"asset-{digest}"

    @staticmethod
    def _create_chunk_id(
        material_id: str,
        page_number: int,
        chunk_index: int,
        text: str,
    ) -> str:
        source = f"{material_id}:{page_number}:{chunk_index}:{text}"
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
        return f"chunk-{digest}"