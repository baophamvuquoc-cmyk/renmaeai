"""
Footage API Routes - Search videos from Pexels and Pixabay
"""

import asyncio
import concurrent.futures
import json
import os
import re as re_mod
from dataclasses import asdict
from typing import Optional, Literal, List, Dict, Set

from dotenv import load_dotenv, set_key
from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from pydantic import BaseModel

from modules.footage_api import get_footage_api, reload_footage_api, get_rotated_footage_api, FootageAPI
from modules.video_cache import get_video_cache
from modules.footage_vision import rank_footage_with_vision

# AI client import (same as script_workflow)
try:
    from routes.script_workflow import get_configured_ai_client
except ImportError:
    get_configured_ai_client = None

router = APIRouter(prefix="/api/footage", tags=["footage"])


# ═══════════════════════════════════════════════════════════════════════════════
# Pydantic models
# ═══════════════════════════════════════════════════════════════════════════════

class SceneSearchItem(BaseModel):
    scene_id: int
    keyword: str = ""  # Single keyword (backward compat)
    keywords: Optional[List[str]] = None  # Multiple keywords for footage mode
    target_duration: Optional[float] = 7.0
    target_clip_duration: Optional[float] = None  # Per-clip duration for multi-keyword mode
    scene_text: Optional[str] = ""  # Voiceover text for AI Vision context


class BatchSearchRequest(BaseModel):
    scenes: List[SceneSearchItem]
    orientation: Optional[str] = "landscape"
    prefer_source: Optional[str] = None
    pexels_api_key: Optional[str] = None
    pixabay_api_key: Optional[str] = None
    use_ai_concepts: Optional[bool] = False
    full_script: Optional[str] = None  # Full script for AI Vision context
    concept_analysis: Optional[Dict] = None  # Concept analysis for thumbnail ranking


class CacheVideoRequest(BaseModel):
    download_url: str
    video_id: str
    source: str


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: pick best video for a target duration (with dedup)
# ═══════════════════════════════════════════════════════════════════════════════

def _pick_best_match(results, target_duration: float, exclude_ids: Set[str] | None = None):
    """Select the video whose duration best fits target_duration, skipping used IDs."""
    best_match = None
    best_score = float("inf")
    for r in results:
        # Dedup: skip already-used videos
        if exclude_ids and r.video_id in exclude_ids:
            continue
        diff = abs(r.duration - target_duration)
        score = diff * 0.5 if r.duration >= target_duration else diff * 2
        if score < best_score:
            best_score = score
            best_match = r
    return best_match


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: Thumbnail-based AI ranking (replaces slow AI Vision)
# ═══════════════════════════════════════════════════════════════════════════════

async def _rank_with_thumbnails(
    results: list,
    scene_text: str,
    scene_keywords: list,
    concept_analysis: Optional[Dict] = None,
    ai_client=None,
    max_thumbnails: int = 8,
) -> list:
    """
    Rank footage by analyzing thumbnail URLs with AI vision.
    Much faster than downloading full videos + extracting keyframes.
    
    Args:
        results: List of FootageResult from search
        scene_text: Scene voiceover text
        scene_keywords: Search keywords used
        concept_analysis: Concept data from /analyze-concept
        ai_client: OpenAIClient instance (must support generate_with_images)
        max_thumbnails: Max thumbnails to send for analysis (5-10)
    
    Returns:
        Reordered results list, best match first
    """
    if not ai_client or not results:
        return results

    # Take top N thumbnails
    candidates = results[:max_thumbnails]
    thumbnail_urls = [r.thumbnail_url for r in candidates if r.thumbnail_url]

    if not thumbnail_urls:
        print("[ThumbnailRank] No thumbnail URLs available, skipping ranking")
        return results

    # Build concept context for the prompt
    concept_ctx = ""
    if concept_analysis:
        parts = []
        if concept_analysis.get('theme'):
            parts.append(f"Theme: {concept_analysis['theme']}")
        if concept_analysis.get('visual_style'):
            parts.append(f"Visual Style: {concept_analysis['visual_style']}")
        if concept_analysis.get('mood'):
            parts.append(f"Mood: {concept_analysis['mood']}")
        if concept_analysis.get('footage_guidelines'):
            parts.append(f"Guidelines: {concept_analysis['footage_guidelines']}")
        if parts:
            concept_ctx = "\n\nSCRIPT CONCEPT (footage MUST match):\n" + "\n".join(parts)

    prompt = f"""You are a stock footage selection expert. I will show you {len(thumbnail_urls)} video thumbnails.
Select the BEST thumbnail that matches this scene.

SCENE TEXT: {scene_text}
SEARCH KEYWORDS: {', '.join(scene_keywords)}
{concept_ctx}

Rank ALL {len(thumbnail_urls)} thumbnails from best to worst match.
For each, provide a score (1-10) and brief reason.

Return ONLY valid JSON:
{{
  "rankings": [
    {{{{
      "index": 0,
      "score": 9,
      "reason": "Perfect match: shows..."
    }}}},
    ...
  ]
}}"""

    try:
        import concurrent.futures
        loop = asyncio.get_event_loop()

        def call_vision(p=prompt, urls=thumbnail_urls):
            return ai_client.generate_with_images(p, urls, temperature=0.2, max_tokens=1500)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            result_text = await loop.run_in_executor(pool, call_vision)

        # Parse rankings
        json_match = re_mod.search(r'\{[\s\S]*"rankings"[\s\S]*\}', result_text)
        if json_match:
            ranking_data = json.loads(json_match.group())
            rankings = ranking_data.get('rankings', [])

            # Sort by score descending
            rankings.sort(key=lambda x: x.get('score', 0), reverse=True)

            # Reorder candidates based on ranking
            reordered = []
            used_indices = set()
            for r in rankings:
                idx = r.get('index', -1)
                if 0 <= idx < len(candidates) and idx not in used_indices:
                    reordered.append(candidates[idx])
                    used_indices.add(idx)
                    score = r.get('score', 0)
                    reason = r.get('reason', '')[:60]
                    print(f"[ThumbnailRank] #{idx} score={score}: {reason}")

            # Add remaining candidates and non-analyzed results
            for i, c in enumerate(candidates):
                if i not in used_indices:
                    reordered.append(c)
            reordered.extend(results[max_thumbnails:])

            print(f"[ThumbnailRank] Ranked {len(rankings)} thumbnails, best=#{rankings[0].get('index', '?')} (score={rankings[0].get('score', '?')})")
            return reordered
        else:
            print(f"[ThumbnailRank] Could not parse AI response, using original order")
            return results

    except Exception as e:
        print(f"[ThumbnailRank] Error: {e}")
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# Helper: AI concept extraction for thematically consistent search keywords
# ═══════════════════════════════════════════════════════════════════════════════

