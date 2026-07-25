import json
from pathlib import Path

from schemas.material_contract import (
    MaterialFileType,
    MaterialStatusResponse,
    MaterialStoredProcessingStatus,
)
from schemas.material_processing_contract import (
    MaterialProcessingResponse,
    MaterialProcessingStatus,
)
from src.agents.multimodal_agent import MultimodalAgent
from src.agents.multimodal_client import MultimodalClientError
from src.ingestion.manifest_exporter import ManifestExporter
from src.ingestion.image_ingestor import ImageIngestor
from src.ingestion.material_storage import (
    MaterialStorage,
    MaterialStorageError,
)
from src.ingestion.pdf_ingestor import PDFIngestor
from src.service.multimodal_ingestion_runner import (
    MultimodalIngestionRunner,
)


class MaterialProcessingError(RuntimeError):
    pass


class MaterialProcessingProviderError(MaterialProcessingError):
    pass


class MaterialProcessingService:
    def __init__(
        self,
        storage: MaterialStorage,
        work_root: str | Path,
        *,
        ingestor: PDFIngestor | None = None,
        image_ingestor: ImageIngestor | None = None,
        manifest_exporter: ManifestExporter | None = None,
        runner: MultimodalIngestionRunner | None = None,
    ) -> None:
        self.storage = storage
        self.work_root = Path(work_root)
        self.ingestor = ingestor or PDFIngestor()
        self.image_ingestor = image_ingestor or ImageIngestor()
        self.manifest_exporter = (
            manifest_exporter or ManifestExporter()
        )
        self.runner = runner or MultimodalIngestionRunner()

    def process(
        self,
        material_id: str,
        agent: MultimodalAgent | None,
    ) -> MaterialProcessingResponse:
        try:
            material = self.storage.get(material_id)
        except MaterialStorageError as exc:
            raise MaterialProcessingError(str(exc)) from exc

        artifact_dir = self._artifact_dir(material.material_id)

        if material.file_type not in {
            MaterialFileType.PDF,
            MaterialFileType.PNG,
            MaterialFileType.JPEG,
        }:
            return self._failed_response(
                material_id=material.material_id,
                file_type=material.file_type,
                artifact_dir=artifact_dir,
                error=(
                    "Unsupported material file type for "
                    "this processing step"
                ),
            )

        try:
            if material.file_type is MaterialFileType.PDF:
                render_result = (
                    self.ingestor.render_pages_with_assets(
                        pdf_path=material.stored_path,
                        material_id=material.material_id,
                        output_dir=artifact_dir / "rendered",
                    )
                )
            else:
                render_result = (
                    self.image_ingestor.render_image_as_page(
                        image_path=material.stored_path,
                        material_id=material.material_id,
                        mime_type=material.mime_type,
                    )
                )

            pages_path, assets_path = self.manifest_exporter.export(
                result=render_result,
                output_dir=artifact_dir,
            )

            run_artifacts = self.runner.run(
                result=render_result,
                agent=agent,
                output_dir=artifact_dir,
            )
        except MultimodalClientError as exc:
            raise MaterialProcessingProviderError(
                "External multimodal provider failed"
            ) from exc
        except Exception as exc:
            return self._failed_response(
                material_id=material.material_id,
                file_type=material.file_type,
                artifact_dir=artifact_dir,
                error=str(exc),
            )

        return MaterialProcessingResponse(
            material_id=material.material_id,
            file_type=material.file_type,
            status=self._status_from_counts(
                needs_review_count=(
                    run_artifacts.needs_review_count
                ),
                rejected_count=run_artifacts.rejected_count,
            ),
            total_pages=len(render_result.pages),
            total_vision_requests=run_artifacts.total_requests,
            total_vision_responses=run_artifacts.total_responses,
            verified_count=run_artifacts.verified_count,
            needs_review_count=(
                run_artifacts.needs_review_count
            ),
            rejected_count=run_artifacts.rejected_count,
            pages_manifest_path=str(pages_path.resolve()),
            assets_manifest_path=str(assets_path.resolve()),
            vision_requests_path=str(
                run_artifacts.requests_path.resolve()
            ),
            vision_responses_path=self._optional_resolved_path(
                run_artifacts.responses_path
            ),
            vision_verifications_path=self._optional_resolved_path(
                run_artifacts.verifications_path
            ),
        )

    def get_status(
        self,
        material_id: str,
    ) -> MaterialStatusResponse:
        material = self._get_material_or_raise_processing_error(
            material_id
        )
        status_path = self._status_path(material.material_id)

        if not status_path.is_file():
            return self._empty_status_response(
                material=material,
                processing_status=(
                    MaterialStoredProcessingStatus.STORED
                ),
            )

        try:
            return MaterialStatusResponse.model_validate_json(
                status_path.read_text(encoding="utf-8")
            )
        except Exception as exc:
            raise MaterialProcessingError(
                "Stored material processing status is invalid"
            ) from exc

    def mark_processing(
        self,
        material_id: str,
    ) -> MaterialStatusResponse:
        material = self._get_material_or_raise_processing_error(
            material_id
        )
        response = self._empty_status_response(
            material=material,
            processing_status=(
                MaterialStoredProcessingStatus.PROCESSING
            ),
        )
        self._write_status(response)

        return response

    def persist_result(
        self,
        result: MaterialProcessingResponse,
    ) -> MaterialStatusResponse:
        material = self._get_material_or_raise_processing_error(
            result.material_id
        )
        response = MaterialStatusResponse(
            material_id=result.material_id,
            file_type=result.file_type,
            processing_status=self._stored_status_from_result(
                result
            ),
            original_filename=material.original_filename,
            stored_path=material.stored_path,
            total_pages=result.total_pages,
            total_assets=self._read_total_assets(
                result.assets_manifest_path
            ),
            total_vision_requests=(
                result.total_vision_requests
            ),
            total_vision_responses=(
                result.total_vision_responses
            ),
            verified_count=result.verified_count,
            needs_review_count=result.needs_review_count,
            rejected_count=result.rejected_count,
            error_message=result.error,
        )
        self._write_status(response)

        return response

    def persist_failed(
        self,
        material_id: str,
        error_message: str,
    ) -> MaterialStatusResponse:
        material = self._get_material_or_raise_processing_error(
            material_id
        )
        response = self._empty_status_response(
            material=material,
            processing_status=(
                MaterialStoredProcessingStatus.FAILED
            ),
            error_message=error_message,
        )
        self._write_status(response)

        return response

    def _artifact_dir(
        self,
        material_id: str,
    ) -> Path:
        return self.work_root / material_id

    def _status_path(
        self,
        material_id: str,
    ) -> Path:
        return (
            self.storage.storage_root
            / material_id
            / "processing_status.json"
        )

    def _write_status(
        self,
        response: MaterialStatusResponse,
    ) -> None:
        status_path = self._status_path(response.material_id)
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(
            response.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

    def _get_material_or_raise_processing_error(
        self,
        material_id: str,
    ):
        try:
            return self.storage.get(material_id)
        except MaterialStorageError as exc:
            raise MaterialProcessingError(str(exc)) from exc

    @staticmethod
    def _default_manifest_paths(
        artifact_dir: Path,
    ) -> dict[str, Path]:
        return {
            "pages": artifact_dir / "pages.json",
            "assets": artifact_dir / "assets.json",
            "vision_requests": (
                artifact_dir / "vision_requests.json"
            ),
        }

    @staticmethod
    def _empty_status_response(
        *,
        material,
        processing_status: MaterialStoredProcessingStatus,
        error_message: str | None = None,
    ) -> MaterialStatusResponse:
        return MaterialStatusResponse(
            material_id=material.material_id,
            file_type=material.file_type,
            processing_status=processing_status,
            original_filename=material.original_filename,
            stored_path=material.stored_path,
            total_pages=0,
            total_assets=0,
            total_vision_requests=0,
            total_vision_responses=0,
            verified_count=0,
            needs_review_count=0,
            rejected_count=0,
            error_message=error_message,
        )

    @classmethod
    def _failed_response(
        cls,
        *,
        material_id: str,
        file_type: MaterialFileType,
        artifact_dir: Path,
        error: str,
    ) -> MaterialProcessingResponse:
        paths = cls._default_manifest_paths(artifact_dir)

        return MaterialProcessingResponse(
            material_id=material_id,
            file_type=file_type,
            status=MaterialProcessingStatus.FAILED,
            total_pages=0,
            total_vision_requests=0,
            total_vision_responses=0,
            verified_count=0,
            needs_review_count=0,
            rejected_count=0,
            pages_manifest_path=str(paths["pages"].resolve()),
            assets_manifest_path=str(paths["assets"].resolve()),
            vision_requests_path=str(
                paths["vision_requests"].resolve()
            ),
            error=error,
        )

    @staticmethod
    def _stored_status_from_result(
        result: MaterialProcessingResponse,
    ) -> MaterialStoredProcessingStatus:
        if result.status is MaterialProcessingStatus.FAILED:
            return MaterialStoredProcessingStatus.FAILED

        if result.status in {
            MaterialProcessingStatus.NEEDS_REVIEW,
            MaterialProcessingStatus.REJECTED,
        }:
            return MaterialStoredProcessingStatus.NEEDS_REVIEW

        return MaterialStoredProcessingStatus.PROCESSED

    @staticmethod
    def _read_total_assets(
        assets_manifest_path: str,
    ) -> int:
        try:
            payload = json.loads(
                Path(assets_manifest_path).read_text(
                    encoding="utf-8"
                )
            )
            total_assets = payload.get("total_assets", 0)

            if isinstance(total_assets, int) and total_assets >= 0:
                return total_assets

        except Exception:
            pass

        return 0

    @staticmethod
    def _status_from_counts(
        *,
        needs_review_count: int,
        rejected_count: int,
    ) -> MaterialProcessingStatus:
        if rejected_count:
            return MaterialProcessingStatus.REJECTED

        if needs_review_count:
            return MaterialProcessingStatus.NEEDS_REVIEW

        return MaterialProcessingStatus.COMPLETED

    @staticmethod
    def _optional_resolved_path(
        path: Path | None,
    ) -> str | None:
        if path is None:
            return None

        return str(path.resolve())
