import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


class Role(str, enum.Enum):
    designer = "designer"
    reviewer = "reviewer"


class DrawingStatus(str, enum.Enum):
    draft = "draft"
    under_review = "under_review"
    changes_required = "changes_required"
    approved = "approved"


class CommentTag(str, enum.Enum):
    request_change = "request_change"
    general_feedback = "general_feedback"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)

    drawings = relationship("Drawing", back_populates="designer")


class Drawing(Base):
    __tablename__ = "drawings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    designer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(DrawingStatus), nullable=False, default=DrawingStatus.draft)
    created_at = Column(DateTime, default=datetime.utcnow)

    designer = relationship("User", back_populates="drawings")
    versions = relationship(
        "DrawingVersion", back_populates="drawing", order_by="DrawingVersion.version_number"
    )
    status_events = relationship(
        "StatusEvent", back_populates="drawing", order_by="StatusEvent.created_at"
    )


class DrawingVersion(Base):
    __tablename__ = "drawing_versions"

    id = Column(Integer, primary_key=True, index=True)
    drawing_id = Column(Integer, ForeignKey("drawings.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    superseded = Column(Boolean, default=False)

    drawing = relationship("Drawing", back_populates="versions")
    uploader = relationship("User")
    comments = relationship(
        "Comment", back_populates="version", order_by="Comment.created_at"
    )

    @property
    def revision_letter(self) -> str:
        n = self.version_number - 1
        letters = ""
        while True:
            n, rem = divmod(n, 26)
            letters = chr(65 + rem) + letters
            if n == 0:
                break
            n -= 1
        return letters


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("drawing_versions.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    body = Column(Text, nullable=False)
    tag = Column(Enum(CommentTag), nullable=False, default=CommentTag.general_feedback)
    location_ref = Column(String, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    version = relationship("DrawingVersion", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])
    resolver = relationship("User", foreign_keys=[resolved_by])


class StatusEvent(Base):
    __tablename__ = "status_events"

    id = Column(Integer, primary_key=True, index=True)
    drawing_id = Column(Integer, ForeignKey("drawings.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("drawing_versions.id"), nullable=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    drawing = relationship("Drawing", back_populates="status_events")
    actor = relationship("User")
    version = relationship("DrawingVersion")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    drawing_id = Column(Integer, ForeignKey("drawings.id"), nullable=True)
    message = Column(String, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
