from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Integer, Text, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='用户ID')
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False, comment='用户名')
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False, comment='邮箱')
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment='密码哈希')
    avatar: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='头像URL')
    bio: Mapped[str | None] = mapped_column(Text, nullable=True, comment='个人简介')
    gender: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False, comment='性别：0-未知，1-男，2-女')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment='注册时间')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment='更新时间')
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment='最后登录时间')
    status: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment='状态：0-禁用，1-正常')

    # 关系
    footprints = relationship("Footprint", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user")
