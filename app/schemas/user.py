from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[int] = None
    password: Optional[str] = None


class UserProfile(BaseModel):
    avatar: Optional[str] = None
    bio: Optional[str] = None


class UserAvatarUpdate(BaseModel):
    avatar: str


class UserOut(UserBase):
    id: int
    avatar: Optional[str] = None
    bio: Optional[str] = None
    gender: int = 0
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    status: int

    class Config:
        from_attributes = True


class UserSummary(BaseModel):
    id: int
    username: str
    avatar: Optional[str] = None

    class Config:
        from_attributes = True
