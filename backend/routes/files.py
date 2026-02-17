from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
from modules.file_manager import FileManager

router = APIRouter()
file_manager = FileManager()


class ListDirectoryRequest(BaseModel):
    path: str


class RenamePreviewRequest(BaseModel):
    path: str
    files: List[str]
    pattern: Dict


class RenameExecuteRequest(BaseModel):
    path: str
    rename_map: Dict[str, str]


@router.post("/list")
async def list_directory(request: ListDirectoryRequest):
    """List files in a directory"""
    try:
        files = file_manager.list_directory(request.path)
        return {"success": True, "files": files}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Directory not found")
    except NotADirectoryError:
        raise HTTPException(status_code=400, detail="Path is not a directory")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rename-preview")
async def rename_preview(request: RenamePreviewRequest):
    """Generate rename preview without executing"""
    try:
        preview = file_manager.generate_rename_preview(
            request.files,
            request.pattern
        )
        return {"success": True, "preview": preview}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rename-execute")
async def rename_execute(request: RenameExecuteRequest):
    """Execute rename operation"""
    try:
        result = file_manager.execute_rename(request.rename_map)
        
        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error") or "Rename failed"
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
