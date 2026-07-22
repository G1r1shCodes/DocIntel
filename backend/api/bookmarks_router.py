from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session
from database.session import get_db
from database.models import Bookmark
from auth.clerk_auth import get_current_user_from_token
from database.crud_helpers import get_or_create_user
from database.schemas import BookmarkResponse, GenericResponse

router = APIRouter(prefix="/api/bookmarks", tags=["Bookmarks"])

class CreateBookmarkRequest(BaseModel):
    query: str
    answer: str
    filename: Optional[str] = None
    note: Optional[str] = None

@router.post("/", response_model=BookmarkResponse)
def create_bookmark(
    req: CreateBookmarkRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Save an answer/citation as a user bookmark for later lookup.
    """
    db_user = get_or_create_user(db, current_user)
    bm = Bookmark(
        user_id=db_user.id,
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
        "id": bm.id,
        "query": bm.query,
        "answer": bm.answer,
        "filename": bm.filename,
        "note": bm.note,
        "created_at": bm.created_at
    }

@router.get("/", response_model=List[BookmarkResponse])
def list_bookmarks(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Get saved bookmarks with optional keyword search filter.
    """
    db_user = get_or_create_user(db, current_user)
    query_builder = db.query(Bookmark).filter(Bookmark.user_id == db_user.id)
    if search:
        query_builder = query_builder.filter(
            Bookmark.query.ilike(f"%{search}%") | Bookmark.answer.ilike(f"%{search}%") | Bookmark.note.ilike(f"%{search}%")
        )

    bookmarks = query_builder.order_by(Bookmark.created_at.desc()).offset(skip).limit(limit).all()
    return [{
        "id": b.id,
        "query": b.query,
        "answer": b.answer,
        "filename": b.filename,
        "note": b.note,
        "created_at": b.created_at
    } for b in bookmarks]

@router.delete("/{bookmark_id}", response_model=GenericResponse)
def delete_bookmark(
    bookmark_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_from_token)
):
    """
    Delete a saved bookmark (owner only).
    """
    db_user = get_or_create_user(db, current_user)
    bm = db.query(Bookmark).filter(
        Bookmark.id == bookmark_id,
        Bookmark.user_id == db_user.id
    ).first()
    if not bm:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    db.delete(bm)
    db.commit()
    return {"status": "success", "message": f"Bookmark {bookmark_id} deleted."}
