from datetime import datetime
from sqlalchemy import String, DateTime, Integer, ForeignKey, Text, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..db.session import Base


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='评论ID')
    footprint_id: Mapped[int] = mapped_column(ForeignKey("footprints.id", ondelete="CASCADE"), index=True, nullable=False, comment='足迹ID')
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False, comment='用户ID')
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), index=True, nullable=True, comment='父评论ID')
    content: Mapped[str] = mapped_column(Text, nullable=False, comment='评论内容')
    is_deleted: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False, comment='是否删除：0-未删除，1-已删除')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment='创建时间')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment='更新时间')

    # 关系
    footprint = relationship("Footprint", back_populates="comments")
    user = relationship("User", back_populates="comments")
    parent = relationship("Comment", remote_side=[id], backref="children")
    images = relationship("CommentImage", back_populates="comment", cascade="all, delete-orphan")


class CommentImage(Base):
    __tablename__ = "comment_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, comment='图片ID')
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), index=True, nullable=False, comment='评论ID')
    image_url: Mapped[str] = mapped_column(String(255), nullable=False, comment='图片URL')
    description: Mapped[str | None] = mapped_column(String(255), nullable=True, comment='图片描述')
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment='排序顺序')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment='上传时间')

    # 关系
    comment = relationship("Comment", back_populates="images")
