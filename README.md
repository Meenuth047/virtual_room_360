---
title: Virtual Room 360
emoji: 🏠
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 360 Rooms

A lightweight web app for turning a handful of phone photos into an interactive
360° panorama of a room. Register → create categories/rooms → upload 8-40
overlapping photos → generate → view in browser → save to your account.

Built to be simple and cheap to run: no GPU, no AI models, no heavy 3D
reconstruction. Classical OpenCV feature-matching stitching, SQLite, and a
plain HTML/CSS/JS frontend with a small Three.js 360 viewer.

## Stack

- **Backend:** Python + FastAPI, stdlib `sqlite3`, Argon2id password hashing
  (`argon2-cffi`), OpenCV (`cv2.Stitcher`) for panorama stitching.
- **Database:** SQLite (`data/app.db`), created automatically on first run.
- **Storage:** Local filesystem under `uploads/users/<user_id>/...`.
- **Frontend:** Static HTML/CSS/vanilla JS, no build step. Three.js (via CDN)
  powers the 360 sphere viewer.
- **Auth:** Server-side sessions in SQLite, delivered via an HTTP-only cookie.

## Running it

```bash
cd backend
pip install -r requirements.txt
cd ..
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000` in a browser. The database and uploads
directory are created automatically on first run.

### Configuration

Environment variables (all optional, sensible defaults are baked in):

| Variable | Default | Purpose |
|---|---|---|
| `SESSION_TTL_HOURS` | 72 | How long a login session lasts |
| `MIN_IMAGES` | 8 | Minimum photos required to generate a panorama |
| `RECOMMENDED_MIN_IMAGES` / `RECOMMENDED_MAX_IMAGES` | 15 / 30 | Shown as guidance to the user |
| `MAX_IMAGES` | 40 | Hard cap per room |
| `MAX_FILE_SIZE_MB` | 15 | Per-photo upload size limit |
| `MAX_SOURCE_DIMENSION` | 2000 | Source photos are downscaled to this before stitching, to keep memory usage low |
| `CORS_ORIGINS` | `http://localhost:8000` | Comma-separated allowed origins |

For production, put these in a `.env` file (never commit it) and serve over
HTTPS — then flip `secure=True` on the session cookie in
`backend/routers/auth_routes.py`.

## How photo capture works

Users are guided to stand roughly in the center of the room, rotate slowly,
and take a photo every 20-30°, keeping 30-50% overlap between neighbors —
8 photos minimum, 15-30 recommended, 40 maximum. The backend stitches these
with OpenCV's built-in `Stitcher` (classical feature matching + homography,
not AI, not GPU-bound) and fits the result onto a 2:1 equirectangular canvas
so it works with any standard 360 sphere viewer.

This produces a wide panoramic photo of the room, not a full 3D
reconstruction — by design, per the lightweight-first requirement.

## Project layout

```
backend/
  main.py              FastAPI app, mounts the frontend as static files
  config.py             All tunables in one place
  db.py                 SQLite schema + connection helpers
  security.py            Argon2id hashing, session tokens, safe filenames
  auth.py                 get_current_user() FastAPI dependency
  stitching.py            OpenCV panorama generation
  routers/
    auth_routes.py        /api/auth/*
    categories.py          /api/categories/*
    rooms.py                /api/rooms/* (CRUD)
    panorama.py              image upload, generate, authenticated file serving
frontend/
  index.html               Login / register
  dashboard.html            Categories + room grid
  room.html                 Upload photos, generate, 360 viewer
  static/css/style.css
  static/js/{api,auth,dashboard,room,viewer}.js
data/app.db                SQLite database (created at runtime)
uploads/users/<id>/...      Per-user photo/panorama storage (created at runtime)
```

## Security notes

- Passwords are hashed with Argon2id; the raw password is never stored or logged.
- Sessions are random 256-bit tokens stored server-side in SQLite, sent as an
  HTTP-only cookie (not accessible to JS, not put in localStorage).
- Every room/category/panorama/image lookup is scoped by `WHERE user_id = ?`
  against the authenticated session — a user ID from the frontend is never
  trusted on its own, and cross-user requests return a generic 404 rather
  than revealing that the resource exists.
- Uploaded files are renamed to a random hex token; the original filename is
  never used to build a path, and file access is checked with `resolve()` +
  a parent-directory containment check to block path traversal.
- File type is validated by both MIME type and extension; size is capped
  per file and by total image count per room.
- Unhandled backend exceptions are caught and returned as a generic message
  — no stack traces or internals reach the client.
