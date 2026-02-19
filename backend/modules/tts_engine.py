"""
TTS Engine Module — Text-to-Speech generation

Supports:
1. EdgeTTS (Quick Voice) — Microsoft Edge neural voices, free, fast
2. XTTS-v2 (Clone Voice) — Voice cloning with reference audio (optional install)
"""

import os
import asyncio
import edge_tts
from typing import Optional

# Directory for generated audio files
VOICE_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voice_output")
os.makedirs(VOICE_OUTPUT_DIR, exist_ok=True)

# Reference audio directory for voice cloning
REFERENCE_AUDIO_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "voice_references")
os.makedirs(REFERENCE_AUDIO_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# AVAILABLE VOICES — Organized by language
# ═══════════════════════════════════════════════════════════════════════════════

EDGE_VOICES = {
    "vi": {
        "label": "Tiếng Việt",
        "voices": [
            {"id": "vi-VN-HoaiMyNeural", "name": "Hoài My", "gender": "female", "accent": "Bắc"},
            {"id": "vi-VN-NamMinhNeural", "name": "Nam Minh", "gender": "male", "accent": "Bắc"},
        ]
    },
    "en": {
        "label": "English",
        "voices": [
            {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "female", "accent": "US"},
            {"id": "en-US-GuyNeural", "name": "Guy", "gender": "male", "accent": "US"},
            {"id": "en-US-AriaNeural", "name": "Aria", "gender": "female", "accent": "US"},
            {"id": "en-US-DavisNeural", "name": "Davis", "gender": "male", "accent": "US"},
            {"id": "en-GB-SoniaNeural", "name": "Sonia", "gender": "female", "accent": "UK"},
            {"id": "en-GB-RyanNeural", "name": "Ryan", "gender": "male", "accent": "UK"},
            {"id": "en-AU-NatashaNeural", "name": "Natasha", "gender": "female", "accent": "AU"},
        ]
    },
    "ja": {
        "label": "日本語",
        "voices": [
            {"id": "ja-JP-NanamiNeural", "name": "Nanami", "gender": "female", "accent": "JP"},
            {"id": "ja-JP-KeitaNeural", "name": "Keita", "gender": "male", "accent": "JP"},
        ]
    },
    "ko": {
        "label": "한국어",
        "voices": [
            {"id": "ko-KR-SunHiNeural", "name": "Sun-Hi", "gender": "female", "accent": "KR"},
            {"id": "ko-KR-InJoonNeural", "name": "InJoon", "gender": "male", "accent": "KR"},
        ]
    },
    "zh": {
        "label": "中文",
        "voices": [
            {"id": "zh-CN-XiaoxiaoNeural", "name": "Xiaoxiao", "gender": "female", "accent": "CN"},
            {"id": "zh-CN-YunxiNeural", "name": "Yunxi", "gender": "male", "accent": "CN"},
            {"id": "zh-TW-HsiaoChenNeural", "name": "HsiaoChen", "gender": "female", "accent": "TW"},
        ]
    },
    "fr": {
        "label": "Français",
        "voices": [
            {"id": "fr-FR-DeniseNeural", "name": "Denise", "gender": "female", "accent": "FR"},
            {"id": "fr-FR-HenriNeural", "name": "Henri", "gender": "male", "accent": "FR"},
        ]
    },
    "de": {
        "label": "Deutsch",
        "voices": [
            {"id": "de-DE-KatjaNeural", "name": "Katja", "gender": "female", "accent": "DE"},
            {"id": "de-DE-ConradNeural", "name": "Conrad", "gender": "male", "accent": "DE"},
        ]
    },
    "es": {
        "label": "Español",
        "voices": [
            {"id": "es-ES-ElviraNeural", "name": "Elvira", "gender": "female", "accent": "ES"},
            {"id": "es-ES-AlvaroNeural", "name": "Alvaro", "gender": "male", "accent": "ES"},
        ]
    },
    "pt": {
        "label": "Português",
        "voices": [
            {"id": "pt-BR-FranciscaNeural", "name": "Francisca", "gender": "female", "accent": "BR"},
            {"id": "pt-BR-AntonioNeural", "name": "Antonio", "gender": "male", "accent": "BR"},
        ]
    },
    "ru": {
        "label": "Русский",
        "voices": [
            {"id": "ru-RU-SvetlanaNeural", "name": "Svetlana", "gender": "female", "accent": "RU"},
            {"id": "ru-RU-DmitryNeural", "name": "Dmitry", "gender": "male", "accent": "RU"},
        ]
    },
    "th": {
        "label": "ไทย",
        "voices": [
            {"id": "th-TH-PremwadeeNeural", "name": "Premwadee", "gender": "female", "accent": "TH"},
            {"id": "th-TH-NiwatNeural", "name": "Niwat", "gender": "male", "accent": "TH"},
        ]
    },
}


def get_all_voices():
    """Return all available voices organized by language."""
    return EDGE_VOICES


def get_voice_list_flat():
    """Return flat list of all voices for API response."""
    result = []
    for lang_code, lang_data in EDGE_VOICES.items():
        for voice in lang_data["voices"]:
            result.append({
                **voice,
                "language": lang_code,
                "language_label": lang_data["label"],
            })
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE TTS ENGINE — Quick Voice Generation
# ═══════════════════════════════════════════════════════════════════════════════

async def generate_edge_tts(
    text: str,
    voice: str = "vi-VN-HoaiMyNeural",
    speed: float = 1.0,
    output_filename: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> str:
    """
    Generate speech using Microsoft Edge TTS.
    
    Args:
        text: Text to convert to speech
        voice: Edge voice ID (e.g., 'vi-VN-HoaiMyNeural')
        speed: Speech speed multiplier (0.5 - 2.0)
        output_filename: Optional custom filename (without extension)
        output_dir: Optional output directory (default: VOICE_OUTPUT_DIR)
    
    Returns:
        Path to the generated audio file
    """
    if not output_filename:
        import time
        output_filename = f"voice_{int(time.time() * 1000)}"
    
    target_dir = output_dir or VOICE_OUTPUT_DIR
    os.makedirs(target_dir, exist_ok=True)
    output_path = os.path.join(target_dir, f"{output_filename}.mp3")
    
    # Build rate string: +0% is normal, +50% is 1.5x, -50% is 0.5x
    rate_percent = int((speed - 1.0) * 100)
    rate_str = f"{rate_percent:+d}%"
    
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    await communicate.save(output_path)
    
    print(f"[EdgeTTS] Generated: {output_path} ({len(text)} chars, voice={voice}, rate={rate_str})")
    return output_path


async def generate_batch_edge_tts(
    scenes: list,
    voice: str = "vi-VN-HoaiMyNeural",
    speed: float = 1.0,
    progress_callback=None,
    output_dir: Optional[str] = None,
) -> list:
    """
    Generate speech for multiple scenes.
    
    Args:
        scenes: List of {scene_id, content, voiceExport}
        voice: Edge voice ID
        speed: Speech speed
        progress_callback: Optional callback(current, total, scene_id)
        output_dir: Optional output directory for session isolation
    
    Returns:
        List of {scene_id, filename, path, success, error}
    """
    results = []
    export_scenes = [s for s in scenes if s.get("voiceExport", True)]
    total = len(export_scenes)
    
    for i, scene in enumerate(export_scenes):
        scene_id = scene["scene_id"]
        content = scene["content"]
        filename = f"scene_{scene_id:03d}"
        
        try:
            path = await generate_edge_tts(
                text=content,
                voice=voice,
                speed=speed,
                output_filename=filename,
                output_dir=output_dir,
            )
            results.append({
                "scene_id": scene_id,
                "filename": f"{filename}.mp3",
                "path": path,
                "success": True,
                "error": None,
            })
        except Exception as e:
            print(f"[EdgeTTS] Error scene {scene_id}: {e}")
            results.append({
                "scene_id": scene_id,
                "filename": None,
                "path": None,
                "success": False,
                "error": str(e),
            })
        
        if progress_callback:
            progress_callback(i + 1, total, scene_id)
    
    return results
