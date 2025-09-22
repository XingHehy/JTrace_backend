from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..models.user import User
from ..schemas.auth import Token, LoginRequest, RegisterRequest, ChangePasswordRequest
from ..schemas.user import UserOut, UserUpdate, UserAvatarUpdate
from ..core.security import verify_password, hash_password, create_access_token
from .deps import get_current_user
from ..core.redis_client import get_redis
from ..core.config import load_settings
from ..utils.response import ok, fail
from ..utils.avatar_utils import convert_avatar_url

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        # 检查用户名是否已存在
        exist_username = db.query(User).filter(User.username == data.username).first()
        if exist_username:
            return fail("用户名已存在")
        
        # 检查邮箱是否已存在
        exist_email = db.query(User).filter(User.email == data.email).first()
        if exist_email:
            return fail("邮箱已存在")
        
        user = User(
            username=data.username, 
            email=data.email,
            password_hash=hash_password(data.password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        return ok({
            "id": user.id, 
            "username": user.username, 
            "email": user.email,
            "status": user.status,
            "created_at": user.created_at.isoformat()
        })
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.post("/login")
def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    
    # 检查用户状态
    if user.status != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账户已被禁用")
    
    # 更新最后登录时间
    from datetime import datetime
    user.last_login = datetime.utcnow()
    db.commit()
    
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
            "email": current.email,
            "avatar": convert_avatar_url(current.avatar),
            "bio": current.bio,
            "gender": current.gender,
            "status": current.status,
            "created_at": current.created_at.isoformat(),
            "updated_at": current.updated_at.isoformat(),
            "last_login": current.last_login.isoformat() if current.last_login else None
        })
    except Exception as e:
        return fail(str(e))


@router.put("/me")
def update_profile(data: UserUpdate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        # 检查用户名是否已被其他用户使用
        if data.username and data.username != current.username:
            exist_username = db.query(User).filter(User.username == data.username, User.id != current.id).first()
            if exist_username:
                return fail("用户名已存在")
            current.username = data.username
        
        # 检查邮箱是否已被其他用户使用
        if data.email and data.email != current.email:
            exist_email = db.query(User).filter(User.email == data.email, User.id != current.id).first()
            if exist_email:
                return fail("邮箱已存在")
            current.email = data.email
        
        if data.avatar is not None:
            current.avatar = data.avatar
        if data.bio is not None:
            current.bio = data.bio
        if data.gender is not None:
            current.gender = data.gender
        if data.password:
            current.password_hash = hash_password(data.password)
        
        db.commit()
        db.refresh(current)
        
        return ok({
            "id": current.id,
            "username": current.username,
            "email": current.email,
            "avatar": convert_avatar_url(current.avatar),
            "bio": current.bio,
            "gender": current.gender,
            "status": current.status,
            "updated_at": current.updated_at.isoformat()
        })
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.put("/avatar")
def update_avatar(data: UserAvatarUpdate, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        current.avatar = data.avatar
        db.commit()
        db.refresh(current)
        
        return ok({
            "id": current.id,
            "username": current.username,
            "avatar": convert_avatar_url(current.avatar)
        }, "头像更新成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.post("/change-password")
def change_password(data: ChangePasswordRequest, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        if not verify_password(data.old_password, current.password_hash):
            return fail("原密码错误")
        
        current.password_hash = hash_password(data.new_password)
        db.commit()
        
        return ok(None, "密码修改成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))
