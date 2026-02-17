"""
Voice Generation API Routes

Endpoints:
- POST /generate          — Generate voice for 1 scene
- POST /generate-batch    — Generate voice for multiple scenes (SSE streaming progress)
- GET  /download/{filename} — Download a single audio file
- POST /download-all      — Zip and download all audio files
- GET  /voices            — List available voices
- GET  /files             — List generated audio files
- POST /cleanup           — Delete all generated audio files
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import json
import asyncio
import zipfile
import io
import time

from modules.tts_engine import (
    generate_edge_tts,
    generate_batch_edge_tts,
    get_voice_list_flat,
    get_all_voices,
    VOICE_OUTPUT_DIR,
)

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class GenerateVoiceRequest(BaseModel):
    text: str
    voice: str = "vi-VN-HoaiMyNeural"
    language: str = "vi"
    speed: float = 1.0
    scene_id: int = 1


class SceneItem(BaseModel):
    scene_id: int
    content: str
    voiceExport: bool = True


class BatchGenerateRequest(BaseModel):
    scenes: List[SceneItem]
    voice: str = "vi-VN-HoaiMyNeural"
    language: str = "vi"
    speed: float = 1.0


class DownloadAllRequest(BaseModel):
    filenames: List[str]


class CleanupRequest(BaseModel):
    filenames: Optional[List[str]] = None  # None = cleanup all


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/voices")
async def list_voices():
    """Liệt kê tất cả giọng có sẵn, theo ngôn ngữ."""
    return {
        "success": True,
        "voices": get_voice_list_flat(),
        "voices_by_language": get_all_voices(),
    }


@router.post("/generate")
async def generate_voice(request: GenerateVoiceRequest):
    """Tạo voice cho 1 đoạn text / 1 scene."""
    if not request.text or len(request.text.strip()) < 2:
        raise HTTPException(status_code=400, detail="Text cần ít nhất 2 ký tự")

    if request.speed < 0.5 or request.speed > 2.0:
        raise HTTPException(status_code=400, detail="Speed phải từ 0.5 đến 2.0")

    try:
        filename = f"scene_{request.scene_id:03d}"
        path = await generate_edge_tts(
            text=request.text.strip(),
            voice=request.voice,
            speed=request.speed,
            output_filename=filename,
        )

        return {
            "success": True,
            "scene_id": request.scene_id,
            "filename": f"{filename}.mp3",
            "download_url": f"/api/voice/download/{filename}.mp3",
        }

    except Exception as e:
        import traceback
        print(f"[Voice] Error: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-batch")
async def generate_batch_voice(request: BatchGenerateRequest):
    """
    Tạo voice hàng loạt cho nhiều scenes.
    Trả về SSE stream với progress real-time.
    """
    export_scenes = [s for s in request.scenes if s.voiceExport]

    if not export_scenes:
        raise HTTPException(status_code=400, detail="Không có scene nào được chọn để xuất voice")

    async def event_generator():
        total = len(export_scenes)
        results = []
        
        # Validate language-voice consistency
        voice_prefix = request.voice.split("-")[0] if request.voice else ""
        if voice_prefix and request.language and voice_prefix != request.language:
            print(f"[Voice Batch] Warning: language='{request.language}' but voice='{request.voice}' (prefix='{voice_prefix}')")
        
        for i, scene in enumerate(export_scenes):
            scene_id = scene.scene_id
            content = scene.content
            filename = f"scene_{scene_id:03d}"

            # Send progress
            progress = {
                "type": "progress",
                "current": i + 1,
                "total": total,
                "scene_id": scene_id,
                "percentage": int(((i + 1) / total) * 100),
                "message": f"Đang tạo voice scene {scene_id}/{total}..."
            }
            yield f"data: {json.dumps(progress, ensure_ascii=False)}\n\n"

            try:
                path = await generate_edge_tts(
                    text=content,
                    voice=request.voice,
                    speed=request.speed,
                    output_filename=filename,
                )
                
                # Measure audio duration
                duration_seconds = 0.0
                try:
                    from mutagen.mp3 import MP3
                    mp3_path = os.path.join(VOICE_OUTPUT_DIR, f"{filename}.mp3")
                    audio = MP3(mp3_path)
                    duration_seconds = round(audio.info.length, 2)
                except Exception:
                    pass
                
                results.append({
                    "scene_id": scene_id,
                    "filename": f"{filename}.mp3",
                    "download_url": f"/api/voice/download/{filename}.mp3",
                    "success": True,
                    "duration_seconds": duration_seconds,
                })
                
                # Send scene_done event with measured duration
                scene_done = {
                    "type": "scene_done",
                    "scene_id": scene_id,
                    "filename": f"{filename}.mp3",
                    "download_url": f"/api/voice/download/{filename}.mp3",
                    "duration_seconds": duration_seconds,
                    "success": True,
                }
                yield f"data: {json.dumps(scene_done, ensure_ascii=False)}\n\n"
            except Exception as e:
                print(f"[Voice Batch] Error scene {scene_id}: {e}")
                results.append({
                    "scene_id": scene_id,
                    "filename": None,
                    "success": False,
                    "error": str(e),
                    "duration_seconds": 0.0,
                })

        # Calculate total duration
        total_duration = sum(r.get("duration_seconds", 0) for r in results if r["success"])
        
        # Send final result
        result_data = {
            "type": "result",
            "success": True,
            "results": results,
            "total_generated": sum(1 for r in results if r["success"]),
            "total_failed": sum(1 for r in results if not r["success"]),
            "total_duration_seconds": round(total_duration, 2),
        }
        yield f"event: result\ndata: {json.dumps(result_data, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/download/{filename}")
async def download_voice_file(filename: str):
    """Download 1 file audio."""
    filepath = os.path.join(VOICE_OUTPUT_DIR, filename)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"File '{filename}' không tồn tại")

    return FileResponse(
        path=filepath,
        media_type="audio/mpeg",
        filename=filename,
    )


@router.post("/download-all")
async def download_all_voices(request: DownloadAllRequest):
    """Zip tất cả audio files và download."""
    if not request.filenames:
        raise HTTPException(status_code=400, detail="Danh sách file trống")

    # Create zip in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in request.filenames:
            filepath = os.path.join(VOICE_OUTPUT_DIR, filename)
            if os.path.exists(filepath):
                zf.write(filepath, filename)
            else:
                print(f"[Voice] Warning: File not found for zip: {filename}")

    zip_buffer.seek(0)

    timestamp = int(time.time())
    zip_filename = f"voices_{timestamp}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename={zip_filename}",
        }
    )


@router.get("/files")
async def list_voice_files():
    """Liệt kê tất cả voice files đã tạo."""
    files = []
    if os.path.exists(VOICE_OUTPUT_DIR):
        for f in sorted(os.listdir(VOICE_OUTPUT_DIR)):
            if f.endswith(('.mp3', '.wav')):
                filepath = os.path.join(VOICE_OUTPUT_DIR, f)
                files.append({
                    "filename": f,
                    "size_bytes": os.path.getsize(filepath),
                    "download_url": f"/api/voice/download/{f}",
                })

    return {
        "success": True,
        "files": files,
        "count": len(files),
    }


@router.post("/cleanup")
async def cleanup_voice_files(request: CleanupRequest):
    """Xóa voice files đã tạo."""
    deleted = 0

    if request.filenames:
        # Delete specific files
        for filename in request.filenames:
            filepath = os.path.join(VOICE_OUTPUT_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                deleted += 1
    else:
        # Delete all files
        if os.path.exists(VOICE_OUTPUT_DIR):
            for f in os.listdir(VOICE_OUTPUT_DIR):
                filepath = os.path.join(VOICE_OUTPUT_DIR, f)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    deleted += 1

    return {
        "success": True,
        "deleted": deleted,
        "message": f"Đã xóa {deleted} files",
    }
