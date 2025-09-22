from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..db.session import get_db
from ..models import FootprintType
from ..schemas.footprint import FootprintTypeCreate, FootprintTypeOut
from .deps import get_current_user, get_current_admin
from ..utils.response import ok, fail

router = APIRouter(prefix="/footprint-types", tags=["footprint-types"])


@router.get("/")
def list_footprint_types(db: Session = Depends(get_db)):
    """获取所有足迹类型"""
    try:
        types = db.query(FootprintType).order_by(FootprintType.sort_order, FootprintType.id).all()
        return ok([FootprintTypeOut.model_validate(t) for t in types])
    except Exception as e:
        return fail(str(e))


@router.post("/")
def create_footprint_type(
    data: FootprintTypeCreate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """创建足迹类型（管理员权限）"""
    try:
        # 检查名称是否已存在
        exist = db.query(FootprintType).filter(FootprintType.name == data.name).first()
        if exist:
            return fail("类型名称已存在")
        
        footprint_type = FootprintType(
            name=data.name,
            icon=data.icon,
            sort_order=data.sort_order
        )
        db.add(footprint_type)
        db.commit()
        db.refresh(footprint_type)
        
        return ok(FootprintTypeOut.model_validate(footprint_type), "创建成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.put("/{type_id}")
def update_footprint_type(
    type_id: int,
    data: FootprintTypeCreate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """更新足迹类型（管理员权限）"""
    try:
        footprint_type = db.query(FootprintType).filter(FootprintType.id == type_id).first()
        if not footprint_type:
            return fail("类型不存在")
        
        # 检查名称是否已被其他类型使用
        if data.name != footprint_type.name:
            exist = db.query(FootprintType).filter(
                FootprintType.name == data.name,
                FootprintType.id != type_id
            ).first()
            if exist:
                return fail("类型名称已存在")
        
        footprint_type.name = data.name
        footprint_type.icon = data.icon
        footprint_type.sort_order = data.sort_order
        
        db.commit()
        db.refresh(footprint_type)
        
        return ok(FootprintTypeOut.model_validate(footprint_type), "更新成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.delete("/{type_id}")
def delete_footprint_type(
    type_id: int,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin)
):
    """删除足迹类型（管理员权限）"""
    try:
        footprint_type = db.query(FootprintType).filter(FootprintType.id == type_id).first()
        if not footprint_type:
            return fail("类型不存在")
        
        # 检查是否有足迹在使用此类型
        from ..models import Footprint
        count = db.query(Footprint).filter(Footprint.type_id == type_id).count()
        if count > 0:
            return fail(f"此类型下还有 {count} 个足迹，无法删除")
        
        db.delete(footprint_type)
        db.commit()
        
        return ok(None, "删除成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))
