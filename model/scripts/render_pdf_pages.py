import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.multimodal_verifier import (
    MultimodalVerifier,
)
from src.agents.multimodal_agent import (
    DemoMultimodalAgent,
)
from src.ingestion.manifest_exporter import ManifestExporter
from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.vision_request_builder import (
    VisionRequestBuilder,
)
from src.ingestion.vision_request_exporter import (
    VisionRequestExporter,
)
from src.ingestion.vision_response_exporter import (
    VisionResponseExporter,
)
from src.ingestion.vision_verification_exporter import (
    VisionVerificationExporter,
)
from src.service.multimodal_pipeline import (
    MultimodalPipeline,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render PDF pages, detect visual content, "
            "and export multimodal manifests."
        ),
    )

    parser.add_argument(
        "pdf_path",
        type=Path,
        help="Path to the source PDF file.",
    )

    parser.add_argument(
        "--material-id",
        required=True,
        help="Stable material identifier used by the KB.",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/rendered_pages"),
        help="Root directory for rendered page images.",
    )

    parser.add_argument(
        "--manifest-dir",
        type=Path,
        default=Path("data/manifests"),
        help="Root directory for JSON manifests.",
    )

    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="PNG rendering resolution. Default: 150 DPI.",
    )

    parser.add_argument(
        "--multimodal-agent",
        choices=["none", "demo"],
        default="none",
        help=(
            "Multimodal agent to run after request export. "
            "Default: none."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_arguments()

    ingestor = PDFIngestor(
        render_dpi=args.dpi,
    )

    result = ingestor.render_pages_with_assets(
        pdf_path=args.pdf_path,
        material_id=args.material_id,
        output_dir=args.output_dir,
    )

    if not result.assets:
        raise ValueError(
            "PDF rendering produced no page assets"
        )

    rendered_material_dir_name = Path(
        result.assets[0].file_path
    ).parent.name

    material_manifest_dir = (
        args.manifest_dir
        / rendered_material_dir_name
    )

    manifest_exporter = ManifestExporter()

    pages_path, assets_path = manifest_exporter.export(
        result=result,
        output_dir=material_manifest_dir,
    )

    vision_requests = VisionRequestBuilder().build(
        result
    )

    vision_requests_path = (
        VisionRequestExporter().export(
            result=result,
            requests=vision_requests,
            output_dir=material_manifest_dir,
        )
    )

    vision_responses_path: Path | None = None
    vision_verifications_path: Path | None = None

    if args.multimodal_agent == "demo":
        multimodal_pipeline = MultimodalPipeline(
            agent=DemoMultimodalAgent(),
        )

        vision_responses = (
            multimodal_pipeline.process(
                vision_requests
            )
        )

        vision_responses_path = (
            VisionResponseExporter().export(
                result=result,
                responses=vision_responses,
                output_dir=material_manifest_dir,
            )
        )

        verification_batch = (
            MultimodalVerifier().verify_batch(
                requests=vision_requests,
                responses=vision_responses,
            )
        )

        vision_verifications_path = (
            VisionVerificationExporter().export(
                requests=vision_requests,
                batch=verification_batch,
                output_dir=material_manifest_dir,
            )
        )

    vision_page_count = len(vision_requests)

    print()
    print(f"Material ID: {args.material_id}")
    print(
        f"Source PDF: {args.pdf_path.resolve()}"
    )
    print(f"Total pages: {len(result.pages)}")
    print(f"Total assets: {len(result.assets)}")
    print(
        f"Vision requests: {vision_page_count}"
    )
    print(
        "Text-only pages: "
        f"{len(result.pages) - vision_page_count}"
    )
    print(
        "Multimodal agent: "
        f"{args.multimodal_agent}"
    )
    print()

    for page in result.pages:
        text_status = (
            "text"
            if page.extracted_text
            else "no-text"
        )

        visual_status = (
            "visual"
            if page.has_visual_content
            else "no-visual"
        )

        routing_status = (
            "VISION"
            if page.requires_vision
            else "TEXT"
        )

        asset_id = (
            page.image_ids[0]
            if page.image_ids
            else "no-asset"
        )

        print(
            f"Page {page.page_number:04d} | "
            f"{text_status:7} | "
            f"{visual_status:9} | "
            f"route={routing_status:6} | "
            f"asset={asset_id}"
        )

    print()
    print(
        "Pages manifest: "
        f"{pages_path.resolve()}"
    )
    print(
        "Assets manifest: "
        f"{assets_path.resolve()}"
    )
    print(
        "Vision requests: "
        f"{vision_requests_path.resolve()}"
    )

    if vision_responses_path is not None:
        print(
            "Vision responses: "
            f"{vision_responses_path.resolve()}"
        )
    else:
        print(
            "Vision responses: not generated "
            "(multimodal agent disabled)"
        )

    if vision_verifications_path is not None:
        print(
            "Vision verifications: "
            f"{vision_verifications_path.resolve()}"
        )
    else:
        print(
            "Vision verifications: not generated "
            "(multimodal agent disabled)"
        )


if __name__ == "__main__":
    main()
