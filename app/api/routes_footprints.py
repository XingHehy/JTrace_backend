from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime, date
from ..db.session import get_db
from ..models import (
    Footprint, FootprintType, Tag, FootprintTag, 
    FootprintMedia, User, Comment, CommentImage
)
from ..schemas.footprint import (
    FootprintCreate, FootprintOut, FootprintUpdate,
    FootprintTypeCreate, FootprintTypeOut,
    TagOut, FootprintSummary
)
from .deps import get_current_user
from ..utils.response import ok, fail
from ..utils.avatar_utils import convert_avatar_url
from ..utils.media_utils import generate_media_url

router = APIRouter(prefix="/footprints", tags=["footprints"])


@router.get("/types")
def list_footprint_types(db: Session = Depends(get_db)):
    """获取所有足迹类型"""
    try:
        types = db.query(FootprintType).order_by(FootprintType.sort_order, FootprintType.id).all()
        return ok([FootprintTypeOut.model_validate(t) for t in types])
    except Exception as e:
        return fail(str(e))


@router.get("/tags")
def list_tags(
    search: Optional[str] = Query(None, description="搜索标签名称"),
    db: Session = Depends(get_db)
):
    """获取所有标签"""
    try:
        query = db.query(Tag)
        if search:
            query = query.filter(Tag.name.contains(search))
        tags = query.order_by(Tag.created_at.desc()).all()
        return ok([TagOut.model_validate(t) for t in tags])
    except Exception as e:
        return fail(str(e))


