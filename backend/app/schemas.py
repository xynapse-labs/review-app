from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from .models import CommentTag, DrawingStatus, Role


class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    display_name: str
    role: Role

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class CommentCreate(BaseModel):
    body: str
    tag: CommentTag = CommentTag.general_feedback
    location_ref: Optional[str] = None
    parent_id: Optional[int] = None


class CommentOut(BaseModel):
    id: int
    version_id: int
    author: UserOut
    parent_id: Optional[int]
    body: str
    tag: CommentTag
    location_ref: Optional[str]
    resolved: bool
    resolved_by: Optional[int]
    resolved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class VersionOut(BaseModel):
    id: int
    drawing_id: int
    version_number: int
    revision_letter: str
    file_type: str
    original_filename: str
    file_url: str
    uploader: UserOut
    uploaded_at: datetime
    superseded: bool
    comments: List[CommentOut] = []

    class Config:
        from_attributes = True


class StatusEventOut(BaseModel):
    id: int
    version_id: Optional[int]
    actor: UserOut
    old_status: Optional[str]
    new_status: str
    note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DrawingOut(BaseModel):
    id: int
    title: str
    designer: UserOut
    status: DrawingStatus
    created_at: datetime
    versions: List[VersionOut] = []

    class Config:
        from_attributes = True


class DrawingSummaryOut(BaseModel):
    id: int
    title: str
    designer: UserOut
    status: DrawingStatus
    created_at: datetime
    version_count: int
    latest_version_number: int
    open_change_requests: int

    class Config:
        from_attributes = True


class DrawingDetailOut(DrawingOut):
    status_events: List[StatusEventOut] = []


class StatusChangeRequest(BaseModel):
    version_id: int
    new_status: DrawingStatus
    note: Optional[str] = None


class NotificationOut(BaseModel):
    id: int
    drawing_id: Optional[int]
    message: str
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True
