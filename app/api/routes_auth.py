from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..models.user import User
from ..schemas.auth import Token, LoginRequest, RegisterRequest
from ..schemas.user import UserOut
from ..core.security import verify_password, hash_password, create_access_token
from .deps import get_current_user
from ..core.redis_client import get_redis
from ..core.config import load_settings
from ..utils.response import ok, fail

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        exist = db.query(User).filter(User.username == data.username).first()
        if exist:
            return fail("用户名已存在")
        user = User(username=data.username, password_hash=hash_password(data.password))
        db.add(user)
        db.commit()
        db.refresh(user)
        return ok({"id": user.id, "username": user.username, "is_admin": user.is_admin, "is_active": user.is_active, "created_at": user.created_at.isoformat()})
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(user.username)
    # 写入 Redis，设置过期时间
    r = get_redis()
    settings = load_settings()
    ttl = int(settings.jwt.access_token_expires_minutes) * 60
    r.setex(f"auth:token:{user.username}", ttl, token)
    return ok({"access_token": token, "token_type": "bearer"})


@router.get("/me")
def me(current: User = Depends(get_current_user)):
    try:
        return ok({
            "id": current.id,
            "username": current.username,
            "is_admin": current.is_admin,
            "is_active": current.is_active,
            "created_at": current.created_at.isoformat()
        })
    except Exception as e:
        return fail(str(e))
