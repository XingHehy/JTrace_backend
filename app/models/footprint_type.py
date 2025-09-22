from datetime import datetime
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.session import Base


class FootprintType(Base):
    __tablename__ = "footprint_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='类型ID')
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment='类型名称')
    icon: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='类型图标URL')
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='排序顺序')

    # 关系
    footprints = relationship("Footprint", back_populates="footprint_type")
