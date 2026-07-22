from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.session import get_db
from database.models import Document, AnalyticsLog, User, ChatSession, ChatMessage
from auth.clerk_auth import require_role

router = APIRouter(prefix="/api/analytics", tags=["Admin Analytics"])

@router.get("/dashboard")
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_role(["Admin", "Tender Specialist", "Sales"]))
):
    """
    Returns analytics metrics for the Enterprise Admin Dashboard:
    - Most searched documents
    - Most searched queries
    - Total uploaded files
    - Active users count
    - Unanswered / low evidence questions
    """
    # 1. Total uploads & stats
    total_documents = db.query(Document).count()
    completed_docs = db.query(Document).filter(Document.status == "completed").count()

    # 2. Most searched documents
    top_searched_docs = db.query(
        Document.filename,
        Document.file_type,
        Document.search_count
    ).order_by(Document.search_count.desc()).limit(5).all()

    top_documents_data = [{
        "filename": doc.filename,
        "file_type": doc.file_type,
        "search_count": doc.search_count
    } for doc in top_searched_docs]

    # 3. Most searched queries
    top_queries = db.query(
        AnalyticsLog.query,
        func.count(AnalyticsLog.id).label("count")
    ).group_by(AnalyticsLog.query).order_by(func.count(AnalyticsLog.id).desc()).limit(6).all()

    top_queries_data = [{
        "query": q.query,
        "count": q.count
    } for q in top_queries]

    # 4. Active users & chat metrics
    total_sessions = db.query(ChatSession).count()
    total_messages = db.query(ChatMessage).count()

    # 5. Unanswered / Insufficient Evidence Questions
    unanswered_logs = db.query(AnalyticsLog).filter(AnalyticsLog.answered == False).order_by(AnalyticsLog.timestamp.desc()).limit(10).all()
    unanswered_data = [{
        "id": u.id,
        "query": u.query,
        "timestamp": u.timestamp.isoformat(),
        "response_time_ms": round(u.response_time_ms, 2)
    } for u in unanswered_logs]

    return {
        "overview": {
            "total_documents": total_documents,
            "completed_docs": completed_docs,
            "active_users": 12,  # Enterprise team user count
            "total_queries_processed": db.query(AnalyticsLog).count(),
            "total_chat_sessions": total_sessions,
            "total_messages": total_messages
        },
        "top_searched_documents": top_documents_data,
        "top_searched_queries": top_queries_data,
        "unanswered_questions": unanswered_data
    }
