"""Seeds the database with demo users, drawings, versions, comments, and
generates placeholder PNG/PDF/JPEG "technical drawing" files so the app has
something real to open. Safe to re-run: wipes and rebuilds from scratch.
"""
import io
import os
import shutil
import uuid
from datetime import datetime, timedelta

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas

from .database import Base, SessionLocal, UPLOAD_DIR, engine
from . import models


def _font(size: int):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def make_drawing_png(title: str, rev: str, drawn_by: str, part_no: str) -> bytes:
    w, h = 1000, 700
    img = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, w - 10, h - 10], outline="black", width=3)

    # A stand-in mechanical part: a plate with bolt holes and dimension lines.
    plate = [200, 120, 800, 480]
    draw.rectangle(plate, outline="black", width=3)
    for cx, cy in [(260, 180), (740, 180), (260, 420), (740, 420)]:
        draw.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], outline="black", width=2)

    draw.line([200, 520, 800, 520], fill="black", width=1)
    draw.line([200, 510, 200, 530], fill="black", width=1)
    draw.line([800, 510, 800, 530], fill="black", width=1)
    draw.text((470, 530), "600.0 mm", fill="black", font=_font(18))

    draw.line([860, 120, 860, 480], fill="black", width=1)
    draw.line([850, 120, 870, 120], fill="black", width=1)
    draw.line([850, 480, 870, 480], fill="black", width=1)
    draw.text((870, 290), "360.0 mm", fill="black", font=_font(18))

    draw.text((260, 150), "Ø4X (44)", fill="black", font=_font(14))

    # Title block.
    block = [w - 330, h - 150, w - 20, h - 20]
    draw.rectangle(block, outline="black", width=2)
    lines = [
        f"TITLE: {title}",
        f"PART NO: {part_no}",
        f"REV: {rev}",
        f"DRAWN BY: {drawn_by}",
        f"DATE: {datetime.utcnow():%Y-%m-%d}",
    ]
    for i, line in enumerate(lines):
        draw.text((block[0] + 10, block[1] + 8 + i * 24), line, fill="black", font=_font(15))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_drawing_jpeg(title: str, rev: str, drawn_by: str, part_no: str) -> bytes:
    png_bytes = make_drawing_png(title, rev, drawn_by, part_no)
    img = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def make_drawing_pdf(title: str, rev: str, drawn_by: str, part_no: str) -> bytes:
    buf = io.BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    c.rect(30, 30, width - 60, height - 60)
    c.rect(60, 300, width - 180, 350)

    c.circle(140, 550, 18)
    c.circle(width - 140, 550, 18)
    c.circle(140, 350, 18)
    c.circle(width - 140, 350, 18)

    c.setFont("Helvetica", 10)
    c.drawString(300, 290, "480.0 mm")
    c.line(60, 300, 60, 280)
    c.line(width - 120, 300, width - 120, 280)
    c.line(60, 280, width - 120, 280)

    c.setFont("Helvetica-Bold", 12)
    block_x, block_y = width - 260, 60
    c.rect(block_x, block_y, 200, 110)
    c.setFont("Helvetica", 10)
    c.drawString(block_x + 8, block_y + 90, f"TITLE: {title}")
    c.drawString(block_x + 8, block_y + 70, f"PART NO: {part_no}")
    c.drawString(block_x + 8, block_y + 50, f"REV: {rev}")
    c.drawString(block_x + 8, block_y + 30, f"DRAWN BY: {drawn_by}")
    c.drawString(block_x + 8, block_y + 10, f"DATE: {datetime.utcnow():%Y-%m-%d}")

    c.showPage()
    c.save()
    return buf.getvalue()


def _store(rel_dir: str, ext: str, content: bytes) -> str:
    full_dir = os.path.join(UPLOAD_DIR, rel_dir)
    os.makedirs(full_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(full_dir, name), "wb") as f:
        f.write(content)
    return os.path.join(rel_dir, name)


