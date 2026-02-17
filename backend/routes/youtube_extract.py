"""
YouTube Extract API Routes

Extract metadata (title, description, thumbnail) and transcript
from a YouTube video URL using yt-dlp + youtube-transcript-api.
"""

import re
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

router = APIRouter()


# ── Thumbnail Proxy (avoids CORS) ────────────────────────────────────────────

@router.get("/thumbnail-proxy")
def proxy_thumbnail(url: str):
    """Proxy a YouTube thumbnail URL to avoid browser CORS restrictions."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
            content_type = resp.headers.get('Content-Type', 'image/jpeg')
            return Response(content=data, media_type=content_type)
    except Exception:
        return Response(content=b'', status_code=404)


# ── Request / Response Models ─────────────────────────────────────────────────

class YouTubeExtractRequest(BaseModel):
    url: str


class YouTubeExtractResponse(BaseModel):
    success: bool
    video_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    transcript: Optional[str] = None
    transcript_segments: Optional[list] = None
    has_transcript: bool = False
    channel_name: Optional[str] = None
    error: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:v=|/v/)([a-zA-Z0-9_-]{11})',
        r'(?:youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'(?:shorts/)([a-zA-Z0-9_-]{11})',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.post("/extract", response_model=YouTubeExtractResponse)
def extract_youtube_data(request: YouTubeExtractRequest):
    """
    Extract title, description, thumbnail, and transcript from a YouTube URL.
    Uses yt-dlp for metadata and youtube-transcript-api for captions.
    """
    url = request.url.strip()
    if not url:
        return YouTubeExtractResponse(success=False, error="URL is required")

    video_id = _extract_video_id(url)
    if not video_id:
        return YouTubeExtractResponse(success=False, error="Invalid YouTube URL")

    title = None
    description = None
    thumbnail_url = None
    channel_name = None
    transcript_text = None
    transcript_segments = None
    has_transcript = False

    # ── Step 1: Extract metadata with yt-dlp ──────────────────────────────
    try:
        import yt_dlp

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'no_check_certificates': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title')
            description = info.get('description', '')
            channel_name = info.get('channel') or info.get('uploader')

            # Get best thumbnail
            thumbnail_url = info.get('thumbnail')
            if not thumbnail_url:
                thumbnails = info.get('thumbnails', [])
                if thumbnails:
                    # Pick highest resolution
                    best = max(thumbnails, key=lambda t: t.get('height', 0) * t.get('width', 0))
                    thumbnail_url = best.get('url')

            # Fallback thumbnail
            if not thumbnail_url:
                thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

    except Exception as e:
        print(f"[YouTube] yt-dlp metadata error: {e}")
        # Fallback: use basic thumbnail URL
        thumbnail_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

    # ── Step 2: Extract transcript ─────────────────────────────────────────
    # Method A: youtube-transcript-api v1.x (instance-based API)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        ytt_api = YouTubeTranscriptApi()
        fetched = None

        # Try preferred languages first
        for langs in [['vi'], ['en'], ['vi', 'en']]:
            try:
                fetched = ytt_api.fetch(video_id, languages=langs)
                break
            except Exception:
                continue

        # Fallback: any available transcript
        if not fetched:
            try:
                fetched = ytt_api.fetch(video_id)
            except Exception:
                pass

        if fetched:
            has_transcript = True
            snippets = list(fetched)
            transcript_segments = [
                {
                    'text': s.text,
                    'start': s.start,
                    'duration': s.duration
                }
                for s in snippets
            ]
            transcript_text = ' '.join(s.text for s in snippets)
            print(f"[YouTube] Transcript via youtube-transcript-api: {len(snippets)} segments, {len(transcript_text)} chars")

    except Exception as e:
        print(f"[YouTube] youtube-transcript-api error: {e}")

    # Method B fallback: yt-dlp automatic_captions (auto-generated subs)
    if not has_transcript:
        try:
            import yt_dlp
            import json
            import tempfile
            import os

            ydl_opts_sub = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writeautomaticsub': True,
                'writesubtitles': True,
                'subtitleslangs': ['vi', 'en'],
                'subtitlesformat': 'json3',
                'no_check_certificates': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts_sub) as ydl:
                info_sub = ydl.extract_info(url, download=False)
                auto_caps = info_sub.get('automatic_captions', {})
                manual_subs = info_sub.get('subtitles', {})

                # Prefer manual subs, then auto captions
                all_subs = {**auto_caps, **manual_subs}

                sub_data = None
                for lang in ['vi', 'en']:
                    if lang in all_subs:
                        formats = all_subs[lang]
                        # Find json3 format
                        for fmt in formats:
                            if fmt.get('ext') == 'json3':
                                sub_url = fmt.get('url')
                                if sub_url:
                                    import urllib.request
                                    req = urllib.request.Request(sub_url, headers={'User-Agent': 'Mozilla/5.0'})
                                    with urllib.request.urlopen(req, timeout=15) as response:
                                        sub_data = json.loads(response.read().decode('utf-8'))
                                    break
                        if sub_data:
                            break

                if sub_data and 'events' in sub_data:
                    events = sub_data['events']
                    segments = []
                    for ev in events:
                        segs = ev.get('segs', [])
                        text_parts = [s.get('utf8', '') for s in segs if s.get('utf8', '').strip()]
                        if text_parts:
                            text = ''.join(text_parts).strip()
                            if text and text != '\n':
                                segments.append({
                                    'text': text,
                                    'start': ev.get('tStartMs', 0) / 1000.0,
                                    'duration': ev.get('dDurationMs', 0) / 1000.0,
                                })

                    if segments:
                        has_transcript = True
                        transcript_segments = segments
                        transcript_text = ' '.join(s['text'] for s in segments)
                        print(f"[YouTube] Transcript via yt-dlp auto-captions: {len(segments)} segments, {len(transcript_text)} chars")

        except Exception as e:
            print(f"[YouTube] yt-dlp auto-caption fallback error: {e}")

    return YouTubeExtractResponse(
        success=True,
        video_id=video_id,
        title=title,
        description=description,
        thumbnail_url=thumbnail_url,
        transcript=transcript_text,
        transcript_segments=transcript_segments,
        has_transcript=has_transcript,
        channel_name=channel_name,
    )
