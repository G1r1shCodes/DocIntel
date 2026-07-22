from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import Bookmark
from auth.clerk_auth import get_current_user_from_token

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])

class CreateBookmarkRequest(BaseModel):
    query: str
    answer: str
    filename: Optional[str] = None
    note: Optional[str] = None

@router.post("/")
def create_bookmark(
    req: CreateBookmarkRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Save an answer/citation as a user bookmark for later lookup.
    """
    bm = Bookmark(
        query=req.query,
        answer=req.answer,
        filename=req.filename,
        note=req.note
    )
    db.add(bm)
    db.commit()
    db.refresh(bm)

    return {
        "status": "success",
        "bookmark_id": bm.id,
        "query": bm.query,
        "filename": bm.filename,
        "created_at": bm.created_at.isoformat()
    }

@router.get("/")
def list_bookmarks(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get saved bookmarks with optional keyword search filter.
    """
    query_builder = db.query(Bookmark)
    if search:
        query_builder = query_builder.filter(
            Bookmark.query.ilike(f"%{search}%") | Bookmark.answer.ilike(f"%{search}%") | Bookmark.note.ilike(f"%{search}%")
        )

    bookmarks = query_builder.order_by(Bookmark.created_at.desc()).all()
    return [{
        "id": b.id,
        "query": b.query,
        "answer": b.answer,
        "filename": b.filename,
        "note": b.note,
        "created_at": b.created_at.isoformat()
    } for b in bookmarks]

@router.delete("/{bookmark_id}")
def delete_bookmark(bookmark_id: int, db: Session = Depends(get_db)):
    """
    Delete a saved bookmark.
    """
    bm = db.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bm)
    db.commit()
    return {"status": "success", "message": f"Bookmark {bookmark_id} deleted."}
