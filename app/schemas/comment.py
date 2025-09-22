from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from .user import UserSummary


class CommentImageBase(BaseModel):
    image_url: str
    description: Optional[str] = None
    sort_order: int = 0


class CommentImageCreate(CommentImageBase):
    pass


class CommentImageOut(CommentImageBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CommentBase(BaseModel):
    content: str


class CommentCreate(CommentBase):
    parent_id: Optional[int] = None
    images: Optional[List[CommentImageCreate]] = None


class CommentUpdate(BaseModel):
    content: Optional[str] = None


class CommentOut(CommentBase):
    id: int
    footprint_id: int
    user_id: int
    parent_id: Optional[int] = None
    is_deleted: int
    created_at: datetime
    updated_at: datetime
    user: Optional[UserSummary] = None
    images: Optional[List[CommentImageOut]] = None
    children: Optional[List["CommentOut"]] = None

    class Config:
        from_attributes = True


# 更新前向引用
CommentOut.model_rebuild()
