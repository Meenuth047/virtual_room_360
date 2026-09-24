import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from .. import config, security
from ..auth import get_current_user
from ..db import db_cursor
from ..stitching import StitchError, generate_panorama
from .rooms import _get_owned_room, _room_dir

router = APIRouter(tags=["panorama"])
logger = logging.getLogger("panorama.routes")


def _validate_image(upload: UploadFile, contents: bytes):
    if upload.content_type not in config.ALLOWED_IMAGE_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload.filename}")
    if len(contents) > config.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"{upload.filename} exceeds the {config.MAX_FILE_SIZE_MB}MB size limit.",
        )
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail=f"{upload.filename} is empty.")


@router.post("/api/rooms/{room_id}/images", status_code=201)
async def upload_images(room_id: int, files: list[UploadFile], user=Depends(get_current_user)):
    with db_cursor() as cur:
        room = _get_owned_room(cur, room_id, user["id"])

    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")
    if len(files) > config.MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Too many images. Please upload at most {config.MAX_IMAGES} photos.",
        )

    source_dir = _room_dir(user["id"], room["category_id"], room_id) / "source"
    source_dir.mkdir(parents=True, exist_ok=True)

    saved = []
    try:
        for f in files:
            contents = await f.read()
            _validate_image(f, contents)
            filename = security.safe_filename(f.filename or "photo.jpg")
            dest = source_dir / filename
            dest.write_bytes(contents)
            saved.append(filename)
    except HTTPException:
        # Roll back any files saved in this batch before raising
        for name in saved:
            (source_dir / name).unlink(missing_ok=True)
        raise

    existing_count = len(list(source_dir.iterdir()))
    if existing_count > config.MAX_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Room already has too many photos (max {config.MAX_IMAGES}).",
        )

    return {"uploaded": len(saved), "total_source_images": existing_count}


@router.get("/api/rooms/{room_id}/images")
def list_room_images(room_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        room = _get_owned_room(cur, room_id, user["id"])
    source_dir = _room_dir(user["id"], room["category_id"], room_id) / "source"
    if not source_dir.exists():
        return {"images": []}
    return {"images": sorted(p.name for p in source_dir.iterdir() if p.is_file())}


@router.delete("/api/rooms/{room_id}/images/{filename}", status_code=204)
def delete_room_image(room_id: int, filename: str, user=Depends(get_current_user)):
    with db_cursor() as cur:
        room = _get_owned_room(cur, room_id, user["id"])
    source_dir = _room_dir(user["id"], room["category_id"], room_id) / "source"

    # Only allow deleting files we generated ourselves (hex-token names) within this room's dir
    target = (source_dir / filename).resolve()
    if source_dir.resolve() not in target.parents or not target.exists():
        raise HTTPException(status_code=404, detail="Image not found.")
    target.unlink()
    return None


@router.post("/api/rooms/{room_id}/generate", status_code=202)
def generate_room_panorama(room_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        room = _get_owned_room(cur, room_id, user["id"])

    source_dir = _room_dir(user["id"], room["category_id"], room_id) / "source"
    images = sorted(p for p in source_dir.iterdir() if p.is_file()) if source_dir.exists() else []

    if len(images) < config.MIN_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Please upload at least {config.MIN_IMAGES} photos "
                f"(recommended {config.RECOMMENDED_MIN_IMAGES}-{config.RECOMMENDED_MAX_IMAGES}) before generating."
            ),
        )
    if len(images) > config.MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Too many photos (max {config.MAX_IMAGES}).")

    panorama_dir = _room_dir(user["id"], room["category_id"], room_id) / "panorama"
    thumbnail_dir = _room_dir(user["id"], room["category_id"], room_id) / "thumbnail"
    panorama_path = panorama_dir / "panorama.jpg"
    thumbnail_path = thumbnail_dir / "thumb.jpg"

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO panoramas (room_id, original_image_count, processing_status) VALUES (?, ?, 'processing')",
            (room_id, len(images)),
        )
        panorama_id = cur.lastrowid

    try:
        generate_panorama(images, panorama_path, thumbnail_path)
    except StitchError as e:
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE panoramas SET processing_status = 'failed', error_message = ?, "
                "updated_at = datetime('now') WHERE id = ?",
                (str(e), panorama_id),
            )
        raise HTTPException(status_code=422, detail=str(e))
    except Exception:
        logger.exception("Unexpected error generating panorama for room %s", room_id)
        with db_cursor(commit=True) as cur:
            cur.execute(
                "UPDATE panoramas SET processing_status = 'failed', "
                "error_message = 'An unexpected error occurred while generating the panorama.', "
                "updated_at = datetime('now') WHERE id = ?",
                (panorama_id,),
            )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating the panorama. Please try again.",
        )

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE panoramas SET processing_status = 'complete', panorama_path = ?, thumbnail_path = ?, "
            "updated_at = datetime('now') WHERE id = ?",
            (
                str(panorama_path.relative_to(config.UPLOADS_DIR)),
                str(thumbnail_path.relative_to(config.UPLOADS_DIR)),
                panorama_id,
            ),
        )
        cur.execute("UPDATE rooms SET updated_at = datetime('now') WHERE id = ?", (room_id,))

    return {"panorama_id": panorama_id, "status": "complete"}


