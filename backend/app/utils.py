import os
import uuid

from fastapi import HTTPException, UploadFile

from .database import UPLOAD_DIR

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".png": "png",
    ".jpg": "jpeg",
    ".jpeg": "jpeg",
}


def save_upload(file: UploadFile, drawing_id: int) -> tuple[str, str]:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Only PDF, PNG, or JPEG files are accepted")

    drawing_dir = os.path.join(UPLOAD_DIR, str(drawing_id))
    os.makedirs(drawing_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(drawing_dir, stored_name)

    with open(dest_path, "wb") as out:
        out.write(file.file.read())

    return os.path.relpath(dest_path, UPLOAD_DIR), ALLOWED_EXTENSIONS[ext]
