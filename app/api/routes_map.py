"""
地图配置相关路由 - 提供加密的地图配置
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.session import get_db
from .deps import get_current_user
from ..models.user import User
from ..utils.response import ok, fail
from ..utils.encryption import get_config_encryption
import jwt

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/config")
def get_map_config(
    expires_minutes: int = 60,
    db: Session = Depends(get_db)
):
    """
    获取加密的地图配置
    公开接口，无需登录
    """
    try:
        encryption = get_config_encryption()
        encrypted_config = encryption.get_map_config(expires_minutes)
        
        return ok({
            'config': encrypted_config,
            'expires_minutes': expires_minutes,
            'encryption_enabled': encryption.encryption_config.enabled
        }, "地图配置获取成功")
        
    except Exception as e:
        return fail(f"获取地图配置失败: {str(e)}")


@router.get("/config/public")
def get_public_map_info(db: Session = Depends(get_db)):
    """
    获取公开的地图信息（不包含敏感配置）
    用于判断是否需要加载地图组件
    """
    try:
        return ok({
            'map_enabled': True,
            'provider': 'amap',
            'requires_auth': True  # 需要登录才能获取完整配置
        }, "公开地图信息获取成功")
        
    except Exception as e:
        return fail(f"获取公开地图信息失败: {str(e)}")
