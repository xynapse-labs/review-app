# Digital Design Review Workflow Platform

A minimal platform for submitting technical engineering drawings, collecting
threaded reviewer feedback, and tracking approval status through to release —
with an auditable compliance log of every version and status change.

## Features

- **Roles**: Designer (upload, submit, respond to comments) and Reviewer
  (comment, request changes, approve/reject). A reviewer can never approve a
  drawing they designed — enforced server-side, not just hidden in the UI.
- **Versioning**: every upload is a new version, displayed as a revision
  letter (Rev A, B, C...). Approving a version marks all earlier versions
  "superseded" — the current released baseline is always unambiguous.
- **Commenting**: threaded comments per version, tagged "Request Change" or
  "General Feedback", with an optional location reference (e.g. "sheet 1,
  top-left hole pattern"). Request-Change comments carry an open/resolved
  state so a reviewer can verify each flagged item was actually addressed,
  instead of re-reading the whole drawing on resubmission.
- **Status tracking**: Draft → Under Review → (Changes Required ⇄ new
  version auto-reopens review) → Approved. Uploading a new version after
  "Changes Required" automatically reopens the review cycle; revising an
  already-approved drawing drops it back to Draft for a fresh cycle.
- **Compliance log**: every version upload and every status change is
  recorded with who did it and when — visible per-drawing as an audit trail.
- **Auth**: minimal hardcoded users (see below), simple bearer-token
  sessions (no JWT, no password hashing — intentionally out of scope).
- **Bonus features implemented**: in-app notifications (simulated email
  alerts) on submission/comment/approval, and filtering the review
  queue/dashboard by status and date range.
- **Not implemented**: click-to-mark image annotation (region-anchored
  redlining) — comments support a free-text location reference instead; see
  Trade-offs below.

## Tech stack

- **Backend**: FastAPI + SQLAlchemy + SQLite, local disk file storage.
- **Frontend**: React (Vite), plain CSS, react-router.
- **Auth**: in-memory bearer-token session store on the backend.

## Project structure

```
backend/
  app/
    models.py       SQLAlchemy models (User, Drawing, DrawingVersion, Comment, StatusEvent, Notification)
    schemas.py       Pydantic request/response schemas
    auth.py          Minimal token-based auth
    utils.py         File upload validation/storage
    seed.py          Demo users, drawings, and generated demo files
    routers/         auth, drawings, comments, notifications endpoints
  uploads/           Uploaded/generated drawing files (created at runtime)
frontend/
  src/
    api.js           Backend API client
    context/AuthContext.jsx
    pages/           Login, Dashboard, DrawingDetail
    components/      Status/tag badges, notification bell
```

## Setup & Running

### Backend

macOS/Linux:

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/python -m app.seed        # (re)creates the DB with demo data
./venv/bin/uvicorn app.main:app --reload --port 8000
```

Windows (PowerShell):

```powershell
cd backend
py -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python -m app.seed
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

The API runs at `http://localhost:8000` (interactive docs at `/docs`).
Re-running `app.seed` wipes and rebuilds the database and uploaded files —
safe to run any time you want a clean demo state.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend expects the API at
`http://localhost:8000` by default; override with a `VITE_API_BASE` env var
if needed.

## Demo users

All hardcoded (see `backend/app/seed.py`); the login screen also lists them
as one-click buttons.

| Username | Password  | Role     | Name        |
|----------|-----------|----------|-------------|
| alice    | alice123  | designer | Alice Chen  |
| priya    | priya123  | designer | Priya Nair  |
| raj      | raj123    | reviewer | Raj Patel   |
| tom      | tom123    | reviewer | Tom Becker  |

## Demo data

Seeding creates four drawings covering every status and all three accepted
file formats:

- **Bracket Mounting Plate** (PNG, 2 versions) — full lifecycle: submitted,
  sent back with a Request-Change comment, resubmitted, comment resolved,
  approved. Rev A is marked superseded.
- **Housing Assembly Cover** (PDF, 1 version) — currently "Changes Required"
  with an open, unresolved Request-Change comment.
- **Actuator Bracket Reference Photo** (JPEG, 1 version) — sitting in
  "Draft", not yet submitted.
- **Support Bracket** (PNG, 1 version) — freshly submitted, "Under Review",
  no comments yet.

All drawing files are placeholder mechanical-part sheets generated
programmatically (Pillow/ReportLab) with title blocks, dimension lines, and
bolt-hole patterns, so they render as real image/PDF files in the viewer
without needing external CAD assets.

## Architecture & trade-offs

The backend is a single FastAPI service backed by SQLite with local-disk
file storage — deliberately the simplest stack that supports the workflow's
real constraint: every state transition (new version, comment, approve/
reject) must produce an immutable, attributable audit record. That's why
`StatusEvent` is a separate append-only table rather than just overwriting
`Drawing.status`, and why comment resolution is tracked as its own
who/when-stamped field rather than a boolean the UI infers. Versions are
never deleted or mutated — they're superseded, preserving the version
history requirement. Authentication is intentionally minimal (hardcoded
users, an in-memory bearer-token map, plaintext password comparison) since
the brief explicitly scoped out real user management and advanced security;
this would not survive a restart of the backend process or scale past a
single instance, which is fine for a local demo but is the first thing to
replace before any real deployment.

The main trade-off is the image-annotation bonus (click-to-mark a region on
the drawing and comment on it): true region-anchored redlining needs
click-coordinate capture layered over the rendered file and version-relative
coordinate storage, which was cut in favor of getting the core submit →
review → comment → status → audit loop fully correct and enforced (including
segregation of duties and the auto-reopen-on-resubmission behavior). As a
stand-in, comments carry a free-text `location_ref` field so feedback can
still point at "where" on the drawing without the visual affordance. Other
simplifications: SQLite and local disk storage instead of Postgres/S3 (fine
for a single-instance demo, not for concurrent production use), and a single
reviewer sign-off per version rather than a multi-approver sign-off matrix
(common in regulated shops but out of scope for this brief).
