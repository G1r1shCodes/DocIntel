import os
import shutil
import hashlib
import uuid
from datetime import date
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import Document, DocumentChunk
from pipeline.ingestion import process_and_ingest_file
from pipeline.retrieval import retriever_instance
from auth.clerk_auth import get_current_user_from_token, require_role
from typing import List, Optional
import logging
from database.schemas import DocumentResponse, DocumentChunksResponse, UploadResponse, GenericResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["Documents"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
MAX_UPLOAD_SIZE = int(os.environ.get("MAX_UPLOAD_SIZE", "0")) or 50 * 1024 * 1024  # 50 MB default
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

    # --- File validation ---
    ext = os.path.splitext(file.filename)[1].lower()
    file_ext = ext.replace(".", "").lower()

    # Size check before writing anything
    file.file.seek(0, 2)  # Seek to end
    content_length = file.file.tell()
    file.file.seek(0)  # Reset
    if content_length > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE // (1024*1024)} MB."
        )

    # Generate a collision-safe internal filename with date-based subdirectory
    file_uuid = uuid.uuid4().hex
    sanitized_name = (
        file.filename
        .replace("..", "")
        .replace("/", "")
        .replace("\\", "")
        .strip(". ")
    )
    if not sanitized_name:
        sanitized_name = f"upload_{file_uuid[:8]}{ext}"
    date_prefix = date.today().strftime("%Y/%m")
    internal_filename = f"{date_prefix}/{file_uuid}_{sanitized_name}"
    file_path = os.path.join(UPLOAD_DIR, internal_filename.replace("/", os.sep))

    print(f"[Upload] Receiving file: {file.filename} -> {internal_filename}", flush=True)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)

    # Compute SHA-256 hash for dedup tracking
    file_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            file_hash.update(block)
    file_hex = file_hash.hexdigest()

    try:
        # Run ingestion pipeline
        print(f"[Upload] Processing and ingesting: {file_path}", flush=True)
        ingest_res = process_and_ingest_file(file_path)
        new_chunks = ingest_res.get("chunks", [])
        print(f"[Upload] Ingestion complete. Pages: {ingest_res.get('page_count')}, Chunks: {len(new_chunks)}", flush=True)

        # ── Fix chunk filenames to use the ORIGINAL user-facing name ─────────
        # The parser uses os.path.basename(file_path) which includes the
        # internal UUID prefix (e.g. "ab12..._Fullstack_AI_Engineer.pdf").
        # Overwrite with the original filename so downstream code
        # (compress_context, build_citations, update_chunk_metadata) shows
        # the friendly name the user uploaded.
        #
        # NOTE: slicing with [-n:] works correctly only when n > 0;
        # when n == 0, chunks[0:] would match EVERYTHING, so guard it.
        if new_chunks:
            for chunk in retriever_instance.chunks[-len(new_chunks):]:
                chunk.setdefault("metadata", {})["filename"] = file.filename

        # Save Document to DB (get an ID so chunk FK works)
        db_doc = Document(
            filename=file.filename,
            internal_filename=internal_filename,
            file_type=file_ext,
            file_path=file_path,
            file_hash=file_hex,
            file_size=file_size,
            page_count=ingest_res.get("page_count", 1),
            chunk_count=len(new_chunks),
            status="completed",
            uploaded_by=current_user.get("username", "Admin")
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)
        print(f"[Upload] Saved document to database with ID: {db_doc.id}", flush=True)

        # Save chunk objects to DB and capture generated chunk DB IDs
        chunk_objs: list[DocumentChunk] = []
        _pages_lookup = {p["page_number"]: p for p in ingest_res.get("_pages", [])}

        for idx, c in enumerate(new_chunks):
            page_number = c.get("page_number", 1)
            pg = _pages_lookup.get(page_number, {})

            chunk_obj = DocumentChunk(
                document_id=db_doc.id,
                page_number=page_number,
                chunk_index=idx,
                heading=c.get("heading", ""),
                section=c.get("section", ""),
                is_table=c.get("is_table", False),
                text=c.get("text", ""),
                bbox_json=c.get("bbox", None),
                page_width=pg.get("page_width"),
                page_height=pg.get("page_height"),
            )
            db.add(chunk_obj)
            chunk_objs.append(chunk_obj)

        # Single flush populates all auto-generated IDs
        db.flush()
        chunk_db_ids = [obj.id for obj in chunk_objs]

        db.commit()

        # Update retriever chunks with their database and document IDs so
        # downstream code (citations, deletion) can reference them.
        # Now that we've fixed metadata.filename to the original name above,
        # this function can correctly match chunks by filename.
        retriever_instance.update_chunk_metadata(
            filename=file.filename,
            db_ids=chunk_db_ids,
            document_id=db_doc.id,
        )

        return {
            "status": "success",
            "document_id": db_doc.id,
            "filename": db_doc.filename,
            "file_type": db_doc.file_type,
            "page_count": db_doc.page_count,
            "chunk_count": db_doc.chunk_count,
            "file_hash": file_hex,
            "message": f"Successfully parsed and indexed {db_doc.filename}"
        }

    except Exception as e:
        logger.error(f"Error parsing document {file.filename}: {str(e)}", exc_info=True)
        db.rollback()
        # Clean up the uploaded file on failure
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail="An internal server error occurred during document parsing")


@router.post("/upload-legacy", include_in_schema=False)
async def upload_document_legacy(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """Legacy upload endpoint — kept for backward compatibility during migration."""
    if current_user.get("role") == "Viewer":
        raise HTTPException(status_code=403, detail="Viewer role cannot upload documents.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = os.path.getsize(file_path)
    file_ext = os.path.splitext(file.filename)[1].replace(".", "").lower()

    ingest_res = process_and_ingest_file(file_path)

    db_doc = Document(
        filename=file.filename,
        internal_filename=file.filename,
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
        "uploaded_by": d.uploaded_by,
        "file_hash": d.file_hash
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
            "bbox": c.bbox_json,
            "page_width": c.page_width,
            "page_height": c.page_height
        } for c in chunks]
    }

from fastapi.responses import FileResponse


@router.get("/{document_id}/file")
async def get_document_file(
    document_id: int,
    db: Session = Depends(get_db),
):
    """
    Serve the original uploaded file for inline display (e.g. PDF viewer).
    Uses the internal storage path so UUID-based filenames are transparent.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    media_type = "application/pdf" if doc.file_type == "pdf" else "application/octet-stream"
    return FileResponse(
        path=doc.file_path,
        filename=doc.filename,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


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
    filename = doc.filename
    doc_id = doc.id
    db.delete(doc)
    db.commit()

    # Remove from hybrid retriever — prefer document_id when available,
    # fall back to filename for chunks indexed before Phase 2 migration.
    removed = retriever_instance.remove_chunks_by_document_id(doc_id)
    if not removed:
        retriever_instance.remove_chunks_by_filename(filename)

    # Remove file only after the DB row is durably gone, so a commit failure
    # never leaves an orphaned record pointing at a deleted file.
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            logger.warning(f"Could not remove file for document {document_id}: {file_path}")

    return {"status": "success", "message": f"Document {document_id} deleted."}
