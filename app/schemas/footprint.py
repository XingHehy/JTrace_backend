from datetime import date, datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from .user import UserSummary


class FootprintTypeBase(BaseModel):
    name: str
    icon: Optional[str] = None
    sort_order: int = 0


class FootprintTypeCreate(FootprintTypeBase):
    pass


class FootprintTypeOut(FootprintTypeBase):
    id: int

    class Config:
        from_attributes = True


class TagBase(BaseModel):
    name: str


class TagOut(TagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FootprintMediaBase(BaseModel):
    media_url: str
    media_type: str = Field(..., pattern="^(image|video)$")
    description: Optional[str] = None
    sort_order: int = 0


class FootprintMediaCreate(FootprintMediaBase):
    pass


class FootprintMediaOut(FootprintMediaBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FootprintBase(BaseModel):
    name: str
    longitude: float = Field(..., ge=-180, le=180)
    latitude: float = Field(..., ge=-90, le=90)
    address: Optional[str] = None
    visit_time: Optional[date] = None
    description: Optional[str] = None
    is_public: int = 1


class FootprintCreate(FootprintBase):
    type_id: int
    tag_names: Optional[List[str]] = None
    medias: Optional[List[FootprintMediaCreate]] = None


class FootprintUpdate(BaseModel):
    name: Optional[str] = None
    type_id: Optional[int] = None
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    address: Optional[str] = None
    visit_time: Optional[date] = None
    description: Optional[str] = None
    is_public: Optional[int] = None
    tag_names: Optional[List[str]] = None
    medias: Optional[List[FootprintMediaCreate]] = None


class FootprintOut(FootprintBase):
    id: int
    user_id: int
    type_id: int
    created_at: datetime
    updated_at: datetime
    user: Optional[UserSummary] = None
    footprint_type: Optional[FootprintTypeOut] = None
    tags: Optional[List[TagOut]] = None
    medias: Optional[List[FootprintMediaOut]] = None

    class Config:
        from_attributes = True


class FootprintSummary(BaseModel):
    id: int
    name: str
    longitude: float
    latitude: float
    type_id: int
    is_public: int
    created_at: datetime

    class Config:
        from_attributes = True
