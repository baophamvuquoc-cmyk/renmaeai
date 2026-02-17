"""
Projects API Routes

CRUD endpoints for managing projects in the Podcast Remake workflow.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import asyncio

from modules.projects_db import get_projects_db
from modules.websocket_hub import manager as ws_manager

router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str
    style_id: Optional[int] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    style_id: Optional[int] = None


@router.post("")
async def create_project(request: CreateProjectRequest):
    """Tạo project mới"""
    if not request.name or not request.name.strip():
        raise HTTPException(status_code=400, detail="Tên project không được để trống")

    try:
        db = get_projects_db()
        project_id = db.create_project(
            name=request.name.strip(),
            style_id=request.style_id
        )

        project = db.get_project(project_id)

        result = {
            "success": True,
            "project": project,
            "message": f"Đã tạo project '{request.name}'"
        }
        asyncio.ensure_future(ws_manager.broadcast("projects_updated", {"action": "created", "project_id": project_id}))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def get_all_projects():
    """Lấy danh sách tất cả projects"""
    try:
        db = get_projects_db()
        projects = db.get_all_projects()

        return {
            "success": True,
            "projects": projects,
            "count": len(projects)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: int):
    """Lấy chi tiết một project"""
    try:
        db = get_projects_db()
        project = db.get_project(project_id)

        if not project:
            raise HTTPException(status_code=404, detail="Project không tồn tại")

        return {
            "success": True,
            "project": project
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{project_id}")
async def update_project(project_id: int, request: UpdateProjectRequest):
    """Cập nhật project"""
    try:
        db = get_projects_db()

        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.status is not None:
            updates['status'] = request.status
        if request.style_id is not None:
            updates['style_id'] = request.style_id

        if not updates:
            raise HTTPException(status_code=400, detail="Không có thông tin cập nhật")

        success = db.update_project(project_id, updates)

        if not success:
            raise HTTPException(status_code=404, detail="Project không tồn tại")

        asyncio.ensure_future(ws_manager.broadcast("projects_updated", {"action": "updated", "project_id": project_id}))
        return {
            "success": True,
            "message": "Đã cập nhật project"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(project_id: int):
    """Xóa project"""
    try:
        db = get_projects_db()
        success = db.delete_project(project_id)

        if not success:
            raise HTTPException(status_code=404, detail="Project không tồn tại")

        asyncio.ensure_future(ws_manager.broadcast("projects_updated", {"action": "deleted", "project_id": project_id}))
        return {
            "success": True,
            "message": "Đã xóa project"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
