from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr

from ..auth import get_current_user
from ..db import db_cursor

router = APIRouter(prefix="/api/categories", tags=["categories"])


class CategoryIn(BaseModel):
    name: constr(min_length=1, max_length=60)


def _get_owned_category(cur, category_id: int, user_id: int):
    cur.execute("SELECT * FROM categories WHERE id = ? AND user_id = ?", (category_id, user_id))
    cat = cur.fetchone()
    if cat is None:
        raise HTTPException(status_code=404, detail="Category not found.")
    return cat


@router.get("")
def list_categories(user=Depends(get_current_user)):
    with db_cursor() as cur:
        cur.execute(
            "SELECT c.id, c.name, c.created_at, "
            "(SELECT COUNT(*) FROM rooms r WHERE r.category_id = c.id) AS room_count "
            "FROM categories c WHERE c.user_id = ? ORDER BY c.name",
            (user["id"],),
        )
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("", status_code=201)
def create_category(payload: CategoryIn, user=Depends(get_current_user)):
    name = payload.name.strip()
    with db_cursor() as cur:
        cur.execute("SELECT id FROM categories WHERE user_id = ? AND name = ?", (user["id"], name))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="A category with this name already exists.")

    with db_cursor(commit=True) as cur:
        cur.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (user["id"], name))
        new_id = cur.lastrowid
    return {"id": new_id, "name": name}


@router.put("/{category_id}")
def update_category(category_id: int, payload: CategoryIn, user=Depends(get_current_user)):
    with db_cursor() as cur:
        _get_owned_category(cur, category_id, user["id"])

    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE categories SET name = ? WHERE id = ? AND user_id = ?",
            (payload.name.strip(), category_id, user["id"]),
        )
    return {"id": category_id, "name": payload.name.strip()}


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, user=Depends(get_current_user)):
    with db_cursor() as cur:
        _get_owned_category(cur, category_id, user["id"])
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM categories WHERE id = ? AND user_id = ?", (category_id, user["id"]))
    return None
