"""
Footage Vision — AI-powered footage ranking with dual strategy.

Strategy 1 (Gemini native): Upload full video → Gemini analyzes entire video
Strategy 2 (OpenAI proxy):  Download video → ffmpeg keyframes → send images

Auto-detects which strategy to use based on configured AI providers.
"""

import asyncio
import base64
import concurrent.futures
import json
import os
import re as re_mod
import subprocess
import tempfile
import shutil
from typing import Optional

import httpx

from .logging_config import get_automation_logger

logger = get_automation_logger()

# Maximum videos to analyze per scene
MAX_VIDEOS = 6
# Number of keyframes to extract per video (proxy strategy)
FRAMES_PER_VIDEO = 3


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED: Video download & ffmpeg utilities
# ═══════════════════════════════════════════════════════════════════════════════

def _find_ffmpeg() -> Optional[str]:
    """Find ffmpeg executable (bundled first, then system PATH)."""
    try:
        from modules.ffmpeg_setup import get_ffmpeg_path
        return get_ffmpeg_path()
    except (ImportError, Exception):
        pass

    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        if result.returncode == 0:
            return "ffmpeg"
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    for path in [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\tools\ffmpeg\bin\ffmpeg.exe",
    ]:
        if os.path.exists(path):
            return path

    return None


_ffmpeg_path: Optional[str] = None


def _get_ffmpeg() -> Optional[str]:
    """Get cached ffmpeg path."""
    global _ffmpeg_path
    if _ffmpeg_path is None:
        _ffmpeg_path = _find_ffmpeg()
        if _ffmpeg_path:
            logger.info(f"[VisionRank] ffmpeg found: {_ffmpeg_path}")
        else:
            logger.warning("[VisionRank] ffmpeg not found")
    return _ffmpeg_path


async def _download_video(url: str, timeout: float = 30.0) -> Optional[str]:
    """Download video to temp file. Returns path or None."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None

            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            tmp.write(resp.content)
            tmp.close()

            mb = len(resp.content) / 1024 / 1024
            logger.debug(f"[VisionRank] Downloaded: {mb:.1f} MB -> {tmp.name}")
            return tmp.name
    except Exception as e:
        logger.warning(f"[VisionRank] Download failed: {e}")
        return None


def _get_video_duration(video_path: str) -> float:
    """Get video duration using ffprobe."""
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        return 0.0

    ffprobe = ffmpeg.replace("ffmpeg", "ffprobe")
    if not os.path.exists(ffprobe) and ffprobe != "ffprobe":
        ffprobe = "ffprobe"

    try:
        cmd = [ffprobe, "-v", "quiet", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass

    return 0.0


def _extract_keyframes(video_path: str, num_frames: int = 3) -> list[str]:
    """Extract evenly-spaced keyframes as base64 data URIs."""
    ffmpeg = _get_ffmpeg()
    if not ffmpeg:
        return []

    frames = []
    tmp_dir = tempfile.mkdtemp(prefix="visionrank_")

    try:
        duration = _get_video_duration(video_path)
        if duration <= 0:
            duration = 10.0

        start = duration * 0.1
        end = duration * 0.9
        interval = (end - start) / max(num_frames - 1, 1) if num_frames > 1 else 0

        for i in range(num_frames):
            timestamp = start + (interval * i)
            output_path = os.path.join(tmp_dir, f"frame_{i}.jpg")

            cmd = [
                ffmpeg, "-ss", f"{timestamp:.2f}", "-i", video_path,
                "-vframes", "1", "-q:v", "8", "-vf", "scale=512:-1",
                "-y", output_path,
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, timeout=15)
                if result.returncode == 0 and os.path.exists(output_path):
                    with open(output_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        frames.append(f"data:image/jpeg;base64,{b64}")
            except Exception as e:
                logger.warning(f"[VisionRank] Frame extraction error: {e}")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return frames


def _cleanup_temps(paths: list[str]):
    """Remove temp files."""
    for path in paths:
        try:
            if path and os.path.exists(path):
                os.unlink(path)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def _build_gemini_video_prompt(
    scene_text: str,
    scene_keywords: list[str],
    full_script: str,
    video_index: int,
    total_videos: int,
) -> str:
    """Prompt for Gemini native video analysis (one video at a time)."""
    script_ctx = full_script[:1500] if full_script else ""

    return f"""You are a professional video editor evaluating stock footage for a scene.

SCRIPT CONTEXT:
{script_ctx}

CURRENT SCENE voiceover: "{scene_text}"
SCENE KEYWORDS: {', '.join(scene_keywords) if scene_keywords else 'N/A'}

This is video candidate {video_index} of {total_videos}. Watch the ENTIRE video carefully.

Rate this video from 0-100 based on:
1. VISUAL RELEVANCE (40%) — Does the content match the scene topic?
2. MOTION & ENERGY (20%) — Is the pacing appropriate for the voiceover?
3. EMOTIONAL TONE (20%) — Does it evoke the right feeling?
4. PRODUCTION QUALITY (20%) — Is it well-shot and professional?

