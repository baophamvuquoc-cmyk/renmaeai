"""
FFmpeg Setup — Auto-detect or download ffmpeg for the application.

On first run, if ffmpeg is not found in PATH, downloads the essentials
build (~90MB) and extracts to backend/bin/ffmpeg/.

Usage:
    from modules.ffmpeg_setup import get_ffmpeg_path, get_ffprobe_path, ensure_ffmpeg
    
    ensure_ffmpeg()  # Download if needed (call once at startup)
    ffmpeg = get_ffmpeg_path()   # Returns absolute path to ffmpeg.exe
    ffprobe = get_ffprobe_path() # Returns absolute path to ffprobe.exe
"""

import os
import sys
import platform
import subprocess
import zipfile
import shutil
from pathlib import Path
from typing import Optional


# Directory where bundled ffmpeg lives
_BACKEND_DIR = Path(__file__).parent.parent  # backend/
_BIN_DIR = _BACKEND_DIR / "bin"
_FFMPEG_DIR = _BIN_DIR / "ffmpeg"

# Download URL for Windows essentials build (~90MB)
_FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"


def _find_in_path(program: str) -> Optional[str]:
    """Find a program in system PATH."""
    try:
        search_cmd = "where" if platform.system() == "Windows" else "which"
        result = subprocess.check_output(
            [search_cmd, program],
            stderr=subprocess.DEVNULL
        ).decode().strip().split('\n')[0].strip()
        return result
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _find_bundled(program: str) -> Optional[str]:
    """Find program in our bundled bin directory."""
    if platform.system() == "Windows":
        exe = program + ".exe"
    else:
        exe = program

    # Check in bin/ffmpeg/bin/
    bundled_path = _FFMPEG_DIR / "bin" / exe
    if bundled_path.exists():
        return str(bundled_path)

    # Check in bin/ffmpeg/ directly (flat layout)
    bundled_path = _FFMPEG_DIR / exe
    if bundled_path.exists():
        return str(bundled_path)

    # Check in bin/ directly
    bundled_path = _BIN_DIR / exe
    if bundled_path.exists():
        return str(bundled_path)

    return None


def get_ffmpeg_path() -> str:
    """Get path to ffmpeg executable. Checks bundled first, then PATH."""
    # 1. Check bundled
    bundled = _find_bundled("ffmpeg")
    if bundled:
        return bundled

    # 2. Check system PATH
    system = _find_in_path("ffmpeg")
    if system:
        return system

    # 3. Fallback: just return "ffmpeg" and hope it works
    return "ffmpeg"


def get_ffprobe_path() -> str:
    """Get path to ffprobe executable. Checks bundled first, then PATH."""
    bundled = _find_bundled("ffprobe")
    if bundled:
        return bundled

    system = _find_in_path("ffprobe")
    if system:
        return system

    return "ffprobe"


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available (bundled or in PATH)."""
    ffmpeg = get_ffmpeg_path()
    try:
        result = subprocess.run(
            [ffmpeg, "-version"],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def ensure_ffmpeg() -> bool:
    """
    Ensure ffmpeg is available. If not found, download it.
    
    Returns True if ffmpeg is available after this call.
    """
    if is_ffmpeg_available():
        ffmpeg = get_ffmpeg_path()
        print(f"[FFmpeg] Found: {ffmpeg}")
        return True

    print("[FFmpeg] Not found. Downloading essentials build...")
    return _download_ffmpeg()


def _download_ffmpeg() -> bool:
    """Download and extract ffmpeg essentials build."""
    if platform.system() != "Windows":
        print("[FFmpeg] Auto-download only supported on Windows. Please install ffmpeg manually.")
        return False

    try:
        import urllib.request

        # Create directories
        _BIN_DIR.mkdir(exist_ok=True)
        _FFMPEG_DIR.mkdir(exist_ok=True)

        zip_path = _BIN_DIR / "ffmpeg_download.zip"

        print(f"[FFmpeg] Downloading from {_FFMPEG_DOWNLOAD_URL}...")
        print("[FFmpeg] This may take a few minutes (~90MB)...")

        # Download with progress
        def _report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            if total_size > 0:
                pct = min(100, int(downloaded / total_size * 100))
                mb = downloaded / (1024 * 1024)
                if pct % 10 == 0:
                    print(f"[FFmpeg] Downloading... {pct}% ({mb:.0f} MB)")

        urllib.request.urlretrieve(_FFMPEG_DOWNLOAD_URL, str(zip_path), _report_progress)

        print("[FFmpeg] Download complete. Extracting...")

        # Extract zip
        with zipfile.ZipFile(str(zip_path), 'r') as zf:
            # Find the root folder name inside the zip (e.g., "ffmpeg-8.0.1-essentials_build")
            root_names = set()
            for name in zf.namelist():
                parts = name.split('/')
                if parts[0]:
                    root_names.add(parts[0])

            zf.extractall(str(_BIN_DIR))

        # Move extracted bin/ to our ffmpeg dir
        # The zip typically contains: ffmpeg-X.X.X-essentials_build/bin/ffmpeg.exe
        for root_name in root_names:
            extracted_bin = _BIN_DIR / root_name / "bin"
            if extracted_bin.exists():
                # Copy ffmpeg.exe, ffprobe.exe, ffplay.exe to our bin/ffmpeg/bin/
                target_bin = _FFMPEG_DIR / "bin"
                target_bin.mkdir(exist_ok=True)

                for exe in ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]:
                    src = extracted_bin / exe
                    dst = target_bin / exe
                    if src.exists():
                        shutil.copy2(str(src), str(dst))
                        print(f"[FFmpeg] Installed: {dst}")

                # Clean up extracted folder
                shutil.rmtree(str(_BIN_DIR / root_name), ignore_errors=True)
                break

        # Clean up zip
        if zip_path.exists():
            os.remove(str(zip_path))

        # Verify
        if is_ffmpeg_available():
            print("[FFmpeg] Installation complete!")
            return True
        else:
            print("[FFmpeg] Installation failed - ffmpeg not working after extraction")
            return False

    except Exception as e:
        print(f"[FFmpeg] Download failed: {e}")
        # Clean up on failure
        zip_path = _BIN_DIR / "ffmpeg_download.zip"
        if zip_path.exists():
            try:
                os.remove(str(zip_path))
            except OSError:
                pass
        return False


def get_ffmpeg_info() -> dict:
    """Get info about ffmpeg installation."""
    ffmpeg = get_ffmpeg_path()
    ffprobe = get_ffprobe_path()
    available = is_ffmpeg_available()

    info = {
        "available": available,
        "ffmpeg_path": ffmpeg,
        "ffprobe_path": ffprobe,
        "bundled": bool(_find_bundled("ffmpeg")),
        "system": bool(_find_in_path("ffmpeg")),
    }

    if available:
        try:
            result = subprocess.run(
                [ffmpeg, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            first_line = result.stdout.split('\n')[0]
            info["version"] = first_line
        except Exception:
            info["version"] = "unknown"

    return info
