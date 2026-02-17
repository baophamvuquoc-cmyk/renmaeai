"""
Productions API Routes — Manage completed queue outputs.

Endpoints:
- GET    /               — List all productions (with optional search)
- GET    /stats          — Get aggregate stats
- GET    /:id            — Get production detail with files
- DELETE /:id            — Delete production (optionally delete files)
- POST   /               — Create production record manually
- GET    /:id/files      — List files in export directory
- POST   /:id/open       — Open export directory in OS file explorer
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import subprocess
import sys
import os
from pathlib import Path

from modules.production_store import get_production_store

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# Request Models
# ═══════════════════════════════════════════════════════════════════════════════

class CreateProductionRequest(BaseModel):
    title: str = ""
    export_dir: str = ""
    project_name: str = ""
    original_link: str = ""
    description: str = ""
    thumbnail: str = ""
    keywords: str = ""
    script_full: str = ""
    script_split: str = ""
    voiceover: str = ""
    video_footage: str = ""
    video_final: str = ""
    upload_platform: str = ""
    channel_name: str = ""
    video_status: str = "draft"
    preset_name: str = ""
    voice_id: str = ""
    prompts_reference: str = ""
    prompts_scene_builder: str = ""
    prompts_concept: str = ""
    prompts_video: str = ""
    settings_snapshot: Dict[str, Any] = {}


class UpdateProductionRequest(BaseModel):
    project_name: Optional[str] = None
    original_link: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail: Optional[str] = None
    keywords: Optional[str] = None
    script_full: Optional[str] = None
    script_split: Optional[str] = None
    voiceover: Optional[str] = None
    video_footage: Optional[str] = None
    video_final: Optional[str] = None
    upload_platform: Optional[str] = None
    channel_name: Optional[str] = None
    video_status: Optional[str] = None
    prompts_reference: Optional[str] = None
    prompts_scene_builder: Optional[str] = None
    prompts_concept: Optional[str] = None
    prompts_video: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/stats")
async def get_stats():
    """Get aggregate production stats"""
    try:
        store = get_production_store()
        stats = store.get_stats()
        return {"success": True, **stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_productions(
    search: str = Query("", description="Search by title"),
    limit: int = Query(100, ge=1, le=500),
):
    """List all productions, newest first"""
    try:
        store = get_production_store()
        productions = store.get_all_productions(search=search, limit=limit)
        return {
            "success": True,
            "productions": productions,
            "count": len(productions),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{production_id}")
async def get_production(production_id: int):
    """Get production detail"""
    try:
        store = get_production_store()
        production = store.get_production(production_id)

        if not production:
            raise HTTPException(status_code=404, detail="Production không tồn tại")

        return {"success": True, "production": production}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{production_id}/files")
async def get_production_files(production_id: int):
    """List all files in the production's export directory"""
    try:
        store = get_production_store()
        production = store.get_production(production_id)

        if not production:
            raise HTTPException(status_code=404, detail="Production không tồn tại")

        file_info = store.scan_export_dir(production["export_dir"])
        return {"success": True, **file_info}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def create_production(request: CreateProductionRequest):
    """Create a new production record, auto-saving text/URL content as files."""
    try:
        store = get_production_store()
        production_id = store.create_production(
            title=request.title.strip(),
            export_dir=request.export_dir,
            project_name=request.project_name,
            original_link=request.original_link,
            description=request.description,
            thumbnail=request.thumbnail,
            keywords=request.keywords,
            script_full=request.script_full,
            script_split=request.script_split,
            voiceover=request.voiceover,
            video_footage=request.video_footage,
            video_final=request.video_final,
            upload_platform=request.upload_platform,
            channel_name=request.channel_name,
            video_status=request.video_status,
            preset_name=request.preset_name,
            voice_id=request.voice_id,
            prompts_reference=request.prompts_reference,
            prompts_scene_builder=request.prompts_scene_builder,
            prompts_concept=request.prompts_concept,
            prompts_video=request.prompts_video,
            settings_snapshot=request.settings_snapshot,
        )

        # ── Auto-save: only script_split (as file) and thumbnail (download URL) ──
        # All other fields (script_full, description, keywords, prompts) stay as
        # plaintext directly in the DB for easy display in Production Hub.
        updates = {}
        prod_dir = Path(__file__).parent.parent / "productions_data" / str(production_id)

        def _is_file_path(val: str) -> bool:
            """Check if value looks like a real file/dir path."""
            if not val:
                return False
            return ('\\' in val or '/' in val) and len(val) < 500

        try:
            # Save script_split as file (scenes data — can be large CSV)
            if request.script_split and not _is_file_path(request.script_split):
                prod_dir.mkdir(parents=True, exist_ok=True)
                split_file = prod_dir / "scenes.txt"
                split_file.write_text(request.script_split, encoding="utf-8")
                updates["script_split"] = str(split_file)

            # Save thumbnail: download URL or decode base64
            if request.thumbnail:
                if request.thumbnail.startswith(("http://", "https://")):
                    try:
                        import urllib.request
                        prod_dir.mkdir(parents=True, exist_ok=True)
                        thumb_file = prod_dir / "thumbnail.jpg"
                        urllib.request.urlretrieve(request.thumbnail, str(thumb_file))
                        updates["thumbnail"] = str(thumb_file)
                    except Exception as dl_err:
                        print(f"[Productions] Thumbnail download failed: {dl_err}")
                elif request.thumbnail.startswith("data:image"):
                    try:
                        import base64
                        prod_dir.mkdir(parents=True, exist_ok=True)
                        header, b64data = request.thumbnail.split(",", 1)
                        ext = "png" if "png" in header else "jpg"
                        thumb_file = prod_dir / f"thumbnail.{ext}"
                        thumb_file.write_bytes(base64.b64decode(b64data))
                        updates["thumbnail"] = str(thumb_file)
                    except Exception as b64_err:
                        print(f"[Productions] Thumbnail base64 decode failed: {b64_err}")

            # Update DB with file paths (only for script_split + thumbnail)
            if updates:
                store.update_production(production_id, updates)
        except Exception as save_err:
            print(f"[Productions] Auto-save files failed (non-blocking): {save_err}")

        production = store.get_production(production_id)
        return {
            "success": True,
            "production": production,
            "message": f"Đã tạo production '{request.title}'",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{production_id}")
async def update_production(production_id: int, request: UpdateProductionRequest):
    """Update a production record"""
    try:
        store = get_production_store()
        updates = {k: v for k, v in request.dict().items() if v is not None}

        if not updates:
            raise HTTPException(status_code=400, detail="Không có thông tin cập nhật")

        success = store.update_production(production_id, updates)
        if not success:
            raise HTTPException(status_code=404, detail="Production không tồn tại")

        return {"success": True, "message": "Đã cập nhật production"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{production_id}")
async def delete_production(production_id: int, delete_files: bool = Query(False)):
    """Delete a production record. Optionally delete the export files too."""
    try:
        store = get_production_store()
        export_dir = store.delete_production(production_id)

        if export_dir is None:
            raise HTTPException(status_code=404, detail="Production không tồn tại")

        files_deleted = False
        if delete_files and export_dir:
            dir_path = Path(export_dir)
            if dir_path.exists():
                import shutil
                shutil.rmtree(str(dir_path), ignore_errors=True)
                files_deleted = True
                print(f"[Productions] Deleted export dir: {export_dir}")

        return {
            "success": True,
            "message": "Đã xóa production",
            "files_deleted": files_deleted,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{production_id}/open")
async def open_production_folder(production_id: int):
    """Open the production's export directory in OS file explorer"""
    try:
        store = get_production_store()
        production = store.get_production(production_id)

        if not production:
            raise HTTPException(status_code=404, detail="Production không tồn tại")

        export_dir = production["export_dir"]
        if not Path(export_dir).exists():
            raise HTTPException(status_code=404, detail=f"Thư mục không tồn tại: {export_dir}")

        # Open in OS file explorer
        if sys.platform == "win32":
            os.startfile(export_dir)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", export_dir])
        else:
            subprocess.Popen(["xdg-open", export_dir])

        return {"success": True, "message": "Đã mở thư mục"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Open File — Open any file path with OS default application
# ═══════════════════════════════════════════════════════════════════════════════

class OpenFileRequest(BaseModel):
    file_path: str

@router.post("/open-file")
async def open_file(request: OpenFileRequest):
    """Open a file with the OS default application."""
    try:
        file_path = Path(request.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File không tồn tại: {request.file_path}")

        if sys.platform == "win32":
            os.startfile(str(file_path))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(file_path)])
        else:
            subprocess.Popen(["xdg-open", str(file_path)])

        return {"success": True, "message": f"Đã mở {file_path.name}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# Scan & Import — Detect existing pipeline results and create production records
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/scan-import")
async def scan_and_import():
    """Scan output directories for existing results and import them into Production Hub."""
    try:
        store = get_production_store()
        backend_dir = Path(__file__).parent.parent
        voice_dir = backend_dir / "voice_output"
        video_dir = backend_dir / "video_output"

        imported = []

        # Scan for final videos — each final_video.mp4 represents a complete pipeline run
        final_video = video_dir / "final_video.mp4" if video_dir.exists() else None
        has_final_video = final_video is not None and final_video.exists()

        # Count voice and scene video files
        voice_files = sorted(voice_dir.glob("scene_*.mp3")) if voice_dir.exists() else []
        scene_videos = sorted(video_dir.glob("scene_*.mp4")) if video_dir.exists() else []

        if has_final_video or voice_files or scene_videos:
            from datetime import datetime

            # Determine the most recent modification time for title
            mod_time = None
            if has_final_video:
                mod_time = final_video.stat().st_mtime
            elif voice_files:
                mod_time = max(f.stat().st_mtime for f in voice_files)
            elif scene_videos:
                mod_time = max(f.stat().st_mtime for f in scene_videos)

            time_str = datetime.fromtimestamp(mod_time).strftime("%d/%m/%Y %H:%M") if mod_time else "Unknown"
            title = f"Project {time_str}"

            voice_path = str(voice_dir) if voice_files else ""
            video_final_path = str(final_video) if has_final_video else ""
            video_footage_path = str(video_dir) if scene_videos else ""

            production_id = store.create_production(
                title=title,
                project_name="Imported",
                description=f"Auto-imported: {len(voice_files)} voice files, {len(scene_videos)} scene videos" + (", 1 final video" if has_final_video else ""),
                voiceover=voice_path,
                video_final=video_final_path,
                video_footage=video_footage_path,
                video_status="draft",
            )

            imported.append({
                "id": production_id,
                "title": title,
                "voice_files": len(voice_files),
                "scene_videos": len(scene_videos),
                "has_final_video": has_final_video,
            })

        # Also scan for any export directories
        for export_candidate in backend_dir.glob("export_*"):
            if export_candidate.is_dir():
                files_in_export = list(export_candidate.iterdir())
                if files_in_export:
                    from datetime import datetime
                    mod_time = export_candidate.stat().st_mtime
                    time_str = datetime.fromtimestamp(mod_time).strftime("%d/%m/%Y %H:%M")

                    production_id = store.create_production(
                        title=f"Export {time_str}",
                        project_name="Imported",
                        description=f"Auto-imported from export dir: {len(files_in_export)} files",
                        export_dir=str(export_candidate),
                        video_status="draft",
                    )

                    imported.append({
                        "id": production_id,
                        "title": f"Export {time_str}",
                        "export_dir": str(export_candidate),
                        "file_count": len(files_in_export),
                    })

        return {
            "success": True,
            "imported_count": len(imported),
            "imported": imported,
            "message": f"Đã import {len(imported)} production(s) từ file trên ổ đĩa" if imported else "Không tìm thấy kết quả nào trên ổ đĩa",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
