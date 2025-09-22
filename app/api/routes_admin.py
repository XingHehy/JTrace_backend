from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from ..db.session import get_db
from ..models.user import User
from ..models.oplog import OpLog
from ..schemas.user import UserOut
from .deps import get_current_admin
from ..utils.response import ok, fail
from pydantic import BaseModel

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    try:
        users = db.query(User).order_by(User.id.desc()).all()
        data = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "is_admin": u.id == 1,  # 管理员判断基于ID=1
                "is_active": u.status == 1,  # 激活状态基于status字段
                "status": u.status,
                "bio": u.bio,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "updated_at": u.updated_at.isoformat() if u.updated_at else None,
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


class UpdateUserStatusRequest(BaseModel):
    status: int


@router.put("/users/{user_id}/status")
def update_user_status(
    user_id: int, 
    request: UpdateUserStatusRequest,
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    try:
        # 不允许修改管理员自己的状态
        if user_id == 1:
            return fail("不能修改管理员账户状态")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return fail("用户不存在")
        
        user.status = request.status
        db.commit()
        
        return ok({"id": user.id, "status": user.status}, "用户状态更新成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))
