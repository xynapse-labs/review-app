from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from .notifications import notify

router = APIRouter(tags=["comments"])


@router.post("/versions/{version_id}/comments", response_model=schemas.CommentOut)
def add_comment(
    version_id: int,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    version = db.get(models.DrawingVersion, version_id)
    if not version:
        raise HTTPException(404, "Version not found")
    drawing = db.get(models.Drawing, version.drawing_id)
    if user.role == models.Role.designer and drawing.designer_id != user.id:
        raise HTTPException(403, "Designers may only comment on their own submissions")

    if payload.parent_id is not None:
        parent = db.get(models.Comment, payload.parent_id)
        if not parent or parent.version_id != version_id:
            raise HTTPException(400, "Parent comment must belong to the same version")

    comment = models.Comment(
        version_id=version_id,
        author_id=user.id,
        parent_id=payload.parent_id,
        body=payload.body,
        tag=payload.tag,
        location_ref=payload.location_ref,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    tag_label = "requested a change on" if payload.tag == models.CommentTag.request_change else "commented on"
    notify(db, drawing_id=drawing.id, exclude_user_id=user.id, message=f'{user.display_name} {tag_label} "{drawing.title}"')
    return comment


@router.post("/comments/{comment_id}/resolve", response_model=schemas.CommentOut)
def resolve_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    comment = db.get(models.Comment, comment_id)
    if not comment:
        raise HTTPException(404, "Comment not found")
    version = db.get(models.DrawingVersion, comment.version_id)
    drawing = db.get(models.Drawing, version.drawing_id)
    if user.role == models.Role.designer and drawing.designer_id != user.id:
        raise HTTPException(403, "Only the owning designer or a reviewer can resolve this comment")

    comment.resolved = True
    comment.resolved_by = user.id
    comment.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(comment)
    return comment
