from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.session import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='标签ID')
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment='标签名称')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment='创建时间')

    # 关系
    footprint_tags = relationship("FootprintTag", back_populates="tag", cascade="all, delete-orphan")


class FootprintTag(Base):
    __tablename__ = "footprint_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='关联ID')
    footprint_id: Mapped[int] = mapped_column(ForeignKey("footprints.id", ondelete="CASCADE"), nullable=False, comment='足迹ID')
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, comment='标签ID')

    # 关系
    footprint = relationship("Footprint", back_populates="tags")
    tag = relationship("Tag", back_populates="footprint_tags")

    __table_args__ = (
        {"comment": "足迹-标签关联表"}
    )
