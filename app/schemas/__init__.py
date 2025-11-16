"""
Pydantic Schemas
"""

from .document import (
    DocumentBase,
    DocumentSummaryBase,
    DocumentWithSummary,
    DocumentListResponse,
    DocumentDetailResponse,
    DocumentSummaryResponse,
)

from .conversation import (
    MessageBase,
    TokenUsage,
    ConversationBase,
    ConversationListItem,
    ConversationWithMessages,
    PrimaryDocumentInfo,
    CreateConversationRequest,
    SendMessageRequest,
    ConversationListResponse,
    ConversationDetailResponse,
    MessageListResponse,
    MessageCreateResponse,
)

__all__ = [
    # Document schemas
    "DocumentBase",
    "DocumentSummaryBase",
    "DocumentWithSummary",
    "DocumentListResponse",
    "DocumentDetailResponse",
    "DocumentSummaryResponse",
    # Conversation schemas
    "MessageBase",
    "TokenUsage",
    "ConversationBase",
    "ConversationListItem",
    "ConversationWithMessages",
    "PrimaryDocumentInfo",
    "CreateConversationRequest",
    "SendMessageRequest",
    "ConversationListResponse",
    "ConversationDetailResponse",
    "MessageListResponse",
    "MessageCreateResponse",
]