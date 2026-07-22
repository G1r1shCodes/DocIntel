import os
import shutil
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import Document, DocumentChunk, AnalyticsLog
from pipeline.ingestion import process_and_ingest_file
from auth.clerk_auth import get_current_user_from_token, require_role
from typing import List, Optional
import time
import logging
from database.schemas import DocumentResponse, DocumentChunksResponse, UploadResponse, GenericResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Uploads document (PDF, DOCX, XLSX, CSV, TXT, Image), parses, chunks, and indexes it.
    """
    # Role check: Viewers cannot upload
    if current_user.get("role") == "Viewer":
        raise HTTPException(status_code=403, detail="Viewer role cannot upload documents.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)
    file_ext = os.path.splitext(file.filename)[1].replace(".", "").lower()

    try:
        # Run ingestion pipeline
        ingest_res = process_and_ingest_file(file_path)

        # Save to DB
        db_doc = Document(
            filename=file.filename,
            file_type=file_ext,
            file_path=file_path,
            file_size=file_size,
            page_count=ingest_res.get("page_count", 1),
            chunk_count=ingest_res.get("chunk_count", 0),
            status="completed",
            uploaded_by=current_user.get("username", "Admin")
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)

        # Save chunk objects to DB
        for c in ingest_res.get("chunks", []):
            chunk_obj = DocumentChunk(
                document_id=db_doc.id,
                page_number=c.get("page_number", 1),
                heading=c.get("heading", ""),
                section=c.get("section", ""),
                is_table=c.get("is_table", False),
                text=c.get("text", ""),
                bbox_json=c.get("bbox", None)
            )
            db.add(chunk_obj)
        
        db.commit()

        return {
            "status": "success",
            "document_id": db_doc.id,
            "filename": db_doc.filename,
            "file_type": db_doc.file_type,
            "page_count": db_doc.page_count,
            "chunk_count": db_doc.chunk_count,
            "message": f"Successfully parsed and indexed {db_doc.filename}"
        }

    except Exception as e:
        logger.error(f"Error parsing document {file.filename}: {str(e)}", exc_info=True)
        db.rollback()
        # Upsert a single failed record per filename instead of appending a new
        # garbage row on every failed attempt.
        db_doc = db.query(Document).filter(Document.filename == file.filename).first()
        if db_doc:
            db_doc.file_type = file_ext
            db_doc.file_path = file_path
            db_doc.file_size = file_size
            db_doc.status = "failed"
            db_doc.uploaded_by = current_user.get("username", "Admin")
        else:
            db_doc = Document(
                filename=file.filename,
                file_type=file_ext,
                file_path=file_path,
                file_size=file_size,
                status="failed",
                uploaded_by=current_user.get("username", "Admin")
            )
            db.add(db_doc)
        db.commit()
        raise HTTPException(status_code=500, detail="An internal server error occurred during document parsing")

@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Returns list of all ingested documents.
    """
    docs = db.query(Document).order_by(Document.upload_date.desc()).offset(skip).limit(limit).all()
    return [{
        "id": d.id,
        "filename": d.filename,
        "file_type": d.file_type,
        "file_size": d.file_size,
        "page_count": d.page_count,
        "chunk_count": d.chunk_count,
        "upload_date": d.upload_date,
        "status": d.status,
        "search_count": d.search_count,
        "uploaded_by": d.uploaded_by
    } for d in docs]

@router.get("/{document_id}/chunks", response_model=DocumentChunksResponse)
def get_document_chunks(document_id: int, db: Session = Depends(get_db)):
    """
    Get all chunk definitions for a given document.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "chunks": [{
            "id": c.id,
            "page_number": c.page_number,
            "heading": c.heading,
            "section": c.section,
            "is_table": c.is_table,
            "text": c.text,
            "bbox": c.bbox_json
        } for c in chunks]
    }

@router.delete("/{document_id}", response_model=GenericResponse)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["Admin"]))
):
    """
    Delete document (Admin only).
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = doc.file_path
    db.delete(doc)
    db.commit()

    # Remove file only after the DB row is durably gone, so a commit failure
    # never leaves an orphaned record pointing at a deleted file.
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            logger.warning(f"Could not remove file for document {document_id}: {file_path}")

    return {"status": "success", "message": f"Document {document_id} deleted."}