Return ONLY valid JSON:
{{"score": <0-100>, "reason": "<brief explanation>"}}"""


def _build_proxy_keyframes_prompt(
    scene_text: str,
    scene_keywords: list[str],
    full_script: str,
    video_count: int,
    frames_per_video: int,
) -> str:
    """Prompt for proxy/OpenAI keyframe-based ranking."""
    script_ctx = full_script[:1500] if full_script else ""

    return f"""You are a professional video editor selecting the BEST stock footage for a scene.

SCRIPT CONTEXT:
{script_ctx}

CURRENT SCENE voiceover: "{scene_text}"
SCENE KEYWORDS: {', '.join(scene_keywords) if scene_keywords else 'N/A'}

I'm showing you {frames_per_video} keyframes from each of {video_count} different stock videos.
The frames are organized as: Video 1 ({frames_per_video} frames), Video 2 ({frames_per_video} frames), etc.

RANK these videos from BEST to WORST match for this scene based on:
1. VISUAL RELEVANCE — Does the footage content match the scene's topic?
2. MOTION & ENERGY — Do the frames suggest appropriate movement/pacing?
3. EMOTIONAL TONE — Does it evoke the right feeling?
4. PRODUCTION QUALITY — Is the footage well-shot and professional?

Return ONLY valid JSON, no other text:
{{"ranking": [<video_numbers_best_to_worst>], "reason": "<brief explanation>"}}

