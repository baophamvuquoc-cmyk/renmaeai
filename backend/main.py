import sys
import os
import time

_startup_t = time.time()
print(f"[Startup] Loading backend...")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import files, ai, ai_settings, script_workflow, voice, footage, footage_keys, projects, export, youtube_extract, productions, seo

print(f"[Startup] Routes loaded in {time.time()-_startup_t:.1f}s")



app = FastAPI(
    title="Auto Media Architecture API",
    description="Backend for AI-powered video production and file management",
    version="1.0.0"
)

# CORS Configuration — supports both Electron (localhost) and Web deployments
_default_origins = ["http://localhost:5173", "http://localhost:3000", "http://localhost:4173"]
_env_origins = os.environ.get("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(ai_settings.router, prefix="/api/ai", tags=["AI Settings"])
app.include_router(script_workflow.router, prefix="/api/workflow", tags=["Script Workflow"])
app.include_router(voice.router, prefix="/api/voice", tags=["Voice"])
app.include_router(footage.router, tags=["Footage"])  # prefix already in router
app.include_router(footage_keys.router, tags=["Footage Keys"])  # prefix already in router
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(youtube_extract.router, prefix="/api/youtube", tags=["YouTube"])
app.include_router(productions.router, prefix="/api/productions", tags=["Productions"])
app.include_router(seo.router, prefix="/api/seo", tags=["SEO"])


# ── FFmpeg auto-detect at startup ──
try:
    from modules.ffmpeg_setup import get_ffmpeg_info
    _ffmpeg_info = get_ffmpeg_info()
    if _ffmpeg_info["available"]:
        print(f"[Startup] FFmpeg ready: {_ffmpeg_info.get('version', 'unknown')}")
    else:
        print("[Startup] FFmpeg not found. Will auto-download when needed.")
except Exception:
    print("[Startup] FFmpeg check skipped")

# ── Cache cleanup at startup ──
try:
    import shutil
    from pathlib import Path

    _cleaned_total = 0
    _freed_mb = 0.0

    # 1. Footage cache: cleanup videos older than 24h
    try:
        from modules.video_cache import get_video_cache
        _vc = get_video_cache()
        _cleaned_total += _vc.cleanup_old_cache(max_age_hours=24)
    except Exception as e:
        print(f"[Startup] Footage cache cleanup error: {e}")

    # 2. Session subfolders: cleanup >24h old sessions in voice_output and video_output
    _max_age = 24 * 3600  # 24 hours in seconds
    for _dir_name in ["voice_output", "video_output"]:
        _base = Path(_dir_name)
        if not _base.exists():
            continue
        for _sub in _base.iterdir():
            if not _sub.is_dir():
                continue
            try:
                _age = time.time() - _sub.stat().st_mtime
                if _age > _max_age:
                    _size = sum(f.stat().st_size for f in _sub.rglob("*") if f.is_file())
                    _freed_mb += _size / 1024 / 1024
                    shutil.rmtree(_sub, ignore_errors=True)
                    _cleaned_total += 1
            except Exception:
                pass

    if _cleaned_total > 0:
        print(f"[Startup] Cache cleanup: removed {_cleaned_total} old items, freed {_freed_mb:.1f} MB")
    else:
        print("[Startup] Cache cleanup: nothing to clean")
except Exception as e:
    print(f"[Startup] Cache cleanup error: {e}")

print(f"[Startup] App ready in {time.time()-_startup_t:.1f}s")


@app.get("/")
async def root():
    return {
        "message": "Auto Media Architecture API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}


# ── WebSocket Real-Time Sync ──
from fastapi import WebSocket, WebSocketDisconnect
from modules.websocket_hub import manager as ws_manager

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time sync WebSocket — broadcasts data changes to all connected clients."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong heartbeat
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
    except Exception:
        await ws_manager.disconnect(websocket)

@app.get("/ws/status")
async def ws_status():
    """Check WebSocket connection count."""
    return {"active_connections": ws_manager.active_count}

@app.get("/api/ffmpeg/status")
async def ffmpeg_status():
    """Check ffmpeg availability and version."""
    try:
        from modules.ffmpeg_setup import get_ffmpeg_info
        return get_ffmpeg_info()
    except ImportError:
        return {"available": False, "error": "ffmpeg_setup module not found"}

@app.post("/api/ffmpeg/install")
async def ffmpeg_install():
    """Download and install ffmpeg if not available."""
    try:
        from modules.ffmpeg_setup import ensure_ffmpeg, get_ffmpeg_info
        success = ensure_ffmpeg()
        return {**get_ffmpeg_info(), "installed": success}
    except ImportError:
        return {"available": False, "error": "ffmpeg_setup module not found"}

if __name__ == "__main__":
    import uvicorn
    
    # Fix for PyInstaller: Ensure stdout/stderr exist
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')
    
    # Check if running as PyInstaller bundle
    is_frozen = getattr(sys, 'frozen', False)
    
    if is_frozen:
        # Production mode (PyInstaller bundle)
        # Use simplified logging config that doesn't rely on terminal
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            log_level="error",  # Minimal logging
            access_log=False    # Disable access logs
        )
    else:
        # Development mode
        uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
