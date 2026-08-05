from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from ..utils import save_upload
from .notifications import notify

router = APIRouter(prefix="/drawings", tags=["drawings"])


def _drawing_or_404(db: Session, drawing_id: int) -> models.Drawing:
    drawing = (
        db.query(models.Drawing)
        .options(
            joinedload(models.Drawing.designer),
            joinedload(models.Drawing.versions).joinedload(models.DrawingVersion.uploader),
            joinedload(models.Drawing.versions)
            .joinedload(models.DrawingVersion.comments)
            .joinedload(models.Comment.author),
        )
        .filter(models.Drawing.id == drawing_id)
        .first()
    )
    if not drawing:
        raise HTTPException(404, "Drawing not found")
    return drawing


def _assert_can_view(drawing: models.Drawing, user: models.User):
    if user.role == models.Role.designer and drawing.designer_id != user.id:
        raise HTTPException(403, "Designers may only view their own submissions")


def _version_out(v: models.DrawingVersion) -> schemas.VersionOut:
    return schemas.VersionOut(
        id=v.id,
        drawing_id=v.drawing_id,
        version_number=v.version_number,
        revision_letter=v.revision_letter,
        file_type=v.file_type,
        original_filename=v.original_filename,
        file_url=f"/files/{v.file_path}",
        uploader=v.uploader,
        uploaded_at=v.uploaded_at,
        superseded=v.superseded,
        comments=v.comments,
    )


def _drawing_out(d: models.Drawing) -> schemas.DrawingOut:
    return schemas.DrawingOut(
        id=d.id,
        title=d.title,
        designer=d.designer,
        status=d.status,
        created_at=d.created_at,
        versions=[_version_out(v) for v in d.versions],
    )


