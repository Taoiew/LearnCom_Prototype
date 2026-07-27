from src.agents.llm_client import LLMConfig, OpenAICompatibleClient
from src.service.api import create_app
from src.service.rubric_service import RubricService
from src.service.runtime import ModelRuntimeConfig, build_pipeline
from src.service.session_analytics_service import SessionAnalyticsService


config = ModelRuntimeConfig.from_environment()
shared_llm_client = None

if config.mode == "verified_kb":
    shared_llm_client = OpenAICompatibleClient(
        LLMConfig(
            base_url=config.local_llm_base_url,
            model=config.local_llm_model,
            api_key=config.local_llm_api_key,
            timeout_seconds=config.llm_timeout_seconds,
        )
    )

pipeline = build_pipeline(
    config=config,
    llm_client=shared_llm_client,
)

app = create_app(
    pipeline,
    rubric_service=RubricService(
        llm_client=shared_llm_client,
    ),
    analytics_service=SessionAnalyticsService(),
)
