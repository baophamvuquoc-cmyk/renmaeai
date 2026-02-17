"""
Video Cache — Download, cache, and extract metadata from footage videos.

Features:
- Download videos from external URLs
- Extract duration using ffprobe
- Serve cached videos via API
- Automatic cleanup of old cached files
"""

import os
import subprocess
import hashlib
import json
import time
from pathlib import Path
from typing import Optional, Dict, Tuple
import aiohttp
import asyncio


class VideoCache:
    """
    Video caching service for footage preview and metadata extraction.
    
    Usage:
        cache = VideoCache()
        video_path, duration = await cache.cache_video(url, video_id, source)
        preview_url = cache.get_preview_url(video_id)
    """
    
    def __init__(self, cache_dir: str = "footage_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        
        # Metadata cache file
        self.metadata_file = self.cache_dir / "_metadata.json"
        self._metadata: Dict = {}
        self._load_metadata()
        
        # Find ffprobe (bundled first, then system)
        self.ffprobe_path = self._find_ffprobe()
        if self.ffprobe_path:
            print(f"[VideoCache] ffprobe found at: {self.ffprobe_path}")
        else:
            print("[VideoCache] ffprobe not found, duration extraction will use fallback")
    
    def _find_ffprobe(self) -> Optional[str]:
        """Find ffprobe executable (bundled first, then system PATH)."""
        # 1. Check bundled ffmpeg
        try:
            from modules.ffmpeg_setup import get_ffprobe_path
            ffprobe = get_ffprobe_path()
            result = subprocess.run(
                [ffprobe, "-version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return ffprobe
        except (ImportError, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # 2. Check system PATH
        try:
            result = subprocess.run(
                ["ffprobe", "-version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return "ffprobe"
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # 3. Check common locations on Windows
        common_paths = [
            r"C:\ffmpeg\bin\ffprobe.exe",
            r"C:\Program Files\ffmpeg\bin\ffprobe.exe",
            r"C:\tools\ffmpeg\bin\ffprobe.exe",
        ]
        for path in common_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def _load_metadata(self):
        """Load cached metadata from file."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    self._metadata = json.load(f)
            except Exception as e:
                print(f"[VideoCache] Error loading metadata: {e}")
                self._metadata = {}
    
    def _save_metadata(self):
        """Save metadata to file."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            print(f"[VideoCache] Error saving metadata: {e}")
    
    def _get_cache_key(self, video_id: str, source: str) -> str:
        """Generate a unique cache key for a video."""
        return f"{source}_{video_id}"
    
    def _get_cached_path(self, cache_key: str) -> Path:
        """Get the file path for a cached video."""
        return self.cache_dir / f"{cache_key}.mp4"
    
    def get_video_duration_ffprobe(self, filepath: str) -> float:
        """
        Extract video duration using ffprobe.
        
        Returns duration in seconds, or 0 if extraction fails.
        """
        if not self.ffprobe_path:
            return 0.0
        
        try:
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return round(duration, 1)
        except Exception as e:
            print(f"[VideoCache] ffprobe error: {e}")
        
        return 0.0
    
    def get_video_duration_moviepy(self, filepath: str) -> float:
        """Fallback: Extract duration using MoviePy."""
        try:
            from moviepy.editor import VideoFileClip
            clip = VideoFileClip(filepath)
            duration = clip.duration
            clip.close()
            return round(duration, 1)
        except Exception as e:
            print(f"[VideoCache] MoviePy error: {e}")
            return 0.0
    
    def get_video_duration(self, filepath: str) -> float:
        """Get video duration using the best available method."""
        # Try ffprobe first (faster and more reliable)
        duration = self.get_video_duration_ffprobe(filepath)
        if duration > 0:
            return duration
        
        # Fallback to MoviePy
        return self.get_video_duration_moviepy(filepath)
    
    async def download_video(self, url: str, cache_key: str) -> Optional[str]:
        """
        Download a video from URL and cache it.
        
        Returns the cached file path, or None if download fails.
        """
        cached_path = self._get_cached_path(cache_key)
        
        # Return if already cached
        if cached_path.exists():
            print(f"[VideoCache] Already cached: {cache_key}")
            return str(cached_path)
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=120)) as response:
                    if response.status != 200:
                        print(f"[VideoCache] Download failed: HTTP {response.status}")
                        return None
                    
                    # Stream to file
                    with open(cached_path, 'wb') as f:
                        async for chunk in response.content.iter_chunked(8192):
                            f.write(chunk)
                    
                    file_size = cached_path.stat().st_size
                    print(f"[VideoCache] Downloaded: {cache_key} ({file_size / 1024 / 1024:.1f} MB)")
                    return str(cached_path)
                    
        except Exception as e:
            print(f"[VideoCache] Download error: {e}")
            # Clean up partial download
            if cached_path.exists():
                try:
                    os.remove(cached_path)
                except OSError:
                    pass
            return None
    
    async def cache_video(
        self,
        download_url: str,
        video_id: str,
        source: str
    ) -> Tuple[Optional[str], float]:
        """
        Download, cache, and extract metadata from a video.
        
        Returns:
            Tuple of (cached_file_path, duration_seconds)
        """
        cache_key = self._get_cache_key(video_id, source)
        
        # Check if already in metadata cache
        if cache_key in self._metadata:
            cached_info = self._metadata[cache_key]
            cached_path = self._get_cached_path(cache_key)
            if cached_path.exists():
                return str(cached_path), cached_info.get('duration', 0)
        
        # Download the video
        cached_path = await self.download_video(download_url, cache_key)
        if not cached_path:
            return None, 0
        
        # Extract duration
        duration = self.get_video_duration(cached_path)
        
        # Save to metadata cache
        self._metadata[cache_key] = {
            'video_id': video_id,
            'source': source,
            'duration': duration,
            'cached_at': time.time(),
            'file_path': cached_path
        }
        self._save_metadata()
        
        print(f"[VideoCache] Cached {cache_key}: {duration}s")
        return cached_path, duration
    
    def get_cached_video_path(self, video_id: str, source: str) -> Optional[str]:
        """Get path to a cached video file."""
        cache_key = self._get_cache_key(video_id, source)
        cached_path = self._get_cached_path(cache_key)
        if cached_path.exists():
            return str(cached_path)
        return None
    
    def get_preview_url(self, video_id: str, source: str) -> str:
        """Get the API URL for video preview."""
        cache_key = self._get_cache_key(video_id, source)
        return f"/api/footage/preview/{cache_key}"
    
    def is_cached(self, video_id: str, source: str) -> bool:
        """Check if a video is already cached."""
        cache_key = self._get_cache_key(video_id, source)
        return self._get_cached_path(cache_key).exists()
    
    def get_cached_duration(self, video_id: str, source: str) -> float:
        """Get duration of a cached video from metadata."""
        cache_key = self._get_cache_key(video_id, source)
        if cache_key in self._metadata:
            return self._metadata[cache_key].get('duration', 0)
        return 0
    
    def cleanup_old_cache(self, max_age_hours: int = 24):
        """Remove cached videos older than max_age_hours."""
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        removed_count = 0
        
        for cache_key, info in list(self._metadata.items()):
            cached_at = info.get('cached_at', 0)
            if current_time - cached_at > max_age_seconds:
                # Remove file
                cached_path = self._get_cached_path(cache_key)
                try:
                    if cached_path.exists():
                        os.remove(cached_path)
                    del self._metadata[cache_key]
                    removed_count += 1
                except OSError as e:
                    print(f"[VideoCache] Error removing {cache_key}: {e}")
        
        if removed_count > 0:
            self._save_metadata()
            print(f"[VideoCache] Cleaned up {removed_count} old cached videos")
        
        return removed_count
    
    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache."""
        total_size = 0
        file_count = 0
        
        for f in self.cache_dir.glob("*.mp4"):
            total_size += f.stat().st_size
            file_count += 1
        
        return {
            "file_count": file_count,
            "total_size_mb": round(total_size / 1024 / 1024, 1),
            "metadata_entries": len(self._metadata),
            "cache_dir": str(self.cache_dir)
        }


# Singleton instance
_video_cache: Optional[VideoCache] = None


def get_video_cache() -> VideoCache:
    """Get or create the singleton VideoCache instance."""
    global _video_cache
    if _video_cache is None:
        _video_cache = VideoCache()
    return _video_cache