async def _enhance_keywords_with_ai(scenes: List[SceneSearchItem]) -> Dict[int, str]:
    """
    Use AI to analyze all scene keywords together and generate enhanced,
    thematically consistent search keywords optimized for stock video search.
    Returns dict mapping scene_id -> enhanced_keyword.
    Falls back to original keywords on error.
    """
    if get_configured_ai_client is None:
        print("[AI Concepts] AI client not available, using original keywords")
        return {s.scene_id: s.keyword for s in scenes}

    try:
        ai_client = get_configured_ai_client()
        loop = asyncio.get_event_loop()

        keyword_list = "\n".join([f"  Scene {s.scene_id}: \"{s.keyword}\"" for s in scenes])

        prompt = f"""You are a stock video search expert. Analyze these scene keywords from a single video project and generate IMPROVED search keywords that:

1. Follow a CONSISTENT visual theme across all scenes
2. Are MORE SPECIFIC for finding relevant stock footage (e.g. add context like indoor/outdoor, lighting, mood)
3. Each keyword should be UNIQUE — no two scenes should return the same footage
4. Use 3-6 English words per keyword, optimized for Pexels/Pixabay search
5. Maintain the original meaning but add visual specificity

ORIGINAL KEYWORDS:
{keyword_list}

Return ONLY valid JSON, no other text:
{{{', '.join([f'"scene_{s.scene_id}": "improved keyword here"' for s in scenes])}}}"""

        def call_ai(p=prompt):
            return ai_client.generate(p, temperature=0.4)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            result_text = await loop.run_in_executor(pool, call_ai)

        # Parse JSON from AI response
        json_match = re_mod.search(r'\{[^{}]*\}', result_text, re_mod.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            enhanced = {}
            for s in scenes:
                key = f"scene_{s.scene_id}"
                enhanced[s.scene_id] = data.get(key, s.keyword)
            print(f"[AI Concepts] Enhanced {len(enhanced)} keywords")
            for sid, kw in enhanced.items():
                print(f"  Scene {sid}: {kw}")
            return enhanced
        else:
            print("[AI Concepts] Could not parse AI response, using originals")
            return {s.scene_id: s.keyword for s in scenes}

    except Exception as e:
        print(f"[AI Concepts] Error: {e}, falling back to original keywords")
        return {s.scene_id: s.keyword for s in scenes}


@router.get("/status")
async def get_status():
    """Get API configuration status for all footage sources"""
    api = get_footage_api()
    status = api.get_status()
    
    any_configured = any(s["configured"] for s in status.values())
    
    return {
        "success": True,
        "available": any_configured,
        "sources": status
    }


@router.get("/search")
async def search_footage(
    query: str = Query(..., description="Search keywords"),
    orientation: Literal['landscape', 'portrait'] = Query('landscape'),
    sources: Optional[str] = Query(None, description="Comma-separated sources: pexels,pixabay"),
    per_page: int = Query(10, ge=1, le=50),
    page: int = Query(1, ge=1)
):
    """
    Search for footage across configured sources.
    
    Returns list of videos with thumbnails, preview URLs, and metadata.
    """
    api = get_rotated_footage_api()
    
    # Parse sources
    source_list = None
    if sources:
        source_list = [s.strip().lower() for s in sources.split(",")]
        source_list = [s for s in source_list if s in ['pexels', 'pixabay']]
    
    try:
        results = await api.search(
            query=query,
            sources=source_list,
            orientation=orientation,
            per_page=per_page,
            page=page
        )
        
        return {
            "success": True,
            "query": query,
            "count": len(results),
            "results": [asdict(r) for r in results]
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.get("/search-for-scene")
async def search_for_scene(
    keyword: str = Query(..., description="Scene keyword"),
    orientation: Literal['landscape', 'portrait'] = Query('landscape'),
    target_duration: float = Query(7.0, description="Target video duration in seconds")
):
    """
    Search footage for a single scene.
    Returns the best matching video for the given keyword.
    """
    api = get_rotated_footage_api()
    
    try:
        results = await api.search(
            query=keyword,
            orientation=orientation,
            per_page=20,
            page=1
        )
        
        if not results:
            return {
                "success": True,
                "footage": None,
                "message": "No footage found"
            }
        
        best_match = _pick_best_match(results, target_duration)
        
        return {
            "success": True,
            "footage": asdict(best_match) if best_match else None
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


# ═══════════════════════════════════════════════════════════════════════════════
# BATCH SEARCH — SSE streaming
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/search-batch")
async def search_batch(req: BatchSearchRequest, request: Request):
    """
    Search footage for multiple scenes with SSE streaming progress.
    Features: auto-rotate sources, dedup, AI concept keywords.
    """

    async def event_stream():
        # Build API instance: merge per-request keys with .env fallback so both
        # sources are always available for rotation
        api: FootageAPI
        if req.pexels_api_key or req.pixabay_api_key:
            # Merge: use per-request key if provided, else fall back to .env
            api = FootageAPI(
                pexels_key=req.pexels_api_key or os.environ.get("PEXELS_API_KEY") or None,
                pixabay_key=req.pixabay_api_key or os.environ.get("PIXABAY_API_KEY") or None,
            )
        else:
            # Use key pool rotation (round-robin) if keys exist, else fallback to env
            api = get_rotated_footage_api()

        total = len(req.scenes)
        found = 0
        orientation = req.orientation or "landscape"

        # ── Determine available sources for rotation ──
        status = api.get_status()
        available_sources = [name for name, info in status.items() if info.get("configured")]
        if not available_sources:
            available_sources = ["pexels"]  # fallback
        print(f"[SearchBatch] Available sources for rotation: {available_sources}")

        # ── Dedup: track used video IDs across all scenes ──
        used_video_ids: Set[str] = set()

        # ── AI Thumbnail Ranking: detect AI client ──
        thumbnail_ai_client = None
        if get_configured_ai_client is not None:
            try:
                hybrid = get_configured_ai_client()
                if hybrid:
                    # Prefer OpenAI-compatible client (supports generate_with_images for thumbnails)
                    if hasattr(hybrid, 'openai') and hybrid.openai.is_configured():
                        thumbnail_ai_client = hybrid.openai
                        print(f"[SearchBatch] Thumbnail AI: {thumbnail_ai_client.model}")
                    elif hasattr(hybrid, 'gemini_api') and hybrid.gemini_api.is_configured():
                        # Gemini can also analyze images
                        thumbnail_ai_client = hybrid.openai if hasattr(hybrid, 'openai') else None
                        print(f"[SearchBatch] Thumbnail AI: Gemini fallback")
            except Exception as e:
                print(f"[SearchBatch] Thumbnail AI setup failed: {e}")

        # ── AI concept enhancement (optional) ──
        enhanced_keywords: Dict[int, str] = {}
        if req.use_ai_concepts:
            yield f"data: {json.dumps({'type': 'progress', 'scene_id': 0, 'message': 'Dang phan tich concept voi AI...', 'percentage': 2}, ensure_ascii=False)}\n\n"
            try:
                enhanced_keywords = await _enhance_keywords_with_ai(req.scenes)
            except Exception as e:
                print(f"[SearchBatch] AI concept error: {e}")
                enhanced_keywords = {s.scene_id: s.keyword for s in req.scenes}
        else:
            enhanced_keywords = {s.scene_id: s.keyword for s in req.scenes}

        for idx, scene in enumerate(req.scenes):
            # Check if client disconnected
            if await request.is_disconnected():
                return

            # ── Auto-rotate: pick source for this scene ──
            source_for_scene = available_sources[idx % len(available_sources)]

            pct = int(((idx + 1) / total) * 90) + 5

            # ── Multi-keyword mode (footage workflow) ──
            scene_keywords = scene.keywords if scene.keywords else None
            
            if scene_keywords and len(scene_keywords) > 0:
                # Search each keyword sequentially → collect footage_list
                footage_list = []
                clip_duration = scene.target_clip_duration or 4.0
                
                for kw_idx, kw in enumerate(scene_keywords):
                    search_keyword = enhanced_keywords.get(scene.scene_id, kw) if not scene.keywords else kw
                    
                    yield f"data: {json.dumps({'type': 'progress', 'scene_id': scene.scene_id, 'message': f'Scene #{scene.scene_id} keyword {kw_idx+1}/{len(scene_keywords)} [{source_for_scene}]: {search_keyword}', 'percentage': pct}, ensure_ascii=False)}\n\n"
                    
                    try:
                        results = await api.search(
                            query=search_keyword,
                            sources=[source_for_scene],
                            orientation=orientation,
                            per_page=20,
                            page=1,
                        )
                        
                        # ── Thumbnail AI ranking (fast, no video download) ──
                        if thumbnail_ai_client and results:
                            try:
                                yield f"data: {json.dumps({'type': 'progress', 'scene_id': scene.scene_id, 'message': f'Thumbnail AI dang chon footage tot nhat...', 'percentage': pct}, ensure_ascii=False)}\n\n"
                                results = await _rank_with_thumbnails(
                                    results=results,
                                    scene_text=scene.scene_text or kw,
                                    scene_keywords=[kw],
                                    concept_analysis=req.concept_analysis,
                                    ai_client=thumbnail_ai_client,
                                )
                            except Exception as ve:
                                print(f"[SearchBatch] Thumbnail rank error: {ve}")

                        best = _pick_best_match(results, clip_duration, used_video_ids) if results else None
                        
                        # Fallback to other sources
                        if not best and len(available_sources) > 1:
                            other_sources = [s for s in available_sources if s != source_for_scene]
                            for alt_source in other_sources:
                                alt_results = await api.search(
                                    query=search_keyword,
                                    sources=[alt_source],
                                    orientation=orientation,
                                    per_page=20,
                                    page=1,
                                )
                                best = _pick_best_match(alt_results, clip_duration, used_video_ids) if alt_results else None
                                if best:
                                    break
                        
                        # Fallback 2: simplify keyword (first 2 words only)
                        if not best:
                            simple_kw = " ".join(search_keyword.split()[:2])
                            if simple_kw != search_keyword:
                                simple_results = await api.search(
                                    query=simple_kw,
                                    sources=[source_for_scene],
                                    orientation=orientation,
                                    per_page=20,
                                    page=1,
                                )
                                best = _pick_best_match(simple_results, clip_duration, used_video_ids) if simple_results else None
                        
                        # Fallback 3: relax dedup (allow reuse if nothing unique found)
                        if not best and results:
                            best = _pick_best_match(results, clip_duration, None)
                        
                        if best:
                            footage_dict = asdict(best)
                            footage_dict["query"] = search_keyword
                            footage_dict["keyword_index"] = kw_idx
                            used_video_ids.add(best.video_id)
                            footage_list.append(footage_dict)
                        
                    except Exception as e:
                        print(f"[SearchBatch] Error scene #{scene.scene_id} kw '{search_keyword}': {e}")
                    
                    # Rotate source for next keyword
                    source_for_scene = available_sources[(idx + kw_idx + 1) % len(available_sources)]
                    await asyncio.sleep(0.3)
                
                if footage_list:
                    found += 1
                
                yield f"data: {json.dumps({'type': 'scene_result', 'scene_id': scene.scene_id, 'footage': footage_list[0] if footage_list else None, 'footage_list': footage_list, 'keyword_count': len(scene_keywords)})}\n\n"
            
            else:
                # ── Single keyword mode (original behavior) ──
                search_keyword = enhanced_keywords.get(scene.scene_id, scene.keyword)

                yield f"data: {json.dumps({'type': 'progress', 'scene_id': scene.scene_id, 'message': f'Tìm scene #{scene.scene_id} [{source_for_scene}]: {search_keyword}', 'percentage': pct}, ensure_ascii=False)}\n\n"

                try:
                    results = await api.search(
                        query=search_keyword,
                        sources=[source_for_scene],
                        orientation=orientation,
                        per_page=20,
                        page=1,
                    )

                    # ── Thumbnail AI ranking (fast, no video download) ──
                    if thumbnail_ai_client and results:
                        try:
                            yield f"data: {json.dumps({'type': 'progress', 'scene_id': scene.scene_id, 'message': 'Thumbnail AI dang chon footage tot nhat...', 'percentage': pct}, ensure_ascii=False)}\n\n"
                            results = await _rank_with_thumbnails(
                                results=results,
                                scene_text=scene.scene_text or search_keyword,
                                scene_keywords=[search_keyword],
                                concept_analysis=req.concept_analysis,
                                ai_client=thumbnail_ai_client,
                            )
                        except Exception as ve:
                            print(f"[SearchBatch] Thumbnail rank error: {ve}")

                    # Dedup: pick best match excluding already-used videos
                    best = _pick_best_match(results, scene.target_duration or 7.0, used_video_ids) if results else None

                    # If no result from rotated source, try the other source(s)
                    if not best and len(available_sources) > 1:
                        other_sources = [s for s in available_sources if s != source_for_scene]
                        for alt_source in other_sources:
                            alt_results = await api.search(
                                query=search_keyword,
                                sources=[alt_source],
                                orientation=orientation,
                                per_page=20,
                                page=1,
                            )
                            best = _pick_best_match(alt_results, scene.target_duration or 7.0, used_video_ids) if alt_results else None
                            if best:
                                break

                    # Fallback 2: simplify keyword (first 2 words)
                    if not best:
                        simple_kw = " ".join(search_keyword.split()[:2])
                        if simple_kw != search_keyword:
                            simple_results = await api.search(
                                query=simple_kw,
                                sources=[source_for_scene],
                                orientation=orientation,
                                per_page=20,
                                page=1,
                            )
                            best = _pick_best_match(simple_results, scene.target_duration or 7.0, used_video_ids) if simple_results else None

                    # Fallback 3: relax dedup (allow reuse)
                    if not best and results:
                        best = _pick_best_match(results, scene.target_duration or 7.0, None)

                    footage_dict = None
                    if best:
                        footage_dict = asdict(best)
                        footage_dict["query"] = scene.keyword
                        footage_dict["enhanced_query"] = search_keyword
                        used_video_ids.add(best.video_id)
                        found += 1

                    yield f"data: {json.dumps({'type': 'scene_result', 'scene_id': scene.scene_id, 'footage': footage_dict})}\n\n"

                except Exception as e:
                    print(f"[SearchBatch] Error scene #{scene.scene_id}: {e}")
                    yield f"data: {json.dumps({'type': 'scene_result', 'scene_id': scene.scene_id, 'footage': None})}\n\n"

            # Small delay to avoid rate limiting
            await asyncio.sleep(0.4)

        # Final result
        yield f"event: result\ndata: {json.dumps({'type': 'result', 'success': True, 'total': total, 'found': found, 'sources_used': available_sources})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO CACHE & PREVIEW
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/cache/video")
async def cache_video(req: CacheVideoRequest):
    """
    Download & cache a video, extract duration with ffprobe.
    Returns local preview URL and accurate duration.
    """
    cache = get_video_cache()

    try:
        cached_path, duration = await cache.cache_video(
            download_url=req.download_url,
            video_id=req.video_id,
            source=req.source,
        )

        if cached_path:
            preview_url = f"/api/footage/preview/{req.source}/{req.video_id}"
            return {
                "success": True,
                "cached_path": str(cached_path),
                "duration": round(duration, 1),
                "preview_url": preview_url,
            }
        else:
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": "Failed to cache video"},
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
        )


@router.get("/preview/{source}/{video_id}")
async def preview_video(source: str, video_id: str):
    """Serve a cached video file for preview playback."""
    cache = get_video_cache()
    path = cache.get_cached_video_path(video_id, source)

    if path and os.path.isfile(path):
        return FileResponse(path, media_type="video/mp4")
    else:
        return JSONResponse(
            status_code=404,
            content={"success": False, "error": "Video not cached"},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG & KEY TESTING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/config")
async def get_config():
    """
    Get currently configured footage API keys from .env.
    Returns masked keys for display and full keys for re-population.
    """
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    pixabay_key = os.environ.get("PIXABAY_API_KEY", "")
    
    return {
        "success": True,
        "pexels_key": pexels_key,
        "pixabay_key": pixabay_key,
    }


@router.post("/config")
async def update_config(
    pexels_key: Optional[str] = None,
    pixabay_key: Optional[str] = None
):
    """
    Update API keys for footage sources.
    Keys are saved to .env file.
    """
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    
    try:
        if pexels_key is not None:
            set_key(env_path, "PEXELS_API_KEY", pexels_key)
            os.environ["PEXELS_API_KEY"] = pexels_key
        
        if pixabay_key is not None:
            set_key(env_path, "PIXABAY_API_KEY", pixabay_key)
            os.environ["PIXABAY_API_KEY"] = pixabay_key
        
        # Reload API with new keys
        api = reload_footage_api()
        status = api.get_status()
        
        return {
            "success": True,
            "message": "Configuration updated",
            "sources": status
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@router.post("/test-key")
async def test_footage_key(
    source: str = Query(..., description="pexels or pixabay"),
    api_key: str = Query(..., description="API key to test")
):
    """
    Test a Pexels or Pixabay API key by making a minimal search request.
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if source == "pexels":
                # Note: /videos/search is public and doesn't validate keys!
                # Use /v1/collections which requires real authentication
                resp = await client.get(
                    "https://api.pexels.com/v1/collections",
                    params={"per_page": 1},
                    headers={"Authorization": api_key}
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Pexels API key hoạt động!"}
                elif resp.status_code == 401:
                    return JSONResponse(status_code=401, content={"success": False, "error": "API key không hợp lệ"})
                else:
                    return JSONResponse(status_code=resp.status_code, content={"success": False, "error": f"HTTP {resp.status_code}"})

            elif source == "pixabay":
                resp = await client.get(
                    "https://pixabay.com/api/videos/",
                    params={"key": api_key, "q": "nature", "per_page": 3}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if "hits" in data:
                        return {"success": True, "message": "Pixabay API key hoạt động!"}
                    else:
                        return JSONResponse(status_code=401, content={"success": False, "error": "API key không hợp lệ"})
                elif resp.status_code == 401:
                    return JSONResponse(status_code=401, content={"success": False, "error": "API key không hợp lệ"})
                else:
                    return JSONResponse(status_code=resp.status_code, content={"success": False, "error": f"HTTP {resp.status_code}"})
            else:
                return JSONResponse(status_code=400, content={"success": False, "error": "source phải là 'pexels' hoặc 'pixabay'"})
    except httpx.TimeoutException:
        return JSONResponse(status_code=408, content={"success": False, "error": "Timeout - không thể kết nối tới API"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO ASSEMBLY — Merge footage + audio → final video
# ═══════════════════════════════════════════════════════════════════════════════

class AssembleSceneItem(BaseModel):
    scene_id: int
    footage_url: Optional[str] = None  # If empty, auto-search using keyword
    audio_filename: str  # Filename in voice_output/ (e.g., "scene_001.mp3")
    keyword: Optional[str] = None  # For auto-search when footage_url is empty
    keywords: Optional[List[str]] = None  # Multi-keyword list for sub-scenes
    target_clip_duration: Optional[float] = None  # Duration per sub-clip in seconds
    subtitle_text: Optional[str] = None  # Scene text for subtitle burn
    video_id: Optional[str] = None
    source: Optional[str] = None


class AssembleRequest(BaseModel):
    scenes: List[AssembleSceneItem]
    orientation: Optional[str] = "landscape"
    transition_duration: Optional[float] = 0.5  # Crossfade seconds (0 = none)
    bgm_volume: Optional[float] = 0.15  # Background music volume (0.0-1.0)
    video_quality: Optional[str] = "720p"  # 480p / 720p / 1080p
    enable_subtitles: Optional[bool] = True  # Burn subtitles on video


@router.post("/assemble")
async def assemble_video(req: AssembleRequest, request: Request):
    """
    Assemble footage + audio for each scene, then concatenate into final video.
    
    Auto-Sync mode: If footage_url is empty but keyword is provided,
    automatically searches for the best matching footage based on audio duration.
    
    Returns SSE stream with per-scene progress.
    """
    from modules.video_assembler import VideoAssembler
    from modules.tts_engine import VOICE_OUTPUT_DIR
    from mutagen.mp3 import MP3

    def get_audio_duration(audio_path: str) -> float:
        """Get audio duration in seconds."""
        try:
            audio = MP3(audio_path)
            return audio.info.length
        except Exception:
            try:
                from moviepy import AudioFileClip
                clip = AudioFileClip(audio_path)
                dur = clip.duration
                clip.close()
                return dur
            except Exception:
                return 5.0  # Default fallback

    async def event_stream():
        cache = get_video_cache()
        assembler = VideoAssembler(output_dir="video_output")

        total = len(req.scenes)
        scene_videos = []
        used_video_ids: set[str] = set()  # Track used videos to avoid duplicates
        has_auto_search = any(not s.footage_url and s.keyword for s in req.scenes)

        if has_auto_search:
            yield f"data: {json.dumps({'type': 'progress', 'message': f'🎬 Auto-Sync: {total} scenes (tự tìm & ghép footage)', 'percentage': 1})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'progress', 'message': f'Bắt đầu ghép video cho {total} scenes...', 'percentage': 2})}\n\n"

        for idx, scene in enumerate(req.scenes):
            # Check abort
            if await request.is_disconnected():
                return

            pct_base = int((idx / total) * 85) + 5

            # ── Step 1: Get audio path & duration ──
            audio_path = os.path.join(VOICE_OUTPUT_DIR, scene.audio_filename)
            if not os.path.exists(audio_path):
                print(f"[Assemble] Audio not found: {audio_path}")
                yield f"data: {json.dumps({'type': 'progress', 'message': f'⚠️ Scene #{scene.scene_id}: Audio không tìm thấy, bỏ qua', 'percentage': pct_base, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"
                continue

            audio_duration = get_audio_duration(audio_path)

            # ── Determine keywords list for this scene ──
            scene_keywords = scene.keywords or ([scene.keyword] if scene.keyword else [])
            clip_duration = scene.target_clip_duration or audio_duration
            use_subscenes = len(scene_keywords) > 1 and clip_duration < audio_duration

            if use_subscenes:
                # ══ MULTI-KEYWORD SUB-SCENE MODE ══
                num_subs = len(scene_keywords)
                # Distribute audio duration evenly across sub-clips
                sub_durations = [round(audio_duration / num_subs, 2)] * num_subs
                # Fix rounding: adjust last sub-clip to match exact audio duration
                sub_durations[-1] = round(audio_duration - sum(sub_durations[:-1]), 2)

                yield f"data: {json.dumps({'type': 'progress', 'message': f'[{idx+1}/{total}] 🎬 Scene #{scene.scene_id}: {num_subs} sub-clips ({audio_duration:.1f}s)', 'percentage': pct_base, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"

                sub_footage_paths = []
                sub_ok = True

                for si, kw in enumerate(scene_keywords):
                    sub_label = f"{scene.scene_id}.{si+1}"
                    sub_dur = sub_durations[si]
                    pct = pct_base + int(((si + 0.5) / num_subs / total) * 85)

                    yield f"data: {json.dumps({'type': 'progress', 'message': f'[{idx+1}/{total}] 🔍 Sub-clip {sub_label}: \"{kw}\" ({sub_dur:.1f}s)...', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"

                    try:
                        footage_api = get_rotated_footage_api()
                        results = await footage_api.search(
                            query=kw,
                            orientation=req.orientation or 'landscape',
                            per_page=10,
                            min_duration=max(5, sub_dur),
                        )

                        best = footage_api.auto_select_best(
                            results=results,
                            target_duration=sub_dur,
                            used_video_ids=used_video_ids,
                        )

                        if not best:
                            print(f"[Assemble] No footage for sub-clip {sub_label} kw='{kw}'")
                            yield f"data: {json.dumps({'type': 'progress', 'message': f'⚠️ Sub-clip {sub_label}: Không tìm thấy footage', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"
                            sub_ok = False
                            break

                        used_video_ids.add(best.video_id)

                        # Download sub-clip footage
                        sub_cache_key = f"{best.source}_{best.video_id}"
                        sub_footage_path = await cache.download_video(best.download_url, sub_cache_key)
                        if not sub_footage_path:
                            print(f"[Assemble] Download failed for sub-clip {sub_label}")
                            sub_ok = False
                            break

                        sub_footage_paths.append(sub_footage_path)

                    except Exception as e:
                        print(f"[Assemble] Sub-clip {sub_label} error: {e}")
                        yield f"data: {json.dumps({'type': 'progress', 'message': f'⚠️ Sub-clip {sub_label}: {str(e)[:80]}', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"
                        sub_ok = False
                        break

                if not sub_ok or not sub_footage_paths:
                    # Fallback to single-keyword mode if any sub-clip fails
                    print(f"[Assemble] Sub-scene mode failed for scene {scene.scene_id}, trying single-keyword fallback")
                    scene_keywords = [scene_keywords[0]]
                    use_subscenes = False
                    # Fall through to single-keyword mode below

                if sub_ok and sub_footage_paths:
                    try:
                        import concurrent.futures
                        loop = asyncio.get_event_loop()

                        pct = pct_base + int((0.8 / total) * 85)
                        yield f"data: {json.dumps({'type': 'progress', 'message': f'[{idx+1}/{total}] 🎬 Đang ghép {num_subs} sub-clips cho scene #{scene.scene_id}...', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"

                        _paths = list(sub_footage_paths)
                        _durs = list(sub_durations)

                        def do_assemble_subs():
                            return assembler.assemble_subscenes(
                                footage_paths=_paths,
                                clip_durations=_durs,
                                audio_path=audio_path,
                                scene_id=scene.scene_id,
                            )

                        with concurrent.futures.ThreadPoolExecutor() as pool:
                            video_path = await loop.run_in_executor(pool, do_assemble_subs)

                        scene_videos.append({
                            "scene_id": scene.scene_id,
                            "video_path": video_path,
                        })

                        yield f"data: {json.dumps({'type': 'scene_complete', 'scene_id': scene.scene_id, 'video_path': video_path})}\n\n"
                        continue  # Scene done, move to next

                    except Exception as e:
                        print(f"[Assemble] Sub-scene assembly error scene #{scene.scene_id}: {e}")
                        yield f"data: {json.dumps({'type': 'progress', 'message': f'❌ Scene #{scene.scene_id} sub-mode: {str(e)[:100]}', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"
                        continue

            # ══ SINGLE-KEYWORD MODE (original flow + fallback) ══
            footage_url = scene.footage_url
            video_id = scene.video_id
            source = scene.source
            single_keyword = scene_keywords[0] if scene_keywords else ''

            if not footage_url and single_keyword:
                # Auto-Sync: search + auto-select
                pct = pct_base + 2
                yield f"data: {json.dumps({'type': 'progress', 'message': f'[{idx+1}/{total}] 🔍 Tìm footage cho \"{single_keyword}\" ({audio_duration:.1f}s)...', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"

                try:
                    footage_api = get_rotated_footage_api()
                    results = await footage_api.search(
                        query=single_keyword,
                        orientation=req.orientation or 'landscape',
                        per_page=10,
                        min_duration=max(5, audio_duration),
                    )

                    best = footage_api.auto_select_best(
                        results=results,
                        target_duration=audio_duration,
                        used_video_ids=used_video_ids,
                    )

                    if best:
                        footage_url = best.download_url
                        video_id = best.video_id
                        source = best.source
                        used_video_ids.add(best.video_id)
                        yield f"data: {json.dumps({'type': 'footage_found', 'scene_id': scene.scene_id, 'video_id': best.video_id, 'source': best.source, 'duration': best.duration, 'thumbnail_url': best.thumbnail_url, 'download_url': best.download_url}, ensure_ascii=False)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'message': f'⚠️ Scene #{scene.scene_id}: Không tìm thấy footage phù hợp', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"
                        continue
                except Exception as e:
                    print(f"[Assemble] Auto-search error scene #{scene.scene_id}: {e}")
                    yield f"data: {json.dumps({'type': 'progress', 'message': f'⚠️ Scene #{scene.scene_id}: Lỗi tìm footage: {str(e)[:80]}', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"
                    continue

            if not footage_url:
                yield f"data: {json.dumps({'type': 'progress', 'message': f'⚠️ Scene #{scene.scene_id}: Không có footage URL', 'percentage': pct_base, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"
                continue

            # Track used video IDs
            if video_id:
                used_video_ids.add(video_id)

            # ── Step 3: Download footage ──
            pct = pct_base + int((0.5 / total) * 85)
            yield f"data: {json.dumps({'type': 'progress', 'message': f'[{idx+1}/{total}] Đang tải footage scene #{scene.scene_id}...', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"

            try:
                cache_key = f"{source or 'url'}_{video_id or scene.scene_id}"
                footage_path = await cache.download_video(footage_url, cache_key)
                if not footage_path:
                    print(f"[Assemble] Failed to download footage for scene {scene.scene_id}")
                    yield f"data: {json.dumps({'type': 'progress', 'message': f'⚠️ Scene #{scene.scene_id}: Không tải được footage, bỏ qua', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"
                    continue

                # ── Step 4: Assemble scene ──
                pct = pct_base + int((0.8 / total) * 85)
                yield f"data: {json.dumps({'type': 'progress', 'message': f'[{idx+1}/{total}] Đang ghép scene #{scene.scene_id} ({audio_duration:.1f}s)...', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"

                import concurrent.futures
                loop = asyncio.get_event_loop()

                def do_assemble():
                    return assembler.assemble_scene(
                        footage_path=footage_path,
                        audio_path=audio_path,
                        scene_id=scene.scene_id,
                    )

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    video_path = await loop.run_in_executor(pool, do_assemble)

                scene_videos.append({
                    "scene_id": scene.scene_id,
                    "video_path": video_path,
                })

                yield f"data: {json.dumps({'type': 'scene_complete', 'scene_id': scene.scene_id, 'video_path': video_path})}\n\n"

            except Exception as e:
                print(f"[Assemble] Error scene #{scene.scene_id}: {e}")
                yield f"data: {json.dumps({'type': 'progress', 'message': f'❌ Scene #{scene.scene_id}: {str(e)[:100]}', 'percentage': pct, 'scene_id': scene.scene_id}, ensure_ascii=False)}\n\n"

        if not scene_videos:
            yield f"event: error\ndata: {json.dumps({'error': 'Không có scene nào ghép thành công'})}\n\n"
            return

        # ── Step 5: Concatenate all scenes ──
        yield f"data: {json.dumps({'type': 'progress', 'message': f'Đang nối {len(scene_videos)} scenes thành video cuối cùng...', 'percentage': 92})}\n\n"

        try:
            import concurrent.futures
            loop = asyncio.get_event_loop()

            _transition = req.transition_duration or 0.5
            _bgm_vol = req.bgm_volume or 0.15
            _quality = req.video_quality or "720p"

            def do_concat():
                return assembler.assemble_all_scenes(
                    scene_videos,
                    output_filename="final_video.mp4",
                    transition_duration=_transition,
                    bgm_volume=_bgm_vol,
                    video_quality=_quality,
                )

            with concurrent.futures.ThreadPoolExecutor() as pool:
                final_path = await loop.run_in_executor(pool, do_concat)

            file_size = os.path.getsize(final_path)

            yield f"event: result\ndata: {json.dumps({'type': 'result', 'success': True, 'final_video_path': final_path, 'scenes_assembled': len(scene_videos), 'total_scenes': total, 'file_size_mb': round(file_size / 1024 / 1024, 1)})}\n\n"

        except Exception as e:
            print(f"[Assemble] Concat error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': f'Lỗi nối video: {str(e)}'})}\n\n"

        # Cleanup temp files
        assembler.cleanup_temp_files()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/download-video/{filename}")
async def download_assembled_video(filename: str):
    """Download the assembled final video."""
    video_path = os.path.join("video_output", filename)

    if not os.path.exists(video_path):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Video '{filename}' không tìm thấy")

    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=filename,
    )

