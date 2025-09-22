from datetime import datetime, date
from sqlalchemy import String, Date, DateTime, Integer, ForeignKey, Text, Boolean, SmallInteger, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.session import Base


class Footprint(Base):
    __tablename__ = "footprints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='足迹ID')
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False, comment='用户ID')
    type_id: Mapped[int] = mapped_column(ForeignKey("footprint_types.id"), index=True, nullable=False, comment='足迹类型ID')
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment='地点名称')
    longitude: Mapped[float] = mapped_column(DECIMAL(10, 6), nullable=False, comment='经度')
    latitude: Mapped[float] = mapped_column(DECIMAL(10, 6), nullable=False, comment='纬度')
    address: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='详细地址')
    visit_time: Mapped[date | None] = mapped_column(Date, nullable=True, comment='前往时间')
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment='描述/文章')
    is_public: Mapped[int] = mapped_column(SmallInteger, default=1, nullable=False, comment='是否公开：0-私有，1-公开')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment='创建时间')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment='更新时间')

    # 关系
    user = relationship("User", back_populates="footprints")
    footprint_type = relationship("FootprintType", back_populates="footprints")
    tags = relationship("FootprintTag", back_populates="footprint", cascade="all, delete-orphan")
    medias = relationship("FootprintMedia", back_populates="footprint", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="footprint", cascade="all, delete-orphan")