@router.get("/mine")
def get_my_footprints(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    type_id: Optional[int] = Query(None, description="按类型筛选"),
    is_public: Optional[int] = Query(None, description="按公开状态筛选"),
    search: Optional[str] = Query(None, description="搜索地点名称、地址、描述"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    """获取当前用户的足迹"""
    try:
        query = db.query(Footprint).filter(Footprint.user_id == user.id)
        
        if type_id is not None:
            query = query.filter(Footprint.type_id == type_id)
        if is_public is not None:
            query = query.filter(Footprint.is_public == is_public)
        if search:
            query = query.filter(or_(
                Footprint.name.contains(search),
                Footprint.address.contains(search),
                Footprint.description.contains(search)
            ))
        
        items = (
            query.options(
                joinedload(Footprint.footprint_type),
                joinedload(Footprint.tags).joinedload(FootprintTag.tag),
                joinedload(Footprint.medias),
                joinedload(Footprint.user)
            )
            .order_by(Footprint.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # 返回用户信息和足迹列表，与其他接口保持一致的数据结构
        return ok({
            "user": {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "avatar": convert_avatar_url(user.avatar),
                "bio": user.bio,
                "gender": user.gender,
                "created_at": user.created_at.isoformat(),
                "is_admin": user.id == 1  # 简单判断管理员
            },
            "footprints": [_footprint_to_dict(item) for item in items]
        })
    except Exception as e:
        return fail(str(e))


@router.get("/public")
def list_public_footprints(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    type_id: Optional[int] = Query(None, description="按类型筛选"),
    search: Optional[str] = Query(None, description="搜索地点名称"),
    db: Session = Depends(get_db)
):
    """获取公开的足迹"""
    try:
        query = db.query(Footprint).filter(Footprint.is_public == 1)
        
        if type_id is not None:
            query = query.filter(Footprint.type_id == type_id)
        if search:
            query = query.filter(or_(
                Footprint.name.contains(search),
                Footprint.address.contains(search),
                Footprint.description.contains(search)
            ))
        
        items = (
            query.options(
                joinedload(Footprint.footprint_type),
                joinedload(Footprint.tags).joinedload(FootprintTag.tag),
                joinedload(Footprint.medias),
                joinedload(Footprint.user)
            )
            .order_by(Footprint.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        return ok([_footprint_to_dict(item) for item in items])
    except Exception as e:
        return fail(str(e))


@router.get("/user/{username}")
def get_user_footprints(
    username: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取指定用户的公开足迹"""
    try:
        # 查找用户
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return fail("用户不存在")
        
        # 查询该用户的公开足迹
        items = (
            db.query(Footprint)
            .filter(
                Footprint.user_id == user.id,
                Footprint.is_public == 1
            )
            .options(
                joinedload(Footprint.footprint_type),
                joinedload(Footprint.tags).joinedload(FootprintTag.tag),
                joinedload(Footprint.medias),
                joinedload(Footprint.user)
            )
            .order_by(Footprint.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        
        # 返回用户信息和足迹列表
        return ok({
            "user": {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
                "avatar": convert_avatar_url(user.avatar),
                "bio": user.bio,
                "gender": user.gender,
                "created_at": user.created_at.isoformat(),
                "is_admin": user.id == 1  # 简单判断管理员
            },
            "footprints": [_footprint_to_dict(item) for item in items]
        })
    except Exception as e:
        return fail(str(e))


@router.post("/")
def create_footprint(
    body: FootprintCreate, 
    db: Session = Depends(get_db), 
    user = Depends(get_current_user)
):
    """创建新足迹"""
    try:
        # 检查足迹类型是否存在
        footprint_type = db.query(FootprintType).filter(FootprintType.id == body.type_id).first()
        if not footprint_type:
            return fail("足迹类型不存在")
        
        # 创建足迹
        footprint = Footprint(
            user_id=user.id,
            type_id=body.type_id,
            name=body.name,
            longitude=body.longitude,
            latitude=body.latitude,
            address=body.address,
            visit_time=body.visit_time,
            description=body.description,
            is_public=body.is_public
        )
        db.add(footprint)
        db.commit()
        db.refresh(footprint)
        
        # 处理标签
        if body.tag_names:
            for tag_name in body.tag_names:
                # 获取或创建标签
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.add(tag)
                    db.commit()
                    db.refresh(tag)
                
                # 创建关联
                footprint_tag = FootprintTag(footprint_id=footprint.id, tag_id=tag.id)
                db.add(footprint_tag)
        
        # 处理媒体文件
        if body.medias:
            for media_data in body.medias:
                media = FootprintMedia(
                    footprint_id=footprint.id,
                    media_url=media_data.media_url,
                    media_type=media_data.media_type,
                    description=media_data.description,
                    sort_order=media_data.sort_order
                )
                db.add(media)
        
        db.commit()
        
        # 重新查询以获取完整数据
        footprint = (
            db.query(Footprint)
            .options(
                joinedload(Footprint.footprint_type),
                joinedload(Footprint.tags).joinedload(FootprintTag.tag),
                joinedload(Footprint.medias),
                joinedload(Footprint.user)
            )
            .filter(Footprint.id == footprint.id)
            .first()
        )
        
        return ok(_footprint_to_dict(footprint), "创建成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.get("/{footprint_id}")
def get_footprint(
    footprint_id: int, 
    db: Session = Depends(get_db), 
    user = Depends(get_current_user)
):
    """获取足迹详情（需要登录）"""
    try:
        footprint = (
            db.query(Footprint)
            .options(
                joinedload(Footprint.footprint_type),
                joinedload(Footprint.tags).joinedload(FootprintTag.tag),
                joinedload(Footprint.medias),
                joinedload(Footprint.user),
                joinedload(Footprint.comments).joinedload(Comment.user),
                joinedload(Footprint.comments).joinedload(Comment.images)
            )
            .filter(
                Footprint.id == footprint_id,
                or_(
                    Footprint.user_id == user.id,  # 自己的足迹
                    Footprint.is_public == 1       # 公开足迹
                )
            )
            .first()
        )
        
        if not footprint:
            return fail("足迹不存在或无权访问")
        
        return ok(_footprint_to_dict(footprint, include_comments=True))
    except Exception as e:
        return fail(str(e))


@router.get("/{footprint_id}/detail")
def get_footprint_detail(
    footprint_id: int, 
    db: Session = Depends(get_db)
):
    """获取足迹详情（公开访问，用于分享）"""
    try:
        footprint = (
            db.query(Footprint)
            .options(
                joinedload(Footprint.footprint_type),
                joinedload(Footprint.tags).joinedload(FootprintTag.tag),
                joinedload(Footprint.medias),
                joinedload(Footprint.user),
                joinedload(Footprint.comments).joinedload(Comment.user),
                joinedload(Footprint.comments).joinedload(Comment.images)
            )
            .filter(
                Footprint.id == footprint_id,
                Footprint.is_public == 1  # 只能访问公开足迹
            )
            .first()
        )
        
        if not footprint:
            return fail("足迹不存在或不是公开足迹")
        
        return ok(_footprint_to_dict(footprint, include_comments=True))
    except Exception as e:
        return fail(str(e))


@router.put("/{footprint_id}")
def update_footprint(
    footprint_id: int, 
    body: FootprintUpdate, 
    db: Session = Depends(get_db), 
    user = Depends(get_current_user)
):
    """更新足迹"""
    try:
        footprint = db.query(Footprint).filter(
            Footprint.id == footprint_id, 
            Footprint.user_id == user.id
        ).first()
        
        if not footprint:
            return fail("足迹不存在或无权修改")
        
        # 更新基本字段
        if body.name is not None:
            footprint.name = body.name
        if body.type_id is not None:
            footprint.type_id = body.type_id
        if body.longitude is not None:
            footprint.longitude = body.longitude
        if body.latitude is not None:
            footprint.latitude = body.latitude
        if body.address is not None:
            footprint.address = body.address
        if body.visit_time is not None:
            footprint.visit_time = body.visit_time
        if body.description is not None:
            footprint.description = body.description
        if body.is_public is not None:
            footprint.is_public = body.is_public
        
        # 更新标签
        if body.tag_names is not None:
            # 删除原有标签关联
            db.query(FootprintTag).filter(FootprintTag.footprint_id == footprint.id).delete()
            
            # 添加新标签
            for tag_name in body.tag_names:
                tag = db.query(Tag).filter(Tag.name == tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.add(tag)
                    db.commit()
                    db.refresh(tag)
                
                footprint_tag = FootprintTag(footprint_id=footprint.id, tag_id=tag.id)
                db.add(footprint_tag)
        
        # 更新媒体文件
        if body.medias is not None:
            # 删除原有媒体文件
            db.query(FootprintMedia).filter(FootprintMedia.footprint_id == footprint.id).delete()
            
            # 添加新媒体文件
            for media_data in body.medias:
                media = FootprintMedia(
                    footprint_id=footprint.id,
                    media_url=media_data.media_url,
                    media_type=media_data.media_type,
                    description=media_data.description,
                    sort_order=media_data.sort_order
                )
                db.add(media)
        
        db.commit()
        
        # 重新查询以获取完整数据
        footprint = (
            db.query(Footprint)
            .options(
                joinedload(Footprint.footprint_type),
                joinedload(Footprint.tags).joinedload(FootprintTag.tag),
                joinedload(Footprint.medias),
                joinedload(Footprint.user)
            )
            .filter(Footprint.id == footprint.id)
            .first()
        )
        
        return ok(_footprint_to_dict(footprint), "更新成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.delete("/{footprint_id}")
def delete_footprint(
    footprint_id: int, 
    db: Session = Depends(get_db), 
    user = Depends(get_current_user)
):
    """删除足迹"""
    try:
        footprint = db.query(Footprint).filter(
            Footprint.id == footprint_id, 
            Footprint.user_id == user.id
        ).first()
        
        if not footprint:
            return fail("足迹不存在或无权删除")
        
        db.delete(footprint)
        db.commit()
        return ok(None, "删除成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


def _footprint_to_dict(footprint: Footprint, include_comments: bool = False) -> dict:
    """将足迹对象转换为字典"""
    result = {
        "id": footprint.id,
        "user_id": footprint.user_id,
        "type_id": footprint.type_id,
        "name": footprint.name,
        "longitude": float(footprint.longitude),
        "latitude": float(footprint.latitude),
        "address": footprint.address,
        "visit_time": footprint.visit_time.isoformat() if footprint.visit_time else None,
        "description": footprint.description,
        "is_public": footprint.is_public,
        "created_at": footprint.created_at.isoformat(),
        "updated_at": footprint.updated_at.isoformat(),
    }
    
    # 添加用户信息
    if footprint.user:
        result["user"] = {
            "id": footprint.user.id,
            "username": footprint.user.username,
            "nickname": footprint.user.nickname,
            "avatar": convert_avatar_url(footprint.user.avatar)
        }
    
    # 添加类型信息
    if footprint.footprint_type:
        result["footprint_type"] = {
            "id": footprint.footprint_type.id,
            "name": footprint.footprint_type.name,
            "icon": footprint.footprint_type.icon,
            "sort_order": footprint.footprint_type.sort_order
        }
    
    # 添加标签信息
    if footprint.tags:
        result["tags"] = [
            {
                "id": ft.tag.id,
                "name": ft.tag.name,
                "created_at": ft.tag.created_at.isoformat()
            }
            for ft in footprint.tags
        ]
    else:
        result["tags"] = []
    
    # 添加媒体信息
    if footprint.medias:
        result["medias"] = [
            {
                "id": media.id,
                "media_url": generate_media_url(media.media_url),  # 生成签名URL
                "media_type": media.media_type,
                "description": media.description,
                "sort_order": media.sort_order,
                "created_at": media.created_at.isoformat()
            }
            for media in sorted(footprint.medias, key=lambda x: x.sort_order)
        ]
    else:
        result["medias"] = []
    
    # 添加评论信息（如果需要）
    if include_comments and footprint.comments:
        result["comments"] = [
            {
                "id": comment.id,
                "user_id": comment.user_id,
                "parent_id": comment.parent_id,
                "content": comment.content,
                "is_deleted": comment.is_deleted,
                "created_at": comment.created_at.isoformat(),
                "updated_at": comment.updated_at.isoformat(),
                "user": {
                    "id": comment.user.id,
                    "username": comment.user.username,
                    "nickname": comment.user.nickname,
                    "avatar": convert_avatar_url(comment.user.avatar)
                } if comment.user else None,
                "images": [
                    {
                        "id": img.id,
                        "image_url": generate_media_url(img.image_url),  # 生成签名URL
                        "description": img.description,
                        "sort_order": img.sort_order,
                        "created_at": img.created_at.isoformat()
                    }
                    for img in sorted(comment.images, key=lambda x: x.sort_order)
                ] if comment.images else []
            }
            for comment in footprint.comments if comment.is_deleted == 0
        ]
    
    return result