"""
Footage API - Pexels and Pixabay API clients for stock video search
"""

import os
import httpx
from typing import Optional, Literal
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class FootageResult:
    """Unified footage result from any source"""
    video_id: str
    source: Literal['pexels', 'pixabay']
    thumbnail_url: str
    preview_url: str
    download_url: str
    width: int
    height: int
    duration: float
    title: str = ""
    tags: str = ""


class PexelsClient:
    """Pexels API client for video search"""
    
    BASE_URL = "https://api.pexels.com"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PEXELS_API_KEY", "")
        self.is_configured = bool(self.api_key and self.api_key != "your_pexels_api_key_here")
    
    async def search_videos(
        self,
        query: str,
        orientation: Literal['landscape', 'portrait'] = 'landscape',
        per_page: int = 10,
        page: int = 1
    ) -> list[FootageResult]:
        """Search for videos on Pexels"""
        if not self.is_configured:
            return []
        
        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "orientation": orientation,
            "per_page": per_page,
            "page": page
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{self.BASE_URL}/videos/search",
                    headers=headers,
                    params=params
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for video in data.get("videos", []):
                    # Get best quality video file
                    video_files = video.get("video_files", [])
                    if not video_files:
                        continue
                    
                    # Sort by quality (width), prefer HD
                    video_files_sorted = sorted(
                        video_files,
                        key=lambda x: x.get("width", 0),
                        reverse=True
                    )
                    
                    # Get HD version (around 1920px) or highest available
                    best_file = None
                    for vf in video_files_sorted:
                        if vf.get("width", 0) <= 1920:
                            best_file = vf
                            break
                    if not best_file:
                        best_file = video_files_sorted[0]
                    
                    # Get video pictures for thumbnail
                    pictures = video.get("video_pictures", [])
                    thumbnail = pictures[0]["picture"] if pictures else video.get("image", "")
                    
                    results.append(FootageResult(
                        video_id=str(video["id"]),
                        source="pexels",
                        thumbnail_url=thumbnail,
                        preview_url=best_file.get("link", ""),
                        download_url=best_file.get("link", ""),
                        width=best_file.get("width", 0),
                        height=best_file.get("height", 0),
                        duration=float(video.get("duration", 0)),
                        title=video.get("url", "").split("/")[-2].replace("-", " ").title() if video.get("url") else "",
                        tags=query
                    ))
                
                return results
                
            except Exception as e:
                print(f"[Pexels] Search error: {e}")
                return []


