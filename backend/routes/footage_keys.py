"""
Footage API Key Pool Routes - CRUD endpoints for managing multiple API keys.
"""

import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Path, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from modules.footage_key_pool import get_key_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/footage-keys", tags=["Footage Keys"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class AddKeyRequest(BaseModel):
    api_key: str
    label: str = ""


class ToggleKeyRequest(BaseModel):
    active: bool


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/{source}")
async def list_keys(source: str = Path(..., pattern="^(pexels|pixabay)$")):
    """List all API keys for a source (pexels or pixabay)."""
    pool = get_key_pool()
    keys = pool.get_keys(source)

    # Mask the API keys for security (show first 8 + last 4 chars)
    masked_keys = []
    for k in keys:
        raw = k["api_key"]
        if len(raw) > 12:
            masked = raw[:8] + "..." + raw[-4:]
        else:
            masked = raw[:4] + "..."
        masked_keys.append({
            **k,
            "api_key_masked": masked,
            "api_key": raw,  # Keep full key for frontend to use when testing
        })

    return {
        "success": True,
        "source": source,
        "keys": masked_keys,
        "pool_status": pool.get_pool_status().get(source, {}),
    }


@router.post("/{source}")
async def add_key(
    source: str = Path(..., pattern="^(pexels|pixabay)$"),
    body: AddKeyRequest = Body(...),
):
    """Add a new API key to the pool."""
    pool = get_key_pool()
    key_id = pool.add_key(source, body.api_key, body.label)

    if key_id is None:
        return JSONResponse(
            status_code=409,
            content={"success": False, "error": "Key nay da ton tai trong pool"},
        )

    return {
        "success": True,
        "key_id": key_id,
        "message": f"Da them {source} key thanh cong",
    }


@router.delete("/{key_id}")
async def remove_key(key_id: int = Path(...)):
    """Remove a key from the pool."""
    pool = get_key_pool()
    existing = pool.get_key_by_id(key_id)
    if not existing:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Key khong ton tai"},
        )

    pool.remove_key(key_id)
    return {"success": True, "message": "Da xoa key thanh cong"}


@router.patch("/{key_id}/toggle")
async def toggle_key(
    key_id: int = Path(...),
    body: ToggleKeyRequest = Body(...),
):
    """Enable or disable a key."""
    pool = get_key_pool()
    existing = pool.get_key_by_id(key_id)
    if not existing:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Key khong ton tai"},
        )

    pool.toggle_key(key_id, body.active)
    status = "bat" if body.active else "tat"
    return {"success": True, "message": f"Da {status} key thanh cong"}


@router.post("/{source}/test")
async def test_key(
    source: str = Path(..., pattern="^(pexels|pixabay)$"),
    body: AddKeyRequest = Body(...),
):
    """Test a specific API key (does not need to be in the pool)."""
    api_key = body.api_key.strip()
    if not api_key:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "API key khong duoc de trong"},
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if source == "pexels":
                resp = await client.get(
                    "https://api.pexels.com/v1/collections",
                    params={"per_page": 1},
                    headers={"Authorization": api_key},
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Pexels API key hoat dong!"}
                elif resp.status_code == 401:
                    return JSONResponse(
                        status_code=401,
                        content={"success": False, "error": "API key khong hop le"},
                    )
                else:
                    return JSONResponse(
                        status_code=resp.status_code,
                        content={"success": False, "error": f"HTTP {resp.status_code}"},
                    )

            elif source == "pixabay":
                resp = await client.get(
                    "https://pixabay.com/api/videos/",
                    params={"key": api_key, "q": "nature", "per_page": 3},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "hits" in data:
                        return {"success": True, "message": "Pixabay API key hoat dong!"}
                    else:
                        return JSONResponse(
                            status_code=401,
                            content={"success": False, "error": "API key khong hop le"},
                        )
                elif resp.status_code == 401:
                    return JSONResponse(
                        status_code=401,
                        content={"success": False, "error": "API key khong hop le"},
                    )
                else:
                    return JSONResponse(
                        status_code=resp.status_code,
                        content={"success": False, "error": f"HTTP {resp.status_code}"},
                    )

    except httpx.TimeoutException:
        return JSONResponse(
            status_code=408,
            content={"success": False, "error": "Timeout - khong the ket noi toi API"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.get("")
async def get_pool_status():
    """Get overall key pool summary."""
    pool = get_key_pool()
    return {
        "success": True,
        "pool": pool.get_pool_status(),
    }
