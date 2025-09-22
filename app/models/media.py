from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.session import Base


class FootprintMedia(Base):
    __tablename__ = "footprint_medias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='媒体ID')
    footprint_id: Mapped[int] = mapped_column(ForeignKey("footprints.id", ondelete="CASCADE"), index=True, nullable=False, comment='足迹ID')
    media_url: Mapped[str] = mapped_column(String(255), nullable=False, comment='媒体URL')
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, comment='媒体类型：image/video')
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='描述')
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='排序顺序')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment='上传时间')

    # 关系
    footprint = relationship("Footprint", back_populates="medias")
