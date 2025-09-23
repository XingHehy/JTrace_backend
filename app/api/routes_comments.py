from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from ..db.session import get_db
from ..models import Comment, CommentImage, Footprint, User
from ..schemas.comment import CommentCreate, CommentOut, CommentUpdate
from .deps import get_current_user
from ..utils.response import ok, fail
from ..utils.avatar_utils import convert_avatar_url
from ..utils.media_utils import generate_media_url

router = APIRouter(prefix="/comments", tags=["comments"])


@router.get("/footprint/{footprint_id}")
def list_footprint_comments(
    footprint_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """获取足迹的评论列表"""
    try:
        # 检查足迹是否存在且有权访问
        footprint = db.query(Footprint).filter(
            Footprint.id == footprint_id,
            or_(
                Footprint.user_id == user.id,
                Footprint.is_public == 1
            )
        ).first()
        
        if not footprint:
            return fail("足迹不存在或无权访问")
        
        # 获取评论（只获取顶级评论，子评论通过关系加载）
        comments = (
            db.query(Comment)
            .options(
                joinedload(Comment.user),
                joinedload(Comment.images),
                joinedload(Comment.children).joinedload(Comment.user),
                joinedload(Comment.children).joinedload(Comment.images)
            )
            .filter(
                Comment.footprint_id == footprint_id,
                Comment.parent_id.is_(None),
                Comment.is_deleted == 0
            )
            .order_by(Comment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return ok([_comment_to_dict(comment) for comment in comments])
    except Exception as e:
        return fail(str(e))


@router.post("/footprint/{footprint_id}")
def create_comment(
    footprint_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """为足迹创建评论"""
    try:
        # 检查足迹是否存在且有权访问
        footprint = db.query(Footprint).filter(
            Footprint.id == footprint_id,
            or_(
                Footprint.user_id == user.id,
                Footprint.is_public == 1
            )
        ).first()
        
        if not footprint:
            return fail("足迹不存在或无权访问")
        
        # 如果是回复评论，检查父评论是否存在
        if data.parent_id:
            parent_comment = db.query(Comment).filter(
                Comment.id == data.parent_id,
                Comment.footprint_id == footprint_id,
                Comment.is_deleted == 0
            ).first()
            if not parent_comment:
                return fail("父评论不存在")
        
        # 创建评论
        comment = Comment(
            footprint_id=footprint_id,
            user_id=user.id,
            parent_id=data.parent_id,
            content=data.content
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        
        # 处理图片
        if data.images:
            for img_data in data.images:
                image = CommentImage(
                    comment_id=comment.id,
                    image_url=img_data.image_url,
                    description=img_data.description,
                    sort_order=img_data.sort_order
                )
                db.add(image)
        
        db.commit()
        
        # 重新查询以获取完整数据
        comment = (
            db.query(Comment)
            .options(
                joinedload(Comment.user),
                joinedload(Comment.images)
            )
            .filter(Comment.id == comment.id)
            .first()
        )
        
        return ok(_comment_to_dict(comment), "评论成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


# 移除评论更新接口 - 评论发布后不允许修改


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """删除评论（软删除）- 支持级联删除子评论"""
    try:
        comment = db.query(Comment).filter(
            Comment.id == comment_id,
            Comment.user_id == user.id,
            Comment.is_deleted == 0
        ).first()
        
        if not comment:
            return fail("评论不存在或无权删除")
        
        # 级联软删除逻辑
        def cascade_delete_comment(comment_id: int, db: Session):
            """递归软删除评论及其所有子评论"""
            # 软删除当前评论
            current_comment = db.query(Comment).filter(Comment.id == comment_id).first()
            if current_comment:
                current_comment.is_deleted = 1
                
                # 查找所有子评论并递归删除
                child_comments = db.query(Comment).filter(
                    Comment.parent_id == comment_id,
                    Comment.is_deleted == 0
                ).all()
                
                for child in child_comments:
                    cascade_delete_comment(child.id, db)
        
        # 执行级联删除
        cascade_delete_comment(comment_id, db)
        db.commit()
        
        return ok(None, "删除成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.get("/my")
def get_my_comments(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """获取我的评论"""
    try:
        comments = (
            db.query(Comment)
            .options(
                joinedload(Comment.user),
                joinedload(Comment.images),
                joinedload(Comment.footprint)
            )
            .filter(
                Comment.user_id == user.id,
                Comment.is_deleted == 0
            )
            .order_by(Comment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return ok([_comment_to_dict(comment, include_footprint=True) for comment in comments])
    except Exception as e:
        return fail(str(e))



def _comment_to_dict(comment: Comment, include_footprint: bool = False) -> dict:
    """将评论对象转换为字典"""
    result = {
        "id": comment.id,
        "footprint_id": comment.footprint_id,
        "user_id": comment.user_id,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "is_deleted": comment.is_deleted,
        "created_at": comment.created_at.isoformat(),
        "updated_at": comment.updated_at.isoformat()
    }
    
    # 添加用户信息
    if comment.user:
        result["user"] = {
            "id": comment.user.id,
            "username": comment.user.username,
            "nickname": comment.user.nickname,
            "avatar": convert_avatar_url(comment.user.avatar)
        }
    
    # 添加图片信息
    if comment.images:
        result["images"] = [
            {
                "id": img.id,
                "image_url": generate_media_url(img.image_url),  # 生成签名URL
                "description": img.description,
                "sort_order": img.sort_order,
                "created_at": img.created_at.isoformat()
            }
            for img in sorted(comment.images, key=lambda x: x.sort_order)
        ]
    else:
        result["images"] = []
    
    # 添加子评论信息
    if hasattr(comment, 'children') and comment.children:
        result["children"] = [
            _comment_to_dict(child_comment) 
            for child_comment in comment.children 
            if child_comment.is_deleted == 0
        ]
    else:
        result["children"] = []
    
    # 添加足迹信息（如果需要）
    if include_footprint and comment.footprint:
        result["footprint"] = {
            "id": comment.footprint.id,
            "name": comment.footprint.name,
            "longitude": float(comment.footprint.longitude),
            "latitude": float(comment.footprint.latitude)
        }
    
    return result