@router.get("/api/panoramas/{panorama_id}")
def get_panorama(panorama_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT p.* FROM panoramas p JOIN rooms r ON r.id = p.room_id "
            "WHERE p.id = ? AND r.user_id = ?",
            (panorama_id, user["id"]),
        )
        panorama = cur.fetchone()
    if panorama is None:
        raise HTTPException(status_code=404, detail="Panorama not found.")
    return dict(panorama)


@router.delete("/api/panoramas/{panorama_id}", status_code=204)
def delete_panorama(panorama_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT p.* FROM panoramas p JOIN rooms r ON r.id = p.room_id "
            "WHERE p.id = ? AND r.user_id = ?",
            (panorama_id, user["id"]),
        )
        panorama = cur.fetchone()
    if panorama is None:
        raise HTTPException(status_code=404, detail="Panorama not found.")

    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM panoramas WHERE id = ?", (panorama_id,))

    for key in ("panorama_path", "thumbnail_path"):
        rel = panorama[key]
        if rel:
            f = config.UPLOADS_DIR / rel
            f.unlink(missing_ok=True)
    return None


def _serve_asset(relative_path: str, room_id: int, user_id: int):
    """Serve a file from a room's directory only after verifying ownership."""
    with db_cursor() as cur:
        cur.execute("SELECT id FROM rooms WHERE id = ? AND user_id = ?", (room_id, user_id))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Not found.")

    base = config.UPLOADS_DIR.resolve()
    target = (config.UPLOADS_DIR / relative_path).resolve()
    if base not in target.parents or not target.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(target)


@router.get("/api/rooms/{room_id}/panorama-file")
def get_panorama_file(room_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        room = _get_owned_room(cur, room_id, user["id"])
        cur.execute(
            "SELECT panorama_path FROM panoramas WHERE room_id = ? AND processing_status = 'complete' "
            "ORDER BY created_at DESC LIMIT 1",
            (room_id,),
        )
        row = cur.fetchone()
    if row is None or not row["panorama_path"]:
        raise HTTPException(status_code=404, detail="No panorama available for this room.")
    return _serve_asset(row["panorama_path"], room_id, user["id"])


@router.get("/api/rooms/{room_id}/thumbnail-file")
def get_thumbnail_file(room_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        room = _get_owned_room(cur, room_id, user["id"])
        cur.execute(
            "SELECT thumbnail_path FROM panoramas WHERE room_id = ? AND processing_status = 'complete' "
            "ORDER BY created_at DESC LIMIT 1",
            (room_id,),
        )
        row = cur.fetchone()
    if row is None or not row["thumbnail_path"]:
        raise HTTPException(status_code=404, detail="No thumbnail available.")
    return _serve_asset(row["thumbnail_path"], room_id, user["id"])
