from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..db.session import get_db
from ..models.user import User
from ..models.oplog import OpLog
from ..schemas.user import UserOut
from .deps import get_current_admin
from ..utils.response import ok, fail

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    try:
        users = db.query(User).order_by(User.id.desc()).all()
        data = [
            {
                "id": u.id,
                "username": u.username,
                "is_admin": u.is_admin,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ]
        return ok(data)
    except Exception as e:
        return fail(str(e))


@router.get("/logs")
def list_logs(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    try:
        logs = db.query(OpLog).order_by(OpLog.id.desc()).limit(1000).all()
        data = [
            {
                "id": l.id,
                "user_id": l.user_id,
                "action": l.action,
                "path": l.path,
                "method": l.method,
                "detail": l.detail,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
        return ok(data)
    except Exception as e:
        return fail(str(e))