@router.post("", response_model=schemas.DrawingOut)
def create_drawing(
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role != models.Role.designer:
        raise HTTPException(403, "Only designers can submit drawings")

    drawing = models.Drawing(title=title, designer_id=user.id, status=models.DrawingStatus.draft)
    db.add(drawing)
    db.flush()

    rel_path, file_type = save_upload(file, drawing.id)
    version = models.DrawingVersion(
        drawing_id=drawing.id,
        version_number=1,
        file_path=rel_path,
        file_type=file_type,
        original_filename=file.filename,
        uploaded_by=user.id,
    )
    db.add(version)
    db.add(
        models.StatusEvent(
            drawing_id=drawing.id,
            actor_id=user.id,
            old_status=None,
            new_status=models.DrawingStatus.draft.value,
            note="Drawing created",
        )
    )
    db.commit()
    return _drawing_out(_drawing_or_404(db, drawing.id))


@router.get("", response_model=list[schemas.DrawingSummaryOut])
def list_drawings(
    status_filter: Optional[models.DrawingStatus] = None,
    designer_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    query = db.query(models.Drawing).options(
        joinedload(models.Drawing.designer),
        joinedload(models.Drawing.versions).joinedload(models.DrawingVersion.comments),
    )

    if user.role == models.Role.designer:
        query = query.filter(models.Drawing.designer_id == user.id)
    elif designer_id is not None:
        query = query.filter(models.Drawing.designer_id == designer_id)

    if status_filter is not None:
        query = query.filter(models.Drawing.status == status_filter)
    if date_from is not None:
        query = query.filter(models.Drawing.created_at >= date_from)
    if date_to is not None:
        query = query.filter(models.Drawing.created_at <= date_to)

    drawings = query.order_by(models.Drawing.created_at.desc()).all()

    out = []
    for d in drawings:
        latest = d.versions[-1] if d.versions else None
        open_requests = sum(
            1
            for v in d.versions
            for c in v.comments
            if c.tag == models.CommentTag.request_change and not c.resolved
        )
        out.append(
            schemas.DrawingSummaryOut(
                id=d.id,
                title=d.title,
                designer=d.designer,
                status=d.status,
                created_at=d.created_at,
                version_count=len(d.versions),
                latest_version_number=latest.version_number if latest else 0,
                open_change_requests=open_requests,
            )
        )
    return out


@router.get("/{drawing_id}", response_model=schemas.DrawingDetailOut)
def get_drawing(
    drawing_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    drawing = _drawing_or_404(db, drawing_id)
    _assert_can_view(drawing, user)
    base = _drawing_out(drawing)
    return schemas.DrawingDetailOut(**base.model_dump(), status_events=drawing.status_events)


@router.get("/{drawing_id}/audit-log", response_model=list[schemas.StatusEventOut])
def get_audit_log(
    drawing_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    drawing = _drawing_or_404(db, drawing_id)
    _assert_can_view(drawing, user)
    return drawing.status_events


@router.post("/{drawing_id}/submit", response_model=schemas.DrawingOut)
def submit_drawing(
    drawing_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    drawing = _drawing_or_404(db, drawing_id)
    if drawing.designer_id != user.id:
        raise HTTPException(403, "Only the owning designer can submit this drawing")
    if drawing.status not in (models.DrawingStatus.draft, models.DrawingStatus.changes_required):
        raise HTTPException(400, f"Cannot submit a drawing in status '{drawing.status.value}'")

    old_status = drawing.status.value
    drawing.status = models.DrawingStatus.under_review
    db.add(
        models.StatusEvent(
            drawing_id=drawing.id,
            version_id=drawing.versions[-1].id if drawing.versions else None,
            actor_id=user.id,
            old_status=old_status,
            new_status=drawing.status.value,
            note="Submitted for review",
        )
    )
    db.commit()
    notify(db, drawing_id=drawing.id, exclude_user_id=user.id, message=f'"{drawing.title}" submitted for review')
    return _drawing_out(_drawing_or_404(db, drawing.id))


@router.post("/{drawing_id}/versions", response_model=schemas.DrawingOut)
def add_version(
    drawing_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    drawing = _drawing_or_404(db, drawing_id)
    if drawing.designer_id != user.id:
        raise HTTPException(403, "Only the owning designer can add a new version")

    next_number = (drawing.versions[-1].version_number if drawing.versions else 0) + 1
    rel_path, file_type = save_upload(file, drawing.id)
    version = models.DrawingVersion(
        drawing_id=drawing.id,
        version_number=next_number,
        file_path=rel_path,
        file_type=file_type,
        original_filename=file.filename,
        uploaded_by=user.id,
    )
    db.add(version)

    old_status = drawing.status.value
    if drawing.status == models.DrawingStatus.changes_required:
        # Closing the loop: a fresh version after requested changes reopens review automatically.
        drawing.status = models.DrawingStatus.under_review
    elif drawing.status == models.DrawingStatus.approved:
        # Revising a released drawing starts a new in-work cycle.
        drawing.status = models.DrawingStatus.draft
    db.flush()

    db.add(
        models.StatusEvent(
            drawing_id=drawing.id,
            version_id=version.id,
            actor_id=user.id,
            old_status=old_status,
            new_status=drawing.status.value,
            note=f"New version uploaded (Rev {version.revision_letter})",
        )
    )
    db.commit()
    notify(
        db,
        drawing_id=drawing.id,
        exclude_user_id=user.id,
        message=f'New revision {version.revision_letter} uploaded for "{drawing.title}"',
    )
    return _drawing_out(_drawing_or_404(db, drawing.id))


@router.post("/{drawing_id}/status", response_model=schemas.DrawingOut)
def change_status(
    drawing_id: int,
    payload: schemas.StatusChangeRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    if user.role != models.Role.reviewer:
        raise HTTPException(403, "Only reviewers can approve or request changes")
    if payload.new_status not in (models.DrawingStatus.approved, models.DrawingStatus.changes_required):
        raise HTTPException(400, "Status can only be set to 'approved' or 'changes_required'")

    drawing = _drawing_or_404(db, drawing_id)
    if drawing.designer_id == user.id:
        raise HTTPException(403, "A designer cannot review or approve their own submission")

    version = db.get(models.DrawingVersion, payload.version_id)
    if not version or version.drawing_id != drawing.id:
        raise HTTPException(404, "Version not found on this drawing")

    old_status = drawing.status.value
    drawing.status = payload.new_status

    if payload.new_status == models.DrawingStatus.approved:
        for v in drawing.versions:
            if v.version_number < version.version_number:
                v.superseded = True

    db.add(
        models.StatusEvent(
            drawing_id=drawing.id,
            version_id=version.id,
            actor_id=user.id,
            old_status=old_status,
            new_status=drawing.status.value,
            note=payload.note,
        )
    )
    db.commit()
    verb = "approved" if payload.new_status == models.DrawingStatus.approved else "sent back with requested changes"
    notify(db, drawing_id=drawing.id, exclude_user_id=user.id, message=f'"{drawing.title}" was {verb}')
    return _drawing_out(_drawing_or_404(db, drawing.id))
