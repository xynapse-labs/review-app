from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import Base, UPLOAD_DIR, engine
from .routers import auth, comments, drawings, notifications

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Digital Design Review Workflow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

app.include_router(auth.router)
app.include_router(drawings.router)
app.include_router(comments.router)
app.include_router(notifications.router)


@app.get("/health")
def health():
    return {"status": "ok"}
