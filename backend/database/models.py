from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime, Float, JSON
from sqlalchemy.orm import relationship
from .session import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    clerk_id = Column(String, unique=True, index=True, nullable=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, index=True, nullable=True)
    role = Column(String, default="Viewer")  # Admin, Tender Specialist, Sales, Engineer, Viewer
    created_at = Column(DateTime, default=datetime.utcnow)

    chat_sessions = relationship("ChatSession", back_populates="user")
    bookmarks = relationship("Bookmark", back_populates="user")
    analytics_logs = relationship("AnalyticsLog", back_populates="user")

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)                     # Original user-facing filename
    internal_filename = Column(String, nullable=True)         # UUID-based storage name
    file_type = Column(String)                                # pdf, docx, xlsx, csv, txt, image
    file_path = Column(String)                                # Full path on disk
    file_hash = Column(String, nullable=True, index=True)     # SHA-256 hex digest for dedup
    file_size = Column(Integer, default=0)
    page_count = Column(Integer, default=1)
    chunk_count = Column(Integer, default=0)
    upload_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="completed")             # processing, completed, failed
    search_count = Column(Integer, default=0)
    uploaded_by = Column(String, default="Admin")

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    page_number = Column(Integer, default=1)
    chunk_index = Column(Integer, default=0)
    heading = Column(String, nullable=True)
    section = Column(String, nullable=True)
    is_table = Column(Boolean, default=False)
    text = Column(Text)
    bbox_json = Column(JSON, nullable=True)
    page_width = Column(Float, nullable=True)    # For bbox coordinate scaling on frontend
    page_height = Column(Float, nullable=True)

    document = relationship("Document", back_populates="chunks")

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    title = Column(String, default="New Conversation")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"))
    role = Column(String)  # user, assistant
    content = Column(Text)
    faithfulness_status = Column(String, default="FAITHFUL")  # FAITHFUL, UNVERIFIED, INSUFFICIENT_EVIDENCE
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("ChatSession", back_populates="messages")
    citations = relationship("Citation", back_populates="message", cascade="all, delete-orphan")

class Citation(Base):
    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id"))
    chunk_id = Column(Integer, ForeignKey("document_chunks.id"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)

    # Denormalised fields derived from the chunk at query time so that
    # serialisation does not require a second join.  These are *intentionally*
    # cached copies, not the source of truth.
    chunk_index = Column(Integer, default=0)
    filename = Column(String)
    page_number = Column(Integer)
    heading = Column(String, nullable=True)
    section = Column(String, nullable=True)
    text_snippet = Column(Text)

    # Single JSON bounding-box object: {"x0": …, "y0": …, "x1": …, "y1": …}
    bbox = Column(JSON, nullable=True)

    # Page dimensions at render time so the frontend can scale coordinates
    page_width = Column(Float, nullable=True)
    page_height = Column(Float, nullable=True)

    message = relationship("ChatMessage", back_populates="citations")
    chunk = relationship("DocumentChunk")

class Bookmark(Base):
    __tablename__ = "bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    query = Column(String)
    answer = Column(Text)
    filename = Column(String, nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="bookmarks")

class AnalyticsLog(Base):
    __tablename__ = "analytics_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    query = Column(String)
    document_filename = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    answered = Column(Boolean, default=True)
    response_time_ms = Column(Float, default=0.0)

    user = relationship("User", back_populates="analytics_logs")
