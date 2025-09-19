from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, date
from ..db.session import get_db
from ..models.footprint import Footprint
from ..schemas.footprint import FootprintCreate, FootprintOut, FootprintUpdate
from .deps import get_current_user
from ..utils.response import ok, fail

router = APIRouter(prefix="/footprints", tags=["footprints"])


def _parse_date(d):
    if d is None or d == "":
        return None
    if isinstance(d, date):
        return d
    try:
        return datetime.strptime(str(d), "%Y-%m-%d").date()
    except Exception:
        return None


@router.get("/")
def list_my_footprints(db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        items = db.query(Footprint).filter(Footprint.user_id == user.id).order_by(Footprint.id.desc()).all()
        data = [_to_out_model(item) for item in items]
        return ok(data)
    except Exception as e:
        return fail(str(e))


@router.post("/")
def create_footprint(body: FootprintCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        tags_str = ",".join(body.tags or [])
        item = Footprint(
            user_id=user.id,
            name=body.name,
            lng=body.lng,
            lat=body.lat,
            type=body.type,
            date=_parse_date(body.date),
            tags=tags_str,
            notes=body.notes,
            is_public=bool(body.is_public),
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return ok(_to_out_model(item), "创建成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


# 先定义固定路径，避免被 /{item_id} 抢占
@router.get("/mine")
def list_my_footprints_mine(db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        items = db.query(Footprint).filter(Footprint.user_id == user.id).order_by(Footprint.id.desc()).all()
        data = [_to_out_model(item) for item in items]
        return ok(data)
    except Exception as e:
        return fail(str(e))

@router.get("/public")
def list_public_footprints(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        items = (
            db.query(Footprint)
            .filter(Footprint.is_public == True)  # noqa: E712
            .order_by(Footprint.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        data = [_to_out_model(i) for i in items]
        return ok(data)
    except Exception as e:
        return fail(str(e))


@router.get("/{item_id}")
def get_footprint(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        item = db.query(Footprint).filter(Footprint.id == item_id, Footprint.user_id == user.id).first()
        if not item:
            return fail("Not found")
        return ok(_to_out_model(item))
    except Exception as e:
        return fail(str(e))


@router.put("/{item_id}")
def update_footprint(item_id: int, body: FootprintUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        item = db.query(Footprint).filter(Footprint.id == item_id, Footprint.user_id == user.id).first()
        if not item:
            return fail("Not found")
        if body.name is not None:
            item.name = body.name
        if body.lng is not None:
            item.lng = body.lng
        if body.lat is not None:
            item.lat = body.lat
        if body.type is not None:
            item.type = body.type
        if body.date is not None:
            item.date = _parse_date(body.date)
        if body.tags is not None:
            item.tags = ",".join(body.tags)
        if body.notes is not None:
            item.notes = body.notes
        if body.is_public is not None:
            item.is_public = bool(body.is_public)
        db.commit()
        db.refresh(item)
        return ok(_to_out_model(item), "更新成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


@router.delete("/{item_id}")
def delete_footprint(item_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        item = db.query(Footprint).filter(Footprint.id == item_id, Footprint.user_id == user.id).first()
        if not item:
            return fail("Not found")
        db.delete(item)
        db.commit()
        return ok(True, "删除成功")
    except Exception as e:
        db.rollback()
        return fail(str(e))


def _to_out(item: Footprint) -> FootprintOut:
    return FootprintOut(
        id=item.id,
        user_id=item.user_id,
        name=item.name,
        lng=item.lng,
        lat=item.lat,
        type=item.type,
        date=item.date,
        tags=(item.tags.split(",") if item.tags else []),
        notes=item.notes,
        is_public=bool(item.is_public),
        created_at=item.created_at,
    )


def _to_out_model(item: Footprint) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "name": item.name,
        "lng": item.lng,
        "lat": item.lat,
        "type": item.type,
        "date": item.date.isoformat() if item.date else None,
        "tags": (item.tags.split(",") if item.tags else []),
        "notes": item.notes,
        "is_public": bool(item.is_public),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }
