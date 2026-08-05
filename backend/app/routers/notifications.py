from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/notifications", tags=["notifications"])


def notify(db: Session, drawing_id: int, exclude_user_id: int, message: str) -> None:
    """Simulated in-app alert: notifies the drawing's designer and all reviewers
    (anyone with a stake in the drawing) except the user who triggered the event."""
    drawing = db.get(models.Drawing, drawing_id)
    if not drawing:
        return
    reviewer_ids = [u.id for u in db.query(models.User).filter(models.User.role == models.Role.reviewer)]
    recipient_ids = {drawing.designer_id, *reviewer_ids} - {exclude_user_id}
    for uid in recipient_ids:
        db.add(models.Notification(user_id=uid, drawing_id=drawing_id, message=message))
    db.commit()


@router.get("", response_model=list[schemas.NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == user.id)
        .order_by(models.Notification.created_at.desc())
        .all()
    )


@router.post("/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    notification = db.get(models.Notification, notification_id)
    if not notification or notification.user_id != user.id:
        raise HTTPException(404, "Notification not found")
    notification.read = True
    db.commit()
    return notification


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    db.query(models.Notification).filter(
        models.Notification.user_id == user.id, models.Notification.read == False  # noqa: E712
    ).update({"read": True})
    db.commit()
    return {"ok": True}
