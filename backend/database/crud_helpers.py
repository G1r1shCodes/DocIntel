from sqlalchemy.orm import Session
from database.models import User


def get_or_create_user(db: Session, current_user: dict) -> User:
    """
    Resolve the authenticated principal (token user id string) to a persistent
    User row, creating it on first sight. Returns the row so callers can scope
    ownership by the integer primary key used across FK columns.
    """
    clerk_id = current_user.get("user_id") or "user_default_1"
    user = db.query(User).filter(User.clerk_id == clerk_id).first()
    if not user:
        user = User(
            clerk_id=clerk_id,
            username=current_user.get("username", clerk_id),
            role=current_user.get("role", "Viewer"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
