from src.retrieval.conversation_knowledge_store import (
    ConversationKnowledgeStore,
)
from src.retrieval.course_knowledge_store import (
    CourseKnowledgeStore,
)
from src.service.api import create_app
from src.service.conversation_attachment_service import (
    ConversationAttachmentService,
)
from src.service.runtime import (
    build_pipeline_from_environment,
)


course_knowledge_store = CourseKnowledgeStore()

conversation_knowledge_store = (
    ConversationKnowledgeStore()
)

pipeline = build_pipeline_from_environment(
    course_store=course_knowledge_store,
    conversation_store=conversation_knowledge_store,
)

conversation_attachment_service = (
    ConversationAttachmentService(
        base_dir="data/chat_attachments",
        conversation_store=(
            conversation_knowledge_store
        ),
    )
)

app = create_app(
    pipeline=pipeline,
    conversation_attachment_service=(
        conversation_attachment_service
    ),
)
