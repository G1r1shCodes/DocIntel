from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

class Bbox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

class CitationResponse(BaseModel):
    citation_id: str
    chunk_id: Optional[int] = None
    document_id: Optional[int] = None
    filename: str
    page_number: int
    heading: Optional[str] = None
    section: Optional[str] = None
    text_snippet: str
    bbox: Optional[Bbox] = None
    page_width: Optional[float] = None
    page_height: Optional[float] = None

class ChatMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    faithfulness_status: str
    timestamp: datetime
    citations: List[CitationResponse] = []

class ChatSessionListResponse(BaseModel):
    id: int
    title: str
    created_at: datetime
    message_count: int

class ChatSessionResponse(BaseModel):
    session_id: int
    title: str
    messages: List[ChatMessageResponse]

class ChatQueryResponse(BaseModel):
    session_id: int
    message_id: Optional[int] = None
    answer: str
    faithfulness_status: str
    citations: List[CitationResponse] = []
    retrieved_chunks_count: int
    response_time_ms: Optional[float] = None

class DocumentChunkResponse(BaseModel):
    id: int
    page_number: int
    heading: Optional[str] = None
    section: Optional[str] = None
    is_table: bool
    text: str
    bbox: Optional[Dict[str, Any]] = None
    page_width: Optional[float] = None
    page_height: Optional[float] = None

class DocumentChunksResponse(BaseModel):
    document_id: int
    filename: str
    chunks: List[DocumentChunkResponse]

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    file_size: int
    page_count: int
    chunk_count: int
    upload_date: datetime
    status: str
    search_count: int
    uploaded_by: str
    file_hash: Optional[str] = None

class BookmarkResponse(BaseModel):
    id: int
    query: str
    answer: str
    filename: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

class TopDocument(BaseModel):
    filename: str
    file_type: str
    search_count: int

class TopQuery(BaseModel):
    query: str
    count: int

class UnansweredQuestion(BaseModel):
    id: int
    query: str
    timestamp: datetime
    response_time_ms: float

class AnalyticsOverview(BaseModel):
    total_documents: int
    completed_docs: int
    active_users: int
    total_queries_processed: int
    total_chat_sessions: int
    total_messages: int

class AnalyticsDashboardResponse(BaseModel):
    overview: AnalyticsOverview
    top_searched_documents: List[TopDocument]
    top_searched_queries: List[TopQuery]
    unanswered_questions: List[UnansweredQuestion]

class UploadResponse(BaseModel):
    status: str
    document_id: int
    filename: str
    file_type: str
    page_count: int
    chunk_count: int
    file_hash: Optional[str] = None
    message: str

class GenericResponse(BaseModel):
    status: str
    message: str