Example: {{"ranking": [3, 1, 5, 2, 4], "reason": "Video 3 shows dynamic scenes matching the theme"}}"""


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY 1: GEMINI NATIVE — Upload full videos for analysis
# ═══════════════════════════════════════════════════════════════════════════════

async def _rank_with_gemini_video(
    candidates: list,
    scene_text: str,
    scene_keywords: list[str],
    full_script: str,
    gemini_client,
) -> list[tuple[int, float, str]]:
    """
    Analyze each video with Gemini native video understanding.
    Returns list of (candidate_idx, score, reason) sorted by score desc.
    """
    loop = asyncio.get_event_loop()
    scored: list[tuple[int, float, str]] = []
    temp_files: list[str] = []

    # Download all videos first
    download_tasks = []
    for r in candidates:
        url = getattr(r, 'preview_url', None) or getattr(r, 'download_url', None)
        download_tasks.append(_download_video(url) if url else _async_none())

    video_paths = await asyncio.gather(*download_tasks, return_exceptions=True)

    # Analyze each video with Gemini (sequentially — Gemini rate limits)
    for idx, path_result in enumerate(video_paths):
        if not isinstance(path_result, str) or not path_result or not os.path.exists(path_result):
            scored.append((idx, 0.0, "download failed"))
            continue

        temp_files.append(path_result)

        prompt = _build_gemini_video_prompt(
            scene_text=scene_text,
            scene_keywords=scene_keywords,
            full_script=full_script,
            video_index=idx + 1,
            total_videos=len(candidates),
        )

        try:
            def call_gemini(p=prompt, vp=path_result):
                return gemini_client.generate_with_video(p, vp, temperature=0.2)

            with concurrent.futures.ThreadPoolExecutor() as pool:
                response_text = await loop.run_in_executor(pool, call_gemini)

            logger.info(f"[VisionRank:Gemini] Video {idx + 1}: {response_text[:200]}")

            json_match = re_mod.search(r'\{[^{}]*\}', response_text, re_mod.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get("score", 0))
                reason = data.get("reason", "")
                scored.append((idx, score, reason))
            else:
                scored.append((idx, 50.0, "could not parse"))

        except Exception as e:
            logger.warning(f"[VisionRank:Gemini] Video {idx + 1} failed: {e}")
            scored.append((idx, 0.0, str(e)))

    # Cleanup
    _cleanup_temps(temp_files)

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY 2: PROXY KEYFRAMES — Extract frames, send as images
# ═══════════════════════════════════════════════════════════════════════════════

async def _rank_with_proxy_keyframes(
    candidates: list,
    scene_text: str,
    scene_keywords: list[str],
    full_script: str,
    openai_client,
) -> list[tuple[int, float, str]]:
    """
    Download videos, extract keyframes, send to AI for ranking.
    Returns list of (candidate_idx, score, reason) sorted by score desc.
    """
    loop = asyncio.get_event_loop()

    # Download videos concurrently
    download_tasks = []
    for r in candidates:
        url = getattr(r, 'preview_url', None) or getattr(r, 'download_url', None)
        download_tasks.append(_download_video(url) if url else _async_none())

    video_paths = await asyncio.gather(*download_tasks, return_exceptions=True)

    # Extract keyframes
    all_frames: list[tuple[int, list[str]]] = []
    temp_files: list[str] = []

    for idx, path_result in enumerate(video_paths):
        if isinstance(path_result, str) and path_result and os.path.exists(path_result):
            temp_files.append(path_result)
            frames = _extract_keyframes(path_result, FRAMES_PER_VIDEO)
            if frames:
                all_frames.append((idx, frames))

    _cleanup_temps(temp_files)

    if len(all_frames) < 2:
        logger.warning("[VisionRank:Proxy] Too few videos with frames")
        return [(i, 0.0, "") for i in range(len(candidates))]

    logger.info(f"[VisionRank:Proxy] Extracted frames from {len(all_frames)}/{len(candidates)} videos")

    # Build prompt + flatten frames
    prompt = _build_proxy_keyframes_prompt(
        scene_text=scene_text,
        scene_keywords=scene_keywords,
        full_script=full_script,
        video_count=len(all_frames),
        frames_per_video=FRAMES_PER_VIDEO,
    )

    prompt_to_idx: dict[int, int] = {}
    image_data_uris: list[str] = []
    for pos, (orig_idx, frames) in enumerate(all_frames):
        prompt_to_idx[pos + 1] = orig_idx
        image_data_uris.extend(frames)

    logger.info(f"[VisionRank:Proxy] Sending {len(image_data_uris)} frames to AI...")

    try:
        def call_vision():
            return openai_client.generate_with_images(
                prompt=prompt, image_urls=image_data_uris,
                temperature=0.2, max_tokens=500,
            )

        with concurrent.futures.ThreadPoolExecutor() as pool:
            response_text = await loop.run_in_executor(pool, call_vision)

        logger.info(f"[VisionRank:Proxy] AI response: {response_text[:300]}")

        json_match = re_mod.search(r'\{[^{}]*\}', response_text, re_mod.DOTALL)
        if not json_match:
            return [(i, 0.0, "") for i in range(len(candidates))]

        data = json.loads(json_match.group())
        ranking = data.get("ranking", [])
        reason = data.get("reason", "")

        # Convert ranking to scored format
        scored = []
        for rank_pos, video_num in enumerate(ranking):
            if isinstance(video_num, int) and video_num in prompt_to_idx:
                orig_idx = prompt_to_idx[video_num]
                score = 100.0 - (rank_pos * (100.0 / max(len(ranking), 1)))
                scored.append((orig_idx, score, reason if rank_pos == 0 else ""))

        # Add unranked videos
        ranked_indices = {s[0] for s in scored}
        for idx in range(len(candidates)):
            if idx not in ranked_indices:
                scored.append((idx, 0.0, ""))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    except Exception as e:
        logger.error(f"[VisionRank:Proxy] Failed: {e}")
        return [(i, 0.0, "") for i in range(len(candidates))]


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — Auto-detect strategy
# ═══════════════════════════════════════════════════════════════════════════════

async def _async_none():
    """Helper coroutine that returns None."""
    return None


async def rank_footage_with_vision(
    results: list,
    scene_text: str,
    scene_keywords: list[str],
    full_script: str,
    ai_client=None,
    gemini_client=None,
) -> list:
    """
    Rank footage using AI Vision with auto-detected strategy.

    Priority:
      1. Gemini native (if gemini_client available) → full video analysis
      2. OpenAI proxy (if ai_client available) → keyframe extraction
      3. No AI → return original order

    Args:
        results: List of FootageResult from search
        scene_text: Scene voiceover text
        scene_keywords: Search keywords
        full_script: Complete script for context
        ai_client: OpenAIClient (proxy) with generate_with_images()
        gemini_client: GeminiAPIClient with generate_with_video()

    Returns:
        Reordered list of FootageResult, best match first
    """
    if not results:
        return results

    candidates = results[:MAX_VIDEOS]
    strategy = "none"
    scored: list[tuple[int, float, str]] = []

    # Strategy 1: Gemini native video analysis
    if gemini_client and hasattr(gemini_client, 'generate_with_video') and gemini_client.is_configured():
        strategy = "gemini_video"
        logger.info(f"[VisionRank] Strategy: GEMINI NATIVE VIDEO ({len(candidates)} videos)")
        try:
            scored = await _rank_with_gemini_video(
                candidates, scene_text, scene_keywords, full_script, gemini_client,
            )
        except Exception as e:
            logger.error(f"[VisionRank] Gemini strategy failed: {e}, trying proxy fallback")
            strategy = "none"  # Fall through to proxy

    # Strategy 2: Proxy keyframe extraction (fallback)
    if strategy == "none" and ai_client and hasattr(ai_client, 'generate_with_images'):
        strategy = "proxy_keyframes"
        logger.info(f"[VisionRank] Strategy: PROXY KEYFRAMES ({len(candidates)} videos)")
        try:
            scored = await _rank_with_proxy_keyframes(
                candidates, scene_text, scene_keywords, full_script, ai_client,
            )
        except Exception as e:
            logger.error(f"[VisionRank] Proxy strategy failed: {e}")
            return results

    # No strategy available
    if strategy == "none":
        logger.warning("[VisionRank] No AI provider available, using original order")
        return results

    # Log results
    for idx, score, reason in scored[:3]:
        r = candidates[idx]
        vid_id = getattr(r, 'video_id', '?')
        logger.info(f"[VisionRank] #{scored.index((idx, score, reason)) + 1}: video={vid_id}, score={score:.0f}, {reason[:60]}")

    # Reorder
    reordered = [candidates[idx] for idx, _, _ in scored]

    # Append unanalyzed results
    if len(results) > MAX_VIDEOS:
        reordered.extend(results[MAX_VIDEOS:])

    return reordered
