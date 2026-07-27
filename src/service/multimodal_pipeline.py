from schemas.vision_contract import (
    VisionRequest,
    VisionResponse,
)
from src.agents.multimodal_agent import MultimodalAgent


class MultimodalPipeline:
    def __init__(
        self,
        agent: MultimodalAgent,
    ) -> None:
        self.agent = agent

    def process(
        self,
        requests: list[VisionRequest],
    ) -> list[VisionResponse]:
        self._validate_unique_request_ids(requests)

        responses: list[VisionResponse] = []

        for request in requests:
            response = self.agent.analyze(request)

            self._validate_response_link(
                request=request,
                response=response,
            )

            responses.append(response)

        return responses

    @staticmethod
    def _validate_unique_request_ids(
        requests: list[VisionRequest],
    ) -> None:
        request_ids = [
            request.request_id
            for request in requests
        ]

        if len(request_ids) != len(set(request_ids)):
            raise ValueError(
                "Duplicate VisionRequest request_id"
            )

    @staticmethod
    def _validate_response_link(
        request: VisionRequest,
        response: VisionResponse,
    ) -> None:
        if response.request_id != request.request_id:
            raise ValueError(
                "VisionResponse request_id does not "
                "match VisionRequest"
            )

        if response.material_id != request.material_id:
            raise ValueError(
                "VisionResponse material_id does not "
                "match VisionRequest"
            )

        if response.page_number != request.page_number:
            raise ValueError(
                "VisionResponse page_number does not "
                "match VisionRequest"
            )

        if response.asset_id != request.asset_id:
            raise ValueError(
                "VisionResponse asset_id does not "
                "match VisionRequest"
            )