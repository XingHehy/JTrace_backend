from datetime import datetime
from pydantic import BaseModel


class UserBase(BaseModel):
    username: str
    is_active: bool
    is_admin: bool


class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
