from datetime import date, datetime
from pydantic import BaseModel
from typing import List, Optional, Union


class FootprintBase(BaseModel):
    name: str
    lng: float
    lat: float
    type: str = "other"
    date: Optional[Union[str, date]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_public: bool = False


class FootprintCreate(FootprintBase):
    pass


class FootprintUpdate(BaseModel):
    name: Optional[str] = None
    lng: Optional[float] = None
    lat: Optional[float] = None
    type: Optional[str] = None
    date: Optional[Union[str, date]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    is_public: Optional[bool] = None


class FootprintOut(FootprintBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True
