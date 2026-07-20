import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.agents.multimodal_factory import (
    multimodal_agent_context,
)
from src.ingestion.manifest_exporter import (
    ManifestExporter,
)
from src.ingestion.pdf_ingestor import PDFIngestor
from src.service.multimodal_ingestion_runner import (
    MultimodalIngestionRunner,
    MultimodalRunArtifacts,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Render PDF pages, detect visual content, "
            "run optional multimodal analysis, and export "
            "versioned ingestion manifests."
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
        choices=[
            "none",
            "demo",
            "external",
        ],
        default="none",
        help=(
            "Multimodal agent to run after page rendering. "
            "External mode reads configuration from "
            "environment variables."
        ),
    )

    return parser.parse_args()


def render_material(
    args: argparse.Namespace,
):
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

    return result


def create_manifest_directory(
    result,
    manifest_root: Path,
) -> Path:
    rendered_material_dir_name = Path(
        result.assets[0].file_path
    ).parent.name

    return (
        manifest_root
        / rendered_material_dir_name
    )


def print_page_report(
    result,
) -> None:
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


def print_artifact_path(
    label: str,
    path: Path | None,
) -> None:
    if path is None:
        print(f"{label}: not generated")
        return

    print(f"{label}: {path.resolve()}")


def print_summary(
    args: argparse.Namespace,
    result,
    pages_path: Path,
    assets_path: Path,
    artifacts: MultimodalRunArtifacts,
) -> None:
    print()
    print(f"Material ID: {args.material_id}")
    print(
        f"Source PDF: {args.pdf_path.resolve()}"
    )
    print(f"Total pages: {len(result.pages)}")
    print(f"Total assets: {len(result.assets)}")
    print(
        f"Vision requests: "
        f"{artifacts.total_requests}"
    )
    print(
        f"Vision responses: "
        f"{artifacts.total_responses}"
    )
    print(
        f"Verified: {artifacts.verified_count}"
    )
    print(
        "Needs review: "
        f"{artifacts.needs_review_count}"
    )
    print(
        f"Rejected: {artifacts.rejected_count}"
    )
    print(
        "Multimodal agent: "
        f"{args.multimodal_agent}"
    )
    print()

    print_page_report(result)

    print()
    print_artifact_path(
        "Pages manifest",
        pages_path,
    )
    print_artifact_path(
        "Assets manifest",
        assets_path,
    )
    print_artifact_path(
        "Vision requests",
        artifacts.requests_path,
    )
    print_artifact_path(
        "Vision responses",
        artifacts.responses_path,
    )
    print_artifact_path(
        "Vision verifications",
        artifacts.verifications_path,
    )


def main() -> None:
    args = parse_arguments()
    result = render_material(args)

    material_manifest_dir = (
        create_manifest_directory(
            result=result,
            manifest_root=args.manifest_dir,
        )
    )

    pages_path, assets_path = (
        ManifestExporter().export(
            result=result,
            output_dir=material_manifest_dir,
        )
    )

    with multimodal_agent_context(
        args.multimodal_agent
    ) as agent:
        artifacts = MultimodalIngestionRunner().run(
            result=result,
            agent=agent,
            output_dir=material_manifest_dir,
        )

    print_summary(
        args=args,
        result=result,
        pages_path=pages_path,
        assets_path=assets_path,
        artifacts=artifacts,
    )


if __name__ == "__main__":
    main()