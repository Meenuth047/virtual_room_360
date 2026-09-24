import shutil

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr

from .. import config, storage
from ..auth import get_current_user
from ..db import db_cursor


router = APIRouter(prefix="/api/rooms", tags=["rooms"])


class RoomIn(BaseModel):
    category_id: int
    name: constr(min_length=1, max_length=100)
    description: str | None = None


class RoomUpdate(BaseModel):
    category_id: int | None = None
    name: constr(min_length=1, max_length=100) | None = None
    description: str | None = None


def _get_owned_room(cur, room_id: int, user_id: int):
    cur.execute("SELECT * FROM rooms WHERE id = ? AND user_id = ?", (room_id, user_id))
    room = cur.fetchone()
    if room is None:
        # Never reveal whether the room exists for another user
        raise HTTPException(status_code=404, detail="Room not found.")
    return room


def _room_dir(user_id: int, category_id: int, room_id: int):
    return config.UPLOADS_DIR / "users" / str(user_id) / "categories" / str(category_id) / "rooms" / str(room_id)


@router.get("")
def list_rooms(category_id: int | None = None, user=Depends(get_current_user)):
    query = (
        "SELECT r.id, r.name, r.description, r.category_id, c.name AS category_name, "
        "r.created_at, r.updated_at, "
        "(SELECT COUNT(*) FROM panoramas p WHERE p.room_id = r.id AND p.processing_status = 'complete') AS has_panorama, "
        "(SELECT p.thumbnail_path FROM panoramas p WHERE p.room_id = r.id AND p.processing_status = 'complete' "
        " ORDER BY p.created_at DESC LIMIT 1) AS thumbnail_path, "
        "(SELECT p.original_image_count FROM panoramas p WHERE p.room_id = r.id ORDER BY p.created_at DESC LIMIT 1) AS source_image_count "
        "FROM rooms r JOIN categories c ON c.id = r.category_id "
        "WHERE r.user_id = ?"
    )
    params = [user["id"]]
    if category_id is not None:
        query += " AND r.category_id = ?"
        params.append(category_id)
    query += " ORDER BY r.updated_at DESC"

    with db_cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_room(payload: RoomIn, user=Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT id FROM categories WHERE id = ? AND user_id = ?",
            (payload.category_id, user["id"]),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Category not found.")

    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO rooms (user_id, category_id, name, description) VALUES (?, ?, ?, ?)",
            (user["id"], payload.category_id, payload.name.strip(), payload.description),
        )
        room_id = cur.lastrowid

    return {"id": room_id, "name": payload.name.strip(), "category_id": payload.category_id}


@router.get("/{room_id}")
def get_room(room_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        room = _get_owned_room(cur, room_id, user["id"])
        cur.execute(
            "SELECT id, original_image_count, panorama_path, thumbnail_path, processing_status, "
            "error_message, created_at, updated_at FROM panoramas WHERE room_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (room_id,),
        )
        panorama = cur.fetchone()

    result = dict(room)
    result["panorama"] = dict(panorama) if panorama else None
    return result


@router.put("/{room_id}")
def update_room(room_id: int, payload: RoomUpdate, user=Depends(get_current_user)):
    with db_cursor() as cur:
        _get_owned_room(cur, room_id, user["id"])
        if payload.category_id is not None:
            cur.execute(
                "SELECT id FROM categories WHERE id = ? AND user_id = ?",
                (payload.category_id, user["id"]),
            )
            if cur.fetchone() is None:
                raise HTTPException(status_code=404, detail="Category not found.")

    fields, values = [], []
    if payload.category_id is not None:
        fields.append("category_id = ?")
        values.append(payload.category_id)
    if payload.name is not None:
        fields.append("name = ?")
        values.append(payload.name.strip())
    if payload.description is not None:
        fields.append("description = ?")
        values.append(payload.description)

    if fields:
        fields.append("updated_at = datetime('now')")
        values.extend([room_id, user["id"]])
        with db_cursor(commit=True) as cur:
            cur.execute(
                f"UPDATE rooms SET {', '.join(fields)} WHERE id = ? AND user_id = ?",
                values,
            )

    return {"ok": True}


@router.delete("/{room_id}", status_code=204)
def delete_room(room_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        room = _get_owned_room(cur, room_id, user["id"])
        cur.execute("SELECT panorama_path, thumbnail_path FROM panoramas WHERE room_id = ?", (room_id,))
        pano_rows = cur.fetchall()

    for p in pano_rows:
        storage.delete_asset(p["panorama_path"])
        storage.delete_asset(p["thumbnail_path"])

    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM rooms WHERE id = ? AND user_id = ?", (room_id, user["id"]))

    room_dir = _room_dir(user["id"], room["category_id"], room_id)
    if room_dir.exists():
        shutil.rmtree(room_dir, ignore_errors=True)

    return None

