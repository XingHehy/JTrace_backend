from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, timedelta
from ..db.session import get_db
from ..models.user import User
from ..models.oplog import OpLog
from ..models.footprint import Footprint
from ..models.comment import Comment
from ..models.footprint_type import FootprintType
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
                "nickname": u.nickname,
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


@router.get("/stats")
def get_system_stats(
    days: int = Query(30, description="统计天数"),
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """获取系统统计信息"""
    try:
        # 计算时间范围
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 基础统计
        total_users = db.query(func.count(User.id)).scalar()
        total_footprints = db.query(func.count(Footprint.id)).scalar()
        total_comments = db.query(func.count(Comment.id)).filter(Comment.is_deleted == 0).scalar()
        total_types = db.query(func.count(FootprintType.id)).scalar()
        
        # 活跃用户（最近7天有登录）
        week_ago = now - timedelta(days=7)
        active_users = db.query(func.count(User.id)).filter(
            User.last_login >= week_ago
        ).scalar()
        
        # 今日新增
        today_new_users = db.query(func.count(User.id)).filter(
            User.created_at >= today_start
        ).scalar()
        
        today_new_footprints = db.query(func.count(Footprint.id)).filter(
            Footprint.created_at >= today_start
        ).scalar()
        
        today_new_comments = db.query(func.count(Comment.id)).filter(
            and_(Comment.created_at >= today_start, Comment.is_deleted == 0)
        ).scalar()
        
        # 公开/私有足迹统计
        public_footprints = db.query(func.count(Footprint.id)).filter(
            Footprint.is_public == 1
        ).scalar()
        
        private_footprints = db.query(func.count(Footprint.id)).filter(
            Footprint.is_public == 0
        ).scalar()
        
        # 用户状态统计
        active_users_count = db.query(func.count(User.id)).filter(
            User.status == 1
        ).scalar()
        
        inactive_users_count = db.query(func.count(User.id)).filter(
            User.status == 0
        ).scalar()
        
        # 按类型统计足迹
        footprints_by_type = db.query(
            FootprintType.name,
            func.count(Footprint.id).label('count')
        ).join(Footprint, FootprintType.id == Footprint.type_id)\
         .group_by(FootprintType.id, FootprintType.name)\
         .order_by(func.count(Footprint.id).desc())\
         .all()
        
        # 最近操作日志
        recent_logs = db.query(OpLog).order_by(OpLog.id.desc()).limit(10).all()
        
        data = {
            "overview": {
                "total_users": total_users or 0,
                "total_footprints": total_footprints or 0,
                "total_comments": total_comments or 0,
                "total_types": total_types or 0,
                "active_users": active_users or 0,
                "active_users_count": active_users_count or 0,
                "inactive_users_count": inactive_users_count or 0,
                "public_footprints": public_footprints or 0,
                "private_footprints": private_footprints or 0
            },
            "today": {
                "new_users": today_new_users or 0,
                "new_footprints": today_new_footprints or 0,
                "new_comments": today_new_comments or 0
            },
            "footprints_by_type": [
                {"name": row[0], "count": row[1]} 
                for row in footprints_by_type
            ],
            "recent_logs": [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "path": log.path,
                    "method": log.method,
                    "detail": log.detail,
                    "created_at": log.created_at.isoformat() if log.created_at else None
                }
                for log in recent_logs
            ]
        }
        
        return ok(data)
    except Exception as e:
        return fail(str(e))


@router.get("/users/search")
def search_users(
    q: Optional[str] = Query(None, description="搜索用户名或邮箱"),
    status: Optional[int] = Query(None, description="用户状态筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db), 
    admin: User = Depends(get_current_admin)
):
    """搜索用户"""
    try:
        query = db.query(User)
        
        # 搜索条件
        if q:
            # 使用COALESCE处理NULL值
            search_filter = (
                User.username.like(f"%{q}%") |
                (User.nickname.isnot(None) & User.nickname.like(f"%{q}%")) |
                (User.email.isnot(None) & User.email.like(f"%{q}%"))
            )
            query = query.filter(search_filter)
        
        # 状态筛选
        if status is not None:
            query = query.filter(User.status == status)
        
        # 总数
        total = query.count()
        
        # 分页
        users = query.order_by(User.id.desc()).offset(skip).limit(limit).all()
        
        data = {
            "total": total,
            "users": [
                {
                    "id": u.id,
                    "username": u.username,
                    "nickname": u.nickname,
                    "email": u.email,
                    "is_admin": u.id == 1,
                    "is_active": u.status == 1,
                    "status": u.status,
                    "bio": u.bio,
                    "avatar": u.avatar,
                    "gender": u.gender,
                    "last_login": u.last_login.isoformat() if u.last_login else None,
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                    "updated_at": u.updated_at.isoformat() if u.updated_at else None,
                }
                for u in users
            ]
        }
        
        return ok(data)
    except Exception as e:
        return fail(str(e))
