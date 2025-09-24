from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from ..core.security import decode_token
from ..db.session import get_db
from ..models.user import User
from ..core.redis_client import get_redis
from typing import Optional


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)) -> User:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided")
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # 对比 Redis 中存储的 token
    r = get_redis()
    cache_token = r.get(f"auth:token:{username}")
    if not cache_token or cache_token != token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or revoked")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    # 检查用户状态
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account disabled")
    
    return user


def get_current_user_optional(db: Session = Depends(get_db), token: Optional[str] = Depends(oauth2_scheme)) -> Optional[User]:
    """可选的用户获取，支持未登录访问"""
    if not token:
        return None
    
    try:
        payload = decode_token(token)
        username: str = payload.get("sub")
    except Exception:
        return None

    # 对比 Redis 中存储的 token
    try:
        r = get_redis()
        cache_token = r.get(f"auth:token:{username}")
        if not cache_token or cache_token != token:
            return None
    except Exception:
        return None

    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or user.status != 1:
            return None
        return user
    except Exception:
        return None


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    # 检查是否为管理员（用户ID为1）
    if user.id != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
