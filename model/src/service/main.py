from src.service.api import create_app
from src.service.runtime import (
    build_pipeline_from_environment,
)


pipeline = build_pipeline_from_environment()
app = create_app(pipeline)