class PixabayClient:
    """Pixabay API client for video search"""
    
    BASE_URL = "https://pixabay.com/api/videos"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("PIXABAY_API_KEY", "")
        self.is_configured = bool(self.api_key and self.api_key != "your_pixabay_api_key_here")
    
    async def search_videos(
        self,
        query: str,
        orientation: Literal['landscape', 'portrait'] = 'landscape',
        per_page: int = 10,
        page: int = 1
    ) -> list[FootageResult]:
        """Search for videos on Pixabay"""
        if not self.is_configured:
            return []
        
        # Map orientation to Pixabay format
        orientation_map = {
            'landscape': 'horizontal',
            'portrait': 'vertical',
        }
        
        params = {
            "key": self.api_key,
            "q": query,
            "video_type": "film",
            "orientation": orientation_map.get(orientation, 'horizontal'),
            "per_page": per_page,
            "page": page,
            "safesearch": "true"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for video in data.get("hits", []):
                    videos = video.get("videos", {})
                    
                    # Prefer medium quality (around 1280px) for balance
                    video_data = videos.get("medium") or videos.get("small") or videos.get("large") or {}
                    if not video_data:
                        continue
                    
                    results.append(FootageResult(
                        video_id=str(video["id"]),
                        source="pixabay",
                        thumbnail_url=f"https://i.vimeocdn.com/video/{video.get('picture_id')}_640x360.jpg",
                        preview_url=video_data.get("url", ""),
                        download_url=video_data.get("url", ""),
                        width=video_data.get("width", 0),
                        height=video_data.get("height", 0),
                        duration=float(video.get("duration", 0)),
                        title=video.get("tags", "").split(",")[0].strip().title() if video.get("tags") else "",
                        tags=video.get("tags", query)
                    ))
                
                return results
                
            except Exception as e:
                print(f"[Pixabay] Search error: {e}")
                return []


class FootageAPI:
    """Unified API for searching footage from multiple sources"""
    
    def __init__(
        self,
        pexels_key: Optional[str] = None,
        pixabay_key: Optional[str] = None
    ):
        self.pexels = PexelsClient(pexels_key)
        self.pixabay = PixabayClient(pixabay_key)
    
    def get_status(self) -> dict:
        """Get configuration status of all sources"""
        return {
            "pexels": {
                "configured": self.pexels.is_configured,
                "name": "Pexels",
                "url": "https://www.pexels.com/api/"
            },
            "pixabay": {
                "configured": self.pixabay.is_configured,
                "name": "Pixabay",
                "url": "https://pixabay.com/api/docs/"
            }
        }
    
    async def search(
        self,
        query: str,
        sources: Optional[list[Literal['pexels', 'pixabay']]] = None,
        orientation: Literal['landscape', 'portrait'] = 'landscape',
        per_page: int = 10,
        page: int = 1,
        min_duration: float = 0,
    ) -> list[FootageResult]:
        """
        Search for videos across configured sources.
        
        Args:
            query: Search keywords
            sources: List of sources to search (default: all configured)
            orientation: Video orientation filter
            per_page: Results per page per source
            page: Page number
            min_duration: Minimum video duration in seconds (0 = no filter)
        
        Returns:
            List of FootageResult from all sources, interleaved
        """
        if sources is None:
            sources = []
            if self.pexels.is_configured:
                sources.append('pexels')
            if self.pixabay.is_configured:
                sources.append('pixabay')
        
        if not sources:
            return []
        
        all_results = []
        
        # Search each source
        if 'pexels' in sources and self.pexels.is_configured:
            pexels_results = await self.pexels.search_videos(query, orientation, per_page, page)
            all_results.extend(pexels_results)
        
        if 'pixabay' in sources and self.pixabay.is_configured:
            pixabay_results = await self.pixabay.search_videos(query, orientation, per_page, page)
            all_results.extend(pixabay_results)
        
        # Filter by minimum duration (for auto-sync: footage >= audio duration)
        if min_duration > 0:
            filtered = [r for r in all_results if r.duration >= min_duration]
            # If too few results after filtering, include shorter ones but prefer longer
            if len(filtered) < 2 and len(all_results) > 0:
                all_results.sort(key=lambda r: r.duration, reverse=True)
                filtered = all_results  # Return all sorted by duration (longest first)
            all_results = filtered
        
        # Interleave results from different sources for variety
        if len(sources) > 1:
            pexels = [r for r in all_results if r.source == 'pexels']
            pixabay = [r for r in all_results if r.source == 'pixabay']
            
            interleaved = []
            max_len = max(len(pexels), len(pixabay))
            for i in range(max_len):
                if i < len(pexels):
                    interleaved.append(pexels[i])
                if i < len(pixabay):
                    interleaved.append(pixabay[i])
            
            return interleaved
        
        return all_results

    def auto_select_best(
        self,
        results: list[FootageResult],
        target_duration: float,
        used_video_ids: set[str] | None = None,
    ) -> Optional[FootageResult]:
        """
        Auto-select the best footage from search results (VideoGen-style).
        
        Scoring:
          - Duration match (40%): prefer footage 1-2x target duration (no loop/cut)
          - Resolution (30%): prefer HD (>= 720p)
          - No duplicate (30%): avoid videos already used in other scenes
        
        Args:
            results: List of search results to score
            target_duration: Desired video duration in seconds (from audio)
            used_video_ids: Set of video IDs already used in other scenes
        
        Returns:
            Best FootageResult or None if no results
        """
        if not results:
            return None
        
        if used_video_ids is None:
            used_video_ids = set()
        
        scored = []
        for r in results:
            score = 0.0
            
            # Duration score (40%): ideal = footage between 1x and 2x target
            if target_duration > 0:
                ratio = r.duration / target_duration
                if 1.0 <= ratio <= 2.0:
                    score += 40  # Perfect: no loop needed, minimal cut
                elif 0.8 <= ratio < 1.0:
                    score += 30  # Slightly short, minor loop
                elif 2.0 < ratio <= 3.0:
                    score += 25  # A bit long, will be cut
                elif ratio > 3.0:
                    score += 15  # Too long
                else:
                    score += max(0, 20 * ratio)  # Very short, needs loop
            else:
                score += 20  # No target duration, neutral
            
            # Resolution score (30%): prefer HD
            if r.height >= 1080:
                score += 30
            elif r.height >= 720:
                score += 25
            elif r.height >= 480:
                score += 15
            else:
                score += 5
            
            # Duplicate avoidance score (30%)
            if r.video_id not in used_video_ids:
                score += 30
            else:
                score += 0  # Already used
            
            scored.append((score, r))
        
        # Sort by score descending, return best
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1]


# Singleton instance
_footage_api: Optional[FootageAPI] = None


def get_footage_api() -> FootageAPI:
    """Get or create the footage API instance"""
    global _footage_api
    if _footage_api is None:
        _footage_api = FootageAPI()
    return _footage_api


def reload_footage_api():
    """Reload the footage API (e.g., after config change)"""
    global _footage_api
    _footage_api = FootageAPI()
    return _footage_api


def get_rotated_footage_api() -> FootageAPI:
    """
    Create a FootageAPI instance using the next rotated key from the key pool.
    Each call picks the next key in round-robin order.
    Falls back to default (env-based) if no keys in pool.
    """
    try:
        from modules.footage_key_pool import get_key_pool
        pool = get_key_pool()

        pexels_key = pool.get_next_key("pexels")
        pixabay_key = pool.get_next_key("pixabay")

        # If pool has keys, use them; otherwise fall back to env
        if pexels_key or pixabay_key:
            return FootageAPI(
                pexels_key=pexels_key,
                pixabay_key=pixabay_key,
            )
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"[KeyPool] Rotation failed, using default: {e}")

    return get_footage_api()