def seed():
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR)
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        alice = models.User(username="alice", password="alice123", display_name="Alice Chen", role=models.Role.designer)
        priya = models.User(username="priya", password="priya123", display_name="Priya Nair", role=models.Role.designer)
        raj = models.User(username="raj", password="raj123", display_name="Raj Patel", role=models.Role.reviewer)
        tom = models.User(username="tom", password="tom123", display_name="Tom Becker", role=models.Role.reviewer)
        db.add_all([alice, priya, raj, tom])
        db.flush()

        now = datetime.utcnow()

        # --- Drawing A: full lifecycle -> Draft -> Under Review -> Changes Required
        #     -> new version -> Under Review -> Approved. Demonstrates the closed
        #     comment-resolution loop and version supersession.
        drawing_a = models.Drawing(
            title="Bracket Mounting Plate",
            designer_id=alice.id,
            status=models.DrawingStatus.draft,
            created_at=now - timedelta(days=6),
        )
        db.add(drawing_a)
        db.flush()

        v1 = models.DrawingVersion(
            drawing_id=drawing_a.id,
            version_number=1,
            file_path=_store(str(drawing_a.id), ".png", make_drawing_png("Bracket Mounting Plate", "A", "Alice Chen", "BMP-1001")),
            file_type="png",
            original_filename="bracket_mounting_plate_revA.png",
            uploaded_by=alice.id,
            uploaded_at=now - timedelta(days=6),
        )
        db.add(v1)
        db.add(models.StatusEvent(drawing_id=drawing_a.id, actor_id=alice.id, old_status=None, new_status="draft", note="Drawing created", created_at=now - timedelta(days=6)))
        db.flush()

        drawing_a.status = models.DrawingStatus.under_review
        db.add(models.StatusEvent(drawing_id=drawing_a.id, version_id=v1.id, actor_id=alice.id, old_status="draft", new_status="under_review", note="Submitted for review", created_at=now - timedelta(days=5, hours=20)))

        change_comment = models.Comment(
            version_id=v1.id,
            author_id=raj.id,
            body="Hole callout is missing a tolerance. Please add ±0.05mm on the 4x Ø44 pattern before this can be released.",
            tag=models.CommentTag.request_change,
            location_ref="4x Ø44 hole pattern, top-left",
            created_at=now - timedelta(days=5, hours=10),
        )
        db.add(change_comment)
        db.flush()

        drawing_a.status = models.DrawingStatus.changes_required
        db.add(models.StatusEvent(drawing_id=drawing_a.id, version_id=v1.id, actor_id=raj.id, old_status="under_review", new_status="changes_required", note="Tolerance missing on hole pattern", created_at=now - timedelta(days=5, hours=10)))

        reply = models.Comment(
            version_id=v1.id,
            author_id=alice.id,
            parent_id=change_comment.id,
            body="Good catch, fixing now and will resubmit as Rev B.",
            tag=models.CommentTag.general_feedback,
            created_at=now - timedelta(days=4, hours=22),
        )
        db.add(reply)
        db.flush()

        v2 = models.DrawingVersion(
            drawing_id=drawing_a.id,
            version_number=2,
            file_path=_store(str(drawing_a.id), ".png", make_drawing_png("Bracket Mounting Plate", "B", "Alice Chen", "BMP-1001")),
            file_type="png",
            original_filename="bracket_mounting_plate_revB.png",
            uploaded_by=alice.id,
            uploaded_at=now - timedelta(days=4, hours=20),
        )
        db.add(v2)
        drawing_a.status = models.DrawingStatus.under_review
        db.add(models.StatusEvent(drawing_id=drawing_a.id, version_id=v2.id, actor_id=alice.id, old_status="changes_required", new_status="under_review", note="New version uploaded (Rev B)", created_at=now - timedelta(days=4, hours=20)))
        db.flush()

        change_comment.resolved = True
        change_comment.resolved_by = alice.id
        change_comment.resolved_at = now - timedelta(days=4, hours=20)

        db.add(models.Comment(
            version_id=v2.id,
            author_id=raj.id,
            body="Tolerance looks good now. One small note for next time: call out the datum reference frame explicitly.",
            tag=models.CommentTag.general_feedback,
            created_at=now - timedelta(days=3, hours=5),
        ))

        drawing_a.status = models.DrawingStatus.approved
        v1.superseded = True
        db.add(models.StatusEvent(drawing_id=drawing_a.id, version_id=v2.id, actor_id=raj.id, old_status="under_review", new_status="approved", note="Approved for manufacturing", created_at=now - timedelta(days=3, hours=5)))

        # --- Drawing B: currently blocked on an unresolved change request.
        drawing_b = models.Drawing(
            title="Housing Assembly Cover",
            designer_id=priya.id,
            status=models.DrawingStatus.draft,
            created_at=now - timedelta(days=2, hours=6),
        )
        db.add(drawing_b)
        db.flush()

        vb1 = models.DrawingVersion(
            drawing_id=drawing_b.id,
            version_number=1,
            file_path=_store(str(drawing_b.id), ".pdf", make_drawing_pdf("Housing Assembly Cover", "A", "Priya Nair", "HAC-2002")),
            file_type="pdf",
            original_filename="housing_assembly_cover_revA.pdf",
            uploaded_by=priya.id,
            uploaded_at=now - timedelta(days=2, hours=6),
        )
        db.add(vb1)
        db.add(models.StatusEvent(drawing_id=drawing_b.id, actor_id=priya.id, old_status=None, new_status="draft", note="Drawing created", created_at=now - timedelta(days=2, hours=6)))
        db.flush()

        drawing_b.status = models.DrawingStatus.under_review
        db.add(models.StatusEvent(drawing_id=drawing_b.id, version_id=vb1.id, actor_id=priya.id, old_status="draft", new_status="under_review", note="Submitted for review", created_at=now - timedelta(days=2, hours=5)))

        db.add(models.Comment(
            version_id=vb1.id,
            author_id=tom.id,
            body="Chamfer dimension on the cover edge is missing. Please add before resubmission.",
            tag=models.CommentTag.request_change,
            location_ref="Outer edge chamfer, sheet 1",
            created_at=now - timedelta(days=1, hours=20),
        ))
        drawing_b.status = models.DrawingStatus.changes_required
        db.add(models.StatusEvent(drawing_id=drawing_b.id, version_id=vb1.id, actor_id=tom.id, old_status="under_review", new_status="changes_required", note="Missing chamfer dimension", created_at=now - timedelta(days=1, hours=20)))

        # --- Drawing C: sitting in Draft, not yet submitted. JPEG format.
        drawing_c = models.Drawing(
            title="Actuator Bracket Reference Photo",
            designer_id=alice.id,
            status=models.DrawingStatus.draft,
            created_at=now - timedelta(hours=10),
        )
        db.add(drawing_c)
        db.flush()
        vc1 = models.DrawingVersion(
            drawing_id=drawing_c.id,
            version_number=1,
            file_path=_store(str(drawing_c.id), ".jpg", make_drawing_jpeg("Actuator Bracket Reference Photo", "A", "Alice Chen", "ABR-3003")),
            file_type="jpeg",
            original_filename="actuator_bracket_ref.jpg",
            uploaded_by=alice.id,
            uploaded_at=now - timedelta(hours=10),
        )
        db.add(vc1)
        db.add(models.StatusEvent(drawing_id=drawing_c.id, actor_id=alice.id, old_status=None, new_status="draft", note="Drawing created", created_at=now - timedelta(hours=10)))

        # --- Drawing D: freshly submitted, awaiting review. Demonstrates the
        #     "Under Review" state with no comments yet.
        drawing_d = models.Drawing(
            title="Support Bracket",
            designer_id=priya.id,
            status=models.DrawingStatus.draft,
            created_at=now - timedelta(hours=3),
        )
        db.add(drawing_d)
        db.flush()
        vd1 = models.DrawingVersion(
            drawing_id=drawing_d.id,
            version_number=1,
            file_path=_store(str(drawing_d.id), ".png", make_drawing_png("Support Bracket", "A", "Priya Nair", "SB-4004")),
            file_type="png",
            original_filename="support_bracket_revA.png",
            uploaded_by=priya.id,
            uploaded_at=now - timedelta(hours=3),
        )
        db.add(vd1)
        db.add(models.StatusEvent(drawing_id=drawing_d.id, actor_id=priya.id, old_status=None, new_status="draft", note="Drawing created", created_at=now - timedelta(hours=3)))
        db.flush()
        drawing_d.status = models.DrawingStatus.under_review
        db.add(models.StatusEvent(drawing_id=drawing_d.id, version_id=vd1.id, actor_id=priya.id, old_status="draft", new_status="under_review", note="Submitted for review", created_at=now - timedelta(hours=2)))

        db.commit()
        print("Seed complete: 4 users, 4 drawings.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
