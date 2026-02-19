"""
Script Workflow API Routes

Active Endpoints:
- StyleA Analysis (streaming + non-streaming)
- Conversation Pipeline (streaming + non-streaming)
- Style Profile Management (save/load/delete)
- Templates
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import asyncio
import json as json_module
import logging

logger = logging.getLogger("script_workflow")
from modules.script_generator import (
    list_templates,
    get_template,
    SCRIPT_TEMPLATES,
    AdvancedRemakeWorkflow,
    StyleA,
    ConversationStyleAnalyzer
)

from modules.ai_automation import HybridAIClient, AIProvider
from modules.ai_settings_db import get_settings_db
from modules.style_profiles_db import get_style_profiles_db
from modules.websocket_hub import manager as ws_manager

router = APIRouter()

# ── Unified Language Maps ─────────────────────────────────────────────────────
# English names — used in AI prompt instructions (e.g., "The script is in Vietnamese")
LANG_NAME_MAP = {
    'vi': 'Vietnamese', 'en': 'English', 'zh': 'Chinese',
    'ja': 'Japanese', 'ko': 'Korean', 'es': 'Spanish',
    'fr': 'French', 'th': 'Thai', 'de': 'German',
    'pt': 'Portuguese', 'ru': 'Russian'
}

# Native names — used when telling AI to produce output in a specific language
LANG_NATIVE_MAP = {
    'vi': 'tiếng Việt', 'en': 'English', 'zh': '中文',
    'ja': '日本語', 'ko': '한국어', 'es': 'español',
    'fr': 'français', 'th': 'ภาษาไทย', 'de': 'Deutsch',
    'pt': 'português', 'ru': 'русский'
}


def get_configured_ai_client(model: Optional[str] = None) -> HybridAIClient:
    """
    Create a HybridAIClient with proper configuration from database.
    
    Respects the active_provider setting from AI Settings UI:
    - 'openai': Uses OpenAI API key, base URL, and model
    - 'gemini_api': Uses Gemini API key
    - 'custom': Uses Custom API key/base URL/model (OpenAI-compatible)
    
    Falls back to auto-detection if no active provider is set.
    
    Args:
        model: Optional model override. If provided, uses this model instead of the one from settings.
    """
    settings_db = get_settings_db()
    all_settings = settings_db.get_all_settings()
    
    # active_provider is in app_settings table, not ai_settings
    active_provider = settings_db.get_active_provider()
    
    # Load keys based on active provider
    openai_api_key = None
    openai_base_url = None
    openai_model = None
    gemini_api_key = None
    
    if active_provider == 'custom':
        # Custom API uses OpenAI-compatible SDK, so pass as openai params
        custom_settings = all_settings.get('custom_api', {})
        openai_api_key = custom_settings.get('api_key')
        openai_base_url = custom_settings.get('base_url')
        openai_model = model or custom_settings.get('model')
    elif active_provider == 'openai':
        openai_settings = all_settings.get('openai_api', {})
        openai_api_key = openai_settings.get('api_key')
        openai_base_url = openai_settings.get('base_url')
        openai_model = model or openai_settings.get('model')
    elif active_provider == 'gemini_api':
        gemini_settings = all_settings.get('gemini_api', {})
        gemini_api_key = gemini_settings.get('api_key')
    else:
        # No active provider set — load all and let HybridAIClient auto-select
        openai_settings = all_settings.get('openai_api', {})
        openai_api_key = openai_settings.get('api_key')
        openai_base_url = openai_settings.get('base_url')
        openai_model = model or openai_settings.get('model')
        gemini_api_key = all_settings.get('gemini_api', {}).get('api_key')
    
    return HybridAIClient(
        openai_api_key=openai_api_key,
        openai_base_url=openai_base_url,
        openai_model=openai_model,
        gemini_api_key=gemini_api_key
    )



# ===== Request/Response Models =====



# StyleA - 3 Step Analysis Request/Response
class AnalyzeToStyleARequest(BaseModel):
    scripts: List[str]  # 5-20 reference scripts
    model: Optional[str] = None  # ChatGPT model to use (e.g., 'gpt-4o', 'gpt-4o-mini')
    analysis_language: str = "vi"  # Language for analysis prompts and output (vi=Vietnamese, en=English)
    output_language: str = ""  # Target output language - if set and differs from input, scripts will be translated first


class StyleAResponse(BaseModel):
    success: bool
    style_a: Optional[Dict] = None  # The synthesized StyleA profile
    individual_analyses: Optional[List[Dict]] = None  # Analysis of each script
    scripts_analyzed: int = 0
    error: Optional[str] = None



class TemplateInfo(BaseModel):
    id: str
    name: str
    description: str
    structure: List[str]


# ===== API Endpoints =====



@router.get("/templates", response_model=List[TemplateInfo])
async def get_templates():
    """
    Lấy danh sách các template có sẵn
    """
    return list_templates()


@router.get("/templates/{template_id}")
async def get_template_by_id(template_id: str):
    """
    Lấy chi tiết một template
    """
    template = get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{template_id}' không tồn tại"
        )
    
    return {
        "id": template_id,
        "name": template["name"],
        "description": template["description"],
        "structure": template["structure"],
        "style": template["style"].to_dict() if hasattr(template["style"], "to_dict") else template["style"]
    }


# ===== Style Profile Management Endpoints =====

class SaveStyleRequest(BaseModel):
    name: str
    profile: Dict[str, Any]
    description: str = ""
    source_scripts_count: int = 1


@router.post("/styles/save")
async def save_style_profile(request: SaveStyleRequest):
    """
    Lưu style profile để tái sử dụng.
    """
    if not request.name or not request.name.strip():
        raise HTTPException(status_code=400, detail="Tên style không được để trống")
    
    if not request.profile:
        raise HTTPException(status_code=400, detail="Profile data không hợp lệ")
    
    try:
        db = get_style_profiles_db()
        profile_id = db.save_profile(
            name=request.name.strip(),
            profile_data=request.profile,
            description=request.description,
            source_scripts_count=request.source_scripts_count
        )
        
        result = {
            "success": True,
            "id": profile_id,
            "message": f"Đã lưu style '{request.name}'"
        }
        asyncio.ensure_future(ws_manager.broadcast("styles_updated", {"action": "saved", "id": profile_id}))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/styles")
async def get_saved_styles():
    """
    Lấy danh sách tất cả style profiles đã lưu
    """
    try:
        db = get_style_profiles_db()
        profiles = db.get_all_profiles()
        
        return {
            "success": True,
            "profiles": profiles,
            "count": len(profiles)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/styles/{profile_id}")
async def get_style_profile(profile_id: int):
    """
    Lấy chi tiết một style profile
    """
    try:
        db = get_style_profiles_db()
        profile = db.get_profile(profile_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Style profile không tồn tại")
        
        # Increment use count
        db.increment_use_count(profile_id)
        
        return {
            "success": True,
            "profile": profile
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateStyleRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_favorite: Optional[bool] = None


@router.put("/styles/{profile_id}")
async def update_style_profile(profile_id: int, request: UpdateStyleRequest):
    """
    Cập nhật style profile
    """
    try:
        db = get_style_profiles_db()
        
        updates = {}
        if request.name is not None:
            updates['name'] = request.name
        if request.description is not None:
            updates['description'] = request.description
        if request.is_favorite is not None:
            updates['is_favorite'] = 1 if request.is_favorite else 0
        
        if not updates:
            raise HTTPException(status_code=400, detail="Không có thông tin cập nhật")
        
        success = db.update_profile(profile_id, updates)
        
        if not success:
            raise HTTPException(status_code=404, detail="Style profile không tồn tại")
        
        asyncio.ensure_future(ws_manager.broadcast("styles_updated", {"action": "updated", "id": profile_id}))
        return {
            "success": True,
            "message": "Đã cập nhật style profile"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/styles/{profile_id}")
async def delete_style_profile(profile_id: int):
    """
    Xóa style profile.
    """
    try:
        db = get_style_profiles_db()
        success = db.delete_profile(profile_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Style profile không tồn tại")
        
        asyncio.ensure_future(ws_manager.broadcast("styles_updated", {"action": "deleted", "id": profile_id}))
        return {
            "success": True,
            "message": "Đã xóa style profile"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/styles/{profile_id}/favorite")
async def toggle_style_favorite(profile_id: int):
    """
    Toggle trạng thái favorite của style profile
    """
    try:
        db = get_style_profiles_db()
        success = db.toggle_favorite(profile_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Style profile không tồn tại")
        
        asyncio.ensure_future(ws_manager.broadcast("styles_updated", {"action": "toggled_favorite", "id": profile_id}))
        return {
            "success": True,
            "message": "Đã cập nhật trạng thái yêu thích"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# ADVANCED REMAKE - 7 STEP WORKFLOW ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

# Request/Response Models for Advanced Remake



# Request model for conversation-based pipeline
class AdvancedFullPipelineConversationRequest(BaseModel):
    original_script: str
    target_word_count: int
    source_language: str = ""  # Input language (empty = auto-detect / same as output)
    language: str = "vi"
    dialect: str = "Northern Vietnamese"
    channel_name: str = ""
    country: str = "Vietnam"
    add_quiz: bool = False
    value_type: str = "sell"
    storytelling_style: str = ""  # immersive, documentary, conversational, analytical, narrative
    narrative_voice: str = ""
    custom_narrative_voice: str = ""  # custom cách xưng hô ngôi kể
    audience_address: str = ""  # cách xưng hô khán giả
    custom_audience_address: str = ""  # custom description
    style_profile: Optional[Dict[str, Any]] = None
    model: Optional[str] = None  # AI model to use (e.g., 'gpt-5.2', 'gpt-4o')
    custom_value: str = ""  # Custom value text for script generation


@router.post("/advanced-remake/full-pipeline-conversation")
async def advanced_full_pipeline_conversation(request: AdvancedFullPipelineConversationRequest):
    """
    🎯 PIPELINE MỚI: Chạy toàn bộ 7 bước trong 1 CUỘC TRÒ CHUYỆN LIÊN TỤC
    
    Ưu điểm so với full-pipeline cũ:
    - AI nhớ context xuyên suốt tất cả các bước
    - Output mạch lạc và liên kết tốt hơn
    - Giọng văn nhất quán từ đầu đến cuối
    
    Input: Original script + config
    Output: All analysis results + final coherent script
    """
    import asyncio
    
    if not request.original_script or len(request.original_script.strip()) < 50:
        raise HTTPException(status_code=400, detail="Kịch bản gốc cần ít nhất 50 ký tự")
    
    try:
        # Use selected model from request or fall back to settings
        ai_client = get_configured_ai_client(model=request.model)
        workflow = AdvancedRemakeWorkflow(ai_client)
        
        # Run the conversation-based pipeline
        results = await asyncio.to_thread(
            workflow.full_pipeline_conversation,
            original_script=request.original_script,
            target_word_count=request.target_word_count,
            source_language=request.source_language,
            language=request.language,
            dialect=request.dialect,
            channel_name=request.channel_name,
            country=request.country,
            add_quiz=request.add_quiz,
            value_type=request.value_type,
            storytelling_style=request.storytelling_style,
            narrative_voice=request.narrative_voice,
            custom_narrative_voice=request.custom_narrative_voice,
            audience_address=request.audience_address,
            custom_audience_address=request.custom_audience_address,
            style_profile=request.style_profile,
            custom_value=request.custom_value
        )
        
        # Convert dataclass results to dicts for JSON response
        response_data = {
            "success": True,
            "final_script": results.get("final_script", ""),
            "word_count": results.get("word_count", 0)
        }
        
        # Add optional results if available
        if "original_analysis" in results:
            response_data["original_analysis"] = results["original_analysis"].to_dict() if hasattr(results["original_analysis"], "to_dict") else results["original_analysis"]
        if "structure_analysis" in results:
            response_data["structure_analysis"] = results["structure_analysis"].to_dict() if hasattr(results["structure_analysis"], "to_dict") else results["structure_analysis"]
        if "outline_a" in results:
            response_data["outline_a"] = results["outline_a"].to_dict() if hasattr(results["outline_a"], "to_dict") else results["outline_a"]
        if "draft_sections" in results:
            response_data["draft_sections"] = [d.to_dict() if hasattr(d, "to_dict") else d for d in results["draft_sections"]]
        if "refined_sections" in results:
            response_data["refined_sections"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in results["refined_sections"]]
        
        return response_data
        
    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SCENE SPLITTING - Chia kịch bản thành scenes
# ═══════════════════════════════════════════════════════════════════════════════

class SplitToScenesRequest(BaseModel):
    script: str
    model: Optional[str] = None
    language: Optional[str] = None  # 'vi', 'en', etc. None = auto-detect
    split_mode: str = "voiceover"  # 'voiceover' (5-8s) or 'footage' (3-5s)


@router.post("/split-to-scenes")
async def split_script_to_scenes(request: SplitToScenesRequest):
    """
    Chia kịch bản thành các scenes.
    
    Modes:
    - 'voiceover': 5-8 giây/scene (mặc định, cho voice generation)
    - 'footage': 3-5 giây/scene (cho video footage selection)
    
    Sử dụng thuật toán chia thuần (không dùng AI) để đảm bảo:
    - 100% giữ nguyên nội dung kịch bản
    - Xử lý tức thời, không timeout
    - Không tốn token AI
    """
    if not request.script or len(request.script.strip()) < 50:
        raise HTTPException(status_code=400, detail="Kịch bản cần ít nhất 50 ký tự")

    # Validate split_mode
    split_mode = request.split_mode.lower() if request.split_mode else "voiceover"
    if split_mode not in ["voiceover", "footage"]:
        split_mode = "voiceover"

    try:
        detected_lang = request.language or _detect_language(request.script.strip())
        scenes = _split_script_algorithmically(
            request.script.strip(), 
            language=detected_lang, 
            split_mode=split_mode
        )

        if not scenes:
            raise HTTPException(status_code=500, detail="Không thể chia kịch bản. Vui lòng thử lại.")

        # Verify total word preservation
        original_words = request.script.strip().split()
        scene_words = []
        for s in scenes:
            scene_words.extend(s["content"].split())
        
        total_words = sum(s["word_count"] for s in scenes)
        est_pages = round(total_words / 250, 1)  # ~250 words per A4 page

        mode_label = "voiceover (5-8s)" if split_mode == "voiceover" else "footage (3-5s)"
        
        response_data = {
            "success": True,
            "scenes": scenes,
            "scene_count": len(scenes),
            "detected_language": detected_lang,
            "total_words": total_words,
            "est_pages": est_pages,
            "split_mode": split_mode,
        }

        if split_mode == "footage":
            # Footage mode: no est_duration, will be measured from actual audio
            logger.info(f"[SplitScenes] Mode: {mode_label} | Language: {detected_lang} | Original: {len(original_words)} words -> {len(scenes)} scenes, Preserved: {len(scene_words)} words | ~{est_pages} pages")
        else:
            est_total_duration = sum(s.get("est_duration", 0) for s in scenes)
            response_data["est_total_duration"] = round(est_total_duration, 1)
            logger.info(f"[SplitScenes] Mode: {mode_label} | Language: {detected_lang} | Original: {len(original_words)} words -> {len(scenes)} scenes, Preserved: {len(scene_words)} words | Est: {est_total_duration:.0f}s | ~{est_pages} pages")

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in split_script_to_scenes: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ── Clean Scenes Endpoint ─────────────────────────────────────────────────────
class CleanScenesRequest(BaseModel):
    scenes: List[Dict[str, Any]]
    language: Optional[str] = None


@router.post("/clean-scenes")
async def clean_scenes(request: CleanScenesRequest):
    """
    Làm sạch ký tự đặc biệt cho các scenes đã có.
    Xóa tất cả dấu ngoặc kép, ngoặc đơn, ngoặc vuông, v.v.
    """
    if not request.scenes:
        return {"success": True, "scenes": [], "cleaned_count": 0}

    # Characters to remove (same as Step 2b in split algorithm)
    # Using explicit Unicode code points to avoid encoding issues
    chars_to_remove = [
        '"', "'", '(', ')', '[', ']', '{', '}',
        '\u201C', '\u201D',  # " "
        '\u2018', '\u2019',  # ' '
        '\u00AB', '\u00BB',  # « »
        '\u2039', '\u203A',  # ‹ ›
        '\u201E', '\u201F',  # „ ‟
        '\u201A', '\u201B',  # ‚ ‛
    ]

    def clean_text(text: str) -> str:
        for char in chars_to_remove:
            text = text.replace(char, '')
        # Clean up double spaces
        import re
        text = re.sub(r' {2,}', ' ', text).strip()
        return text

    language = request.language or 'vi'
    cleaned_scenes = []
    changed_count = 0

    # Use calibrated speech rate from _get_language_params for accurate duration
    lang_params = _get_language_params(language, "voiceover")
    wps = lang_params.get('speech_rate', 2.5)

    for scene in request.scenes:
        original_content = scene.get('content', '')
        cleaned_content = clean_text(original_content)
        
        # Recount words after cleaning
        word_count = len(cleaned_content.split())
        
        est_duration = round(word_count / wps, 1)
        
        # Track if content changed
        if original_content != cleaned_content:
            changed_count += 1
        
        cleaned_scenes.append({
            **scene,
            'content': cleaned_content,
            'word_count': word_count,
            'est_duration': est_duration
        })

    total_words = sum(s['word_count'] for s in cleaned_scenes)
    est_total_duration = sum(s['est_duration'] for s in cleaned_scenes)
    est_pages = round(total_words / 250, 1)

    print(f"[CleanScenes] Cleaned {changed_count}/{len(request.scenes)} scenes | Total: {total_words} words, {est_total_duration:.0f}s")

    return {
        "success": True,
        "scenes": cleaned_scenes,
        "scene_count": len(cleaned_scenes),
        "cleaned_count": changed_count,
        "total_words": total_words,
        "est_total_duration": round(est_total_duration, 1),
        "est_pages": est_pages
    }


# ── Language Detection ────────────────────────────────────────────────────────
def _detect_language(text: str) -> str:
    """Detect language from text using character analysis."""
    # Vietnamese diacritics
    vi_chars = set('àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
                   'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ')
    
    sample = text[:1000]
    vi_count = sum(1 for c in sample if c in vi_chars)
    
    if vi_count > len(sample) * 0.02:  # >2% Vietnamese chars
        return 'vi'
    
    # Check for Japanese (hiragana/katakana)
    ja_count = sum(1 for c in sample if '\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff')
    if ja_count > len(sample) * 0.05:
        return 'ja'
    
    # Check for Korean (hangul)
    ko_count = sum(1 for c in sample if '\uac00' <= c <= '\ud7af' or '\u1100' <= c <= '\u11ff')
    if ko_count > len(sample) * 0.05:
        return 'ko'
    
    # Check for Chinese (CJK only, after filtering ja/ko)
    cjk_count = sum(1 for c in sample if '\u4e00' <= c <= '\u9fff')
    if cjk_count > len(sample) * 0.1:
        return 'zh'
    
    # Check for Thai
    th_count = sum(1 for c in sample if '\u0e00' <= c <= '\u0e7f')
    if th_count > len(sample) * 0.05:
        return 'th'
    
    # Check for Spanish/French accented chars (rough heuristic)
    es_fr_chars = set('áéíóúñüÁÉÍÓÚÑÜ¿¡àâçèêëîïôùûüÿœæÀÂÇÈÊËÎÏÔÙÛÜŸŒÆ')
    es_fr_count = sum(1 for c in sample if c in es_fr_chars)
    if es_fr_count > len(sample) * 0.01:
        # Distinguish Spanish vs French by specific chars
        if 'ñ' in sample.lower() or '¿' in sample or '¡' in sample:
            return 'es'
        if 'ç' in sample.lower() or 'œ' in sample.lower() or 'æ' in sample.lower():
            return 'fr'
    
    return 'en'


def _get_language_params(language: str, split_mode: str = "voiceover") -> dict:
    """
    Get scene splitting parameters based on language, Edge-TTS speech rate, and split mode.
    
    CALIBRATED from actual Edge-TTS voice generation data (130 Vietnamese scenes).
    Edge-TTS speaks significantly slower than natural human speech.
    
    Split Modes:
    - 'voiceover': 5-8 seconds per scene (for voice generation)
    - 'footage': 3-5 seconds per scene (for video footage selection)
    
    Calibrated Edge-TTS speech rates (words per second):
    - Vietnamese: ~2.95 w/s (measured from 130 scenes, avg 7.55s)
    - English:    ~2.8 w/s (Edge-TTS is slower)
    - Chinese:    ~3.0 chars/s
    - Japanese:   ~4.0 mora/s
    - Korean:     ~3.2 syl/s
    - Spanish:    ~4.5 syl/s
    - French:     ~4.2 syl/s
    - Thai:       ~2.8 syl/s
    
    Footage mode (3-5s): Optimized for video footage selection where each clip should
    be short enough to maintain visual interest and match the concept of each scene.
    """
    # Base speech rates (words per second) - same for both modes
    speech_rates = {
        'vi': 2.95,  # Vietnamese: measured ~2.95 w/s
        'en': 2.8,   # English: Edge-TTS is slower
        'zh': 3.0,   # Chinese: chars/s
        'ja': 4.0,   # Japanese: mora/s
        'ko': 3.2,   # Korean: syllables/s
        'es': 4.5,   # Spanish: syllables/s
        'fr': 4.2,   # French: syllables/s
        'th': 2.8,   # Thai: syllables/s
        'de': 3.5,   # German: estimated w/s
        'pt': 4.0,   # Portuguese: estimated w/s
        'ru': 3.5,   # Russian: estimated w/s
    }
    
    if split_mode == "footage":
        # Footage mode: 3-5 seconds per scene
        # Formula: min_words = 3s * speech_rate, max_words = 5s * speech_rate
        params = {
            'vi': {'min_words': 9,  'max_words': 15, 'syl_per_word': 1.0, 'speech_rate': 2.95},   # 3-5s
            'en': {'min_words': 8,  'max_words': 14, 'syl_per_word': 1.0, 'speech_rate': 2.8},    # 3-5s
            'zh': {'min_words': 9,  'max_words': 15, 'syl_per_word': 1.0, 'speech_rate': 3.0},    # 3-5s
            'ja': {'min_words': 12, 'max_words': 20, 'syl_per_word': 2.5, 'speech_rate': 4.0},    # 3-5s
            'ko': {'min_words': 10, 'max_words': 16, 'syl_per_word': 2.0, 'speech_rate': 3.2},    # 3-5s
            'es': {'min_words': 13, 'max_words': 22, 'syl_per_word': 1.9, 'speech_rate': 4.5},    # 3-5s
            'fr': {'min_words': 12, 'max_words': 21, 'syl_per_word': 1.6, 'speech_rate': 4.2},    # 3-5s
            'th': {'min_words': 8,  'max_words': 14, 'syl_per_word': 1.0, 'speech_rate': 2.8},    # 3-5s
            'de': {'min_words': 10, 'max_words': 17, 'syl_per_word': 1.5, 'speech_rate': 3.5},    # 3-5s
            'pt': {'min_words': 12, 'max_words': 20, 'syl_per_word': 1.8, 'speech_rate': 4.0},    # 3-5s
            'ru': {'min_words': 10, 'max_words': 17, 'syl_per_word': 1.5, 'speech_rate': 3.5},    # 3-5s
        }
        default = {'min_words': 9, 'max_words': 15, 'syl_per_word': 1.3, 'speech_rate': 3.0}
    else:
        # Voiceover mode: 5-8 seconds per scene (default)
        # Formula: min_words = 5s * speech_rate, max_words = 8s * speech_rate
        params = {
            'vi': {'min_words': 17, 'max_words': 27, 'syl_per_word': 1.0, 'speech_rate': 2.95},  # 5-8s
            'en': {'min_words': 14, 'max_words': 22, 'syl_per_word': 1.0, 'speech_rate': 2.8},   # 5-8s
            'zh': {'min_words': 15, 'max_words': 24, 'syl_per_word': 1.0, 'speech_rate': 3.0},   # 5-8s
            'ja': {'min_words': 20, 'max_words': 32, 'syl_per_word': 2.5, 'speech_rate': 4.0},   # 5-8s
            'ko': {'min_words': 16, 'max_words': 26, 'syl_per_word': 2.0, 'speech_rate': 3.2},   # 5-8s
            'es': {'min_words': 22, 'max_words': 36, 'syl_per_word': 1.9, 'speech_rate': 4.5},   # 5-8s
            'fr': {'min_words': 21, 'max_words': 34, 'syl_per_word': 1.6, 'speech_rate': 4.2},   # 5-8s
            'th': {'min_words': 14, 'max_words': 22, 'syl_per_word': 1.0, 'speech_rate': 2.8},   # 5-8s
            'de': {'min_words': 17, 'max_words': 28, 'syl_per_word': 1.5, 'speech_rate': 3.5},   # 5-8s
            'pt': {'min_words': 20, 'max_words': 32, 'syl_per_word': 1.8, 'speech_rate': 4.0},   # 5-8s
            'ru': {'min_words': 17, 'max_words': 28, 'syl_per_word': 1.5, 'speech_rate': 3.5},   # 5-8s
        }
        default = {'min_words': 14, 'max_words': 22, 'syl_per_word': 1.3, 'speech_rate': 3.0}
    
    return params.get(language, default)


def _estimate_duration(word_count: int, language: str) -> float:
    """Estimate Edge-TTS speech duration in seconds for a given word count."""
    p = _get_language_params(language)
    # Direct: duration = word_count / speech_rate (words per second)
    return round(word_count / p['speech_rate'], 1)


def _split_script_algorithmically(
    script: str, 
    language: str = 'vi',
    min_words: int = None, 
    max_words: int = None,
    split_mode: str = "voiceover"
) -> List[Dict]:
    """
    Chia kịch bản thành scenes dựa trên thời lượng giọng nói ước tính.
    
    Split Modes:
    - 'voiceover': 5-8 seconds per scene (default, for voice generation)
    - 'footage': 3-5 seconds per scene (for video footage selection)
    
    Chiến lược v4 (language-aware):
    1. Auto-detect language → set min/max words dựa trên speech rate
    2. Normalize whitespace (newline/tab → space)  
    3. Tách thành câu tại dấu . ! ? (giữ dấu câu)
    4. Câu dài > max_words → tách tại dấu phẩy (giữ dấu phẩy)
    5. Gom câu greedy: tích luỹ cho đến khi >= min_words, flush khi thêm câu vượt max_words
    6. Post-process: gộp các scene ngắn liền kề
    
    Nguyên tắc: KHÔNG BAO GIỜ cắt giữa câu. Cho phép ±5 từ để giữ nguyên câu.
    Đảm bảo 100% giữ nguyên mọi từ trong kịch bản gốc.
    """
    import re as re_mod

    # ── Step 0: Get language parameters ───────────────────────────────────
    lang_params = _get_language_params(language, split_mode)
    if min_words is None:
        min_words = lang_params['min_words']
    if max_words is None:
        max_words = lang_params['max_words']
    
    mode_label = "voiceover (5-8s)" if split_mode == "voiceover" else "footage (3-5s)"
    print(f"[SplitScenes] Mode: {mode_label} | Language: {language} | Target: {min_words}-{max_words} words/scene | Speech rate: {lang_params['speech_rate']} w/s")

    # ── Step 1: Normalize all whitespace ──────────────────────────────────
    text = script.strip()
    text = re_mod.sub(r'[\r\n\t]+', ' ', text)
    text = re_mod.sub(r' {2,}', ' ', text)
    text = text.strip()

    if not text:
        return []

    # ── Step 2: Split into sentences ──────────────────────────────────────
    # Split after sentence-ending punctuation (.!?) followed by whitespace
    # Keep the punctuation attached to preceding text
    parts = re_mod.split(r'(\.{2,}|[.!?])\s+', text)
    
    sentences = []
    i = 0
    while i < len(parts):
        if i + 1 < len(parts) and re_mod.match(r'^(\.{2,}|[.!?])$', parts[i + 1]):
            combined = parts[i].strip() + parts[i + 1]
            if combined.strip():
                sentences.append(combined.strip())
            i += 2
        else:
            if parts[i].strip():
                sentences.append(parts[i].strip())
            i += 1

    if not sentences:
        return []

    # ── Step 2b: Remove ALL special quote/bracket characters ───────────────
    # TTS reads these characters awkwardly; remove ALL of them early
    # This ensures clean text BEFORE any further processing
    # Using explicit Unicode code points to avoid encoding issues
    _chars_to_remove = [
        '"',        # ASCII double quote (U+0022)
        "'",        # ASCII single quote (U+0027)
        '(',        # Parentheses
        ')',
        '[',        # Square brackets
        ']',
        '{',        # Curly braces
        '}',
        '\u201C',   # Left double quotation mark "
        '\u201D',   # Right double quotation mark "
        '\u2018',   # Left single quotation mark '
        '\u2019',   # Right single quotation mark '
        '\u00AB',   # Left-pointing double angle « 
        '\u00BB',   # Right-pointing double angle »
        '\u2039',   # Single left-pointing ‹
        '\u203A',   # Single right-pointing ›
        '\u201E',   # Double low-9 quotation „
        '\u201F',   # Double high-reversed-9 ‟
        '\u201A',   # Single low-9 quotation ‚
        '\u201B',   # Single high-reversed-9 ‛
    ]

    def _clean_special(text: str) -> str:
        """Remove ALL special quote/bracket characters for TTS readability."""
        for char in _chars_to_remove:
            text = text.replace(char, '')
        # Clean up double spaces left behind
        text = re_mod.sub(r' {2,}', ' ', text).strip()
        return text

    sentences = [_clean_special(s) for s in sentences]

    # ── Step 3: Split overly long sentences at commas and conjunctions ─────
    # Vietnamese conjunctions and natural break points
    vi_conjunctions = [
        ' và ', ' nhưng ', ' hay ', ' hoặc ', ' lại ', ' rồi ', 
        ' sau đó ', ' tiếp theo ', ' nên ', ' vì ', ' bởi vì ',
        ' do đó ', ' tuy nhiên ', ' mặc dù ', ' nếu ', ' khi ',
        ' thì ', ' mà ', ' để ', ' còn ', ' cũng ', ' đã ', ' sẽ ',
        ' cái giá là ', ' theo ', ' với ', ' cho '
    ]
    en_conjunctions = [
        ' and ', ' but ', ' or ', ' then ', ' so ', ' because ',
        ' however ', ' although ', ' if ', ' when ', ' while ',
        ' that ', ' which ', ' where ', ' after ', ' before ',
        ' since ', ' for ', ' yet ', ' thus ', ' therefore '
    ]
    # CJK languages use different delimiters (no spaces around conjunctions)
    zh_conjunctions = [
        '但是', '而且', '因为', '所以', '虽然', '或者', '如果', '不过',
        '然后', '接着', '于是', '尽管', '可是', '并且', '即使', '除非'
    ]
    ja_conjunctions = [
        'しかし', 'そして', 'だから', 'それで', 'または', 'けれども',
        'ところが', 'それから', 'つまり', 'なぜなら', 'もし', 'ただし'
    ]
    ko_conjunctions = [
        '그리고', '하지만', '그래서', '또는', '그러나', '왜냐하면',
        '그런데', '따라서', '만약', '비록', '그러므로', '게다가'
    ]
    es_conjunctions = [
        ' y ', ' pero ', ' o ', ' porque ', ' sin embargo ', ' aunque ',
        ' entonces ', ' después ', ' si ', ' cuando ', ' mientras ',
        ' por lo tanto ', ' además ', ' también ', ' sino '
    ]
    fr_conjunctions = [
        ' et ', ' mais ', ' ou ', ' parce que ', ' cependant ', ' bien que ',
        ' alors ', ' ensuite ', ' si ', ' quand ', ' pendant que ',
        ' donc ', ' aussi ', ' puis ', ' pourtant '
    ]
    th_conjunctions = [
        'และ', 'แต่', 'หรือ', 'เพราะ', 'ถ้า', 'เมื่อ', 'ดังนั้น',
        'อย่างไรก็ตาม', 'แม้ว่า', 'จากนั้น', 'แล้ว', 'จึง'
    ]
    de_conjunctions = [
        ' und ', ' aber ', ' oder ', ' weil ', ' obwohl ', ' wenn ',
        ' dann ', ' deshalb ', ' jedoch ', ' trotzdem ', ' damit ',
        ' denn ', ' also ', ' sondern ', ' außerdem '
    ]
    pt_conjunctions = [
        ' e ', ' mas ', ' ou ', ' porque ', ' embora ', ' se ',
        ' então ', ' depois ', ' portanto ', ' contudo ', ' além disso ',
        ' porém ', ' quando ', ' enquanto '
    ]
    ru_conjunctions = [
        ' и ', ' но ', ' или ', ' потому что ', ' однако ', ' если ',
        ' тогда ', ' потом ', ' поэтому ', ' хотя ', ' также ',
        ' кроме того ', ' когда ', ' пока '
    ]
    
    # Map language code to conjunction list
    conjunction_map = {
        'vi': vi_conjunctions, 'en': en_conjunctions,
        'zh': zh_conjunctions, 'ja': ja_conjunctions, 'ko': ko_conjunctions,
        'es': es_conjunctions, 'fr': fr_conjunctions, 'th': th_conjunctions,
        'de': de_conjunctions, 'pt': pt_conjunctions, 'ru': ru_conjunctions
    }
    
    def _split_at_conjunctions(text: str) -> List[str]:
        """Split text at natural break points (conjunctions)."""
        conjunctions = conjunction_map.get(language, en_conjunctions)
        
        best_split = None
        best_balance = float('inf')  # Lower is better (more balanced split)
        
        for conj in conjunctions:
            if conj in text:
                idx = text.find(conj)
                if idx > 0:
                    left = text[:idx].strip()
                    right = text[idx + len(conj):].strip()
                    if left and right:
                        # Prefer splits that create more balanced parts
                        balance = abs(len(left.split()) - len(right.split()))
                        if balance < best_balance:
                            best_balance = balance
                            best_split = (left, conj.strip(), right)
        
        if best_split:
            left, conj, right = best_split
            # Keep conjunction with first part to maintain meaning
            return [left, right]
        
        return [text]
    
    def _split_long_sentence(sentence: str) -> List[str]:
        """Split sentence > max_words at commas and conjunctions."""
        words = sentence.split()
        if len(words) <= max_words:
            return [sentence]
        
        # First try: Split at commas, keeping comma with preceding part
        comma_parts = re_mod.split(r'(?<=,)\s+', sentence)
        if len(comma_parts) > 1:
            # Greedily group comma-parts into chunks ≤ max_words
            result = []
            buf = []
            buf_wc = 0
            for part in comma_parts:
                part = part.strip()
                if not part:
                    continue
                part_wc = len(part.split())
                if buf_wc + part_wc > max_words and buf:
                    result.append(' '.join(buf))
                    buf = []
                    buf_wc = 0
                buf.append(part)
                buf_wc += part_wc
            if buf:
                result.append(' '.join(buf))
        else:
            result = [sentence]
        
        # Second pass: Split any remaining long chunks at conjunctions
        final_result = []
        for chunk in result:
            chunk_wc = len(chunk.split())
            if chunk_wc > max_words:
                # Recursively split at conjunctions
                sub_parts = _split_at_conjunctions(chunk)
                for sub in sub_parts:
                    sub_wc = len(sub.split())
                    if sub_wc > max_words:
                        # Last resort: split at max_words boundary
                        sub_words = sub.split()
                        for i in range(0, len(sub_words), max_words):
                            chunk_slice = ' '.join(sub_words[i:i + max_words])
                            if chunk_slice.strip():
                                final_result.append(chunk_slice.strip())
                    else:
                        final_result.append(sub)
            else:
                final_result.append(chunk)
        
        return final_result if final_result else [sentence]

    segments = []
    for sentence in sentences:
        segments.extend(_split_long_sentence(sentence))

    # ── Step 4: Greedy grouping ───────────────────────────────────────────
    # Accumulate segments. Flush the buffer as a scene when:
    #   - buffer >= min_words AND adding next segment would exceed max_words
    # Allow tolerance of max_words+5 to keep complete sentences together.
    scenes = []
    buf_parts = []
    buf_wc = 0

    for segment in segments:
        seg_wc = len(segment.split())

        if buf_wc == 0:
            buf_parts.append(segment)
            buf_wc = seg_wc
            continue

        combined_wc = buf_wc + seg_wc

        if combined_wc <= max_words:
            # Fits within target — keep accumulating
            buf_parts.append(segment)
            buf_wc = combined_wc
        elif buf_wc >= min_words:
            # Buffer already has enough — flush it, start fresh
            scenes.append(' '.join(buf_parts))
            buf_parts = [segment]
            buf_wc = seg_wc
        elif combined_wc <= max_words + 5:
            # Slightly over but acceptable to keep sentence intact
            buf_parts.append(segment)
            buf_wc = combined_wc
        else:
            # Buffer too short to flush, but segment too big to add
            # Flush buffer anyway (under min, but better than breaking)
            scenes.append(' '.join(buf_parts))
            buf_parts = [segment]
            buf_wc = seg_wc
    
    if buf_parts:
        scenes.append(' '.join(buf_parts))

    # ── Step 4b: Merge consecutive short scenes ───────────────────────────
    if len(scenes) > 1:
        merged = []
        i = 0
        while i < len(scenes):
            current = scenes[i]
            current_wc = len(current.split())
            
            while current_wc < min_words and i + 1 < len(scenes):
                next_scene = scenes[i + 1]
                next_wc = len(next_scene.split())
                
                if current_wc + next_wc <= max_words + 5:
                    current = current + ' ' + next_scene
                    current_wc = current_wc + next_wc
                    i += 1
                else:
                    break
            
            merged.append(current)
            i += 1
        
        scenes = merged

    # ── Step 5: Build result with estimated duration ──────────────────────
    result = []
    for i, content in enumerate(scenes):
        content = content.strip()
        if content:
            wc = len(content.split())
            scene_data = {
                "scene_id": i + 1,
                "content": content,
                "word_count": wc,
            }
            if split_mode == "footage":
                # Footage mode: no estimated duration, will be measured from actual audio
                scene_data["audio_duration"] = None
            else:
                scene_data["est_duration"] = _estimate_duration(wc, language)
            result.append(scene_data)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
# SCENE CONTEXT ANALYSIS - Character & Setting extraction
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyzeSceneContextRequest(BaseModel):
    script: str
    language: Optional[str] = 'vi'
    model: Optional[str] = None

@router.post("/analyze-scene-context")
async def analyze_scene_context(request: AnalyzeSceneContextRequest):
    """
    Analyze full script to extract consistent characters and settings.
    Returns characters[] and settings[] for use in per-scene prompt generation.
    """
    if not request.script or len(request.script.strip()) < 20:
        raise HTTPException(status_code=400, detail="Script quá ngắn để phân tích")

    try:
        ai_client = get_configured_ai_client(model=request.model)
        import concurrent.futures

        loop = asyncio.get_event_loop()
        lang_name = {
            'vi': 'Vietnamese', 'en': 'English', 'zh': 'Chinese',
            'ja': 'Japanese', 'ko': 'Korean', 'es': 'Spanish',
            'fr': 'French', 'th': 'Thai', 'pt': 'Portuguese'
        }.get(request.language, 'the given language')

        # Truncate script if too long (use first 3000 + last 1000 chars)
        script_text = request.script.strip()
        if len(script_text) > 4500:
            script_text = script_text[:3000] + "\n...\n" + script_text[-1000:]

        prompt = f"""You are a video production assistant. Analyze this {lang_name} script and extract the main CHARACTERS and SETTINGS for visual consistency across all scenes.

SCRIPT:
{script_text}

Extract:
1. **characters**: List of recurring characters/subjects. For each, provide:
   - id: unique identifier (e.g. "char_1")  
   - name: short name/label
   - visual_description: detailed visual appearance (age, gender, clothing, hair, features) in English for AI image/video generation
   - role: their role (protagonist, narrator, supporting, etc.)

2. **settings**: List of recurring locations/environments. For each, provide:
   - id: unique identifier (e.g. "set_1")
   - name: short name/label
   - visual_description: detailed visual description (lighting, colors, objects, atmosphere) in English for AI image/video generation

IMPORTANT:
- Descriptions must be in English for AI generation tools
- Be specific about visual details
- If the script is narration-style with no clear characters, create a character for the narrator's implied subject
- Return ONLY valid JSON, no other text

Return format:
{{
  "characters": [
    {{"id": "char_1", "name": "...", "visual_description": "...", "role": "protagonist"}}
  ],
  "settings": [
    {{"id": "set_1", "name": "...", "visual_description": "..."}}
  ]
}}"""

        def call_ai(p=prompt):
            return ai_client.generate(p, temperature=0.3)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            result_text = await loop.run_in_executor(pool, call_ai)

        import re as re_mod
        json_match = re_mod.search(r'\{[\s\S]*"characters"[\s\S]*"settings"[\s\S]*\}', result_text)
        if not json_match:
            json_match = re_mod.search(r'\{[\s\S]*\}', result_text)

        if json_match:
            context_data = json_module.loads(json_match.group())
            print(f"[SceneContext] Extracted {len(context_data.get('characters', []))} characters, {len(context_data.get('settings', []))} settings")
            return {
                "success": True,
                "characters": context_data.get("characters", []),
                "settings": context_data.get("settings", []),
            }
        else:
            return {"success": False, "error": "Could not parse AI response", "characters": [], "settings": []}

    except Exception as e:
        print(f"[SceneContext] Error: {e}")
        return {"success": False, "error": str(e), "characters": [], "settings": []}


# ═══════════════════════════════════════════════════════════════════════════════
# CONCEPT ANALYSIS - Deep script analysis for footage alignment
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyzeConceptRequest(BaseModel):
    script: str
    model: Optional[str] = None

@router.post("/analyze-concept")
async def analyze_concept(request: AnalyzeConceptRequest):
    """
    Analyze the full script to extract holistic concept information:
    theme, visual style, environments, subjects, mood, and footage guidelines.
    This is used to guide keyword generation and footage selection.
    """
    if not request.script or len(request.script.strip()) < 20:
        raise HTTPException(status_code=400, detail="Script qua ngan de phan tich")

    try:
        ai_client = get_configured_ai_client(model=request.model)
        import concurrent.futures

        loop = asyncio.get_event_loop()

        # Truncate script if too long (use first 4000 + last 1000 chars)
        script_text = request.script.strip()
        if len(script_text) > 5500:
            script_text = script_text[:4000] + "\n...\n" + script_text[-1000:]

        prompt = f"""You are a video production director and stock footage search expert. Analyze this script deeply and extract a COMPREHENSIVE CONCEPT PROFILE that will guide stock footage selection.

SCRIPT:
{script_text}

You MUST extract ALL of the following. Pay special attention to items marked [ANCHOR] — these will be used as HARD CONSTRAINTS for every keyword search.

1. **theme**: The main topic/subject of the entire script (e.g., "space exploration", "construction timelapse", "ocean wildlife documentary")
2. **visual_style**: Camera style, lighting, and visual approach (e.g., "cinematic slow-motion", "aerial drone", "timelapse photography", "close-up macro")
3. **environments**: List of ALL physical settings/locations mentioned or implied (e.g., ["deep space", "spacecraft interior", "planet surface"])
4. **subjects**: List of ALL people, objects, creatures, or activities (e.g., ["astronaut in spacesuit", "rocket launch", "control room operators"])
5. **mood**: Emotional tone (e.g., "awe-inspiring and epic", "tense and suspenseful")
6. **color_palette**: Dominant colors/tones (e.g., "dark blues with bright highlights")
7. **footage_guidelines**: Specific instructions for footage search to ensure EVERY clip matches the concept
8. **tempo**: Pacing (e.g., "slow and contemplative", "building from slow to intense")

[ANCHOR] KEYWORD CONSTRAINT FIELDS (CRITICAL — these control ALL keyword generation):

9. **concept_prefix**: 2-3 word prefix that MUST appear in EVERY search keyword. This ensures visual consistency. Examples: "timelapse construction", "underwater ocean", "aerial city", "close-up nature", "cinematic space". Pick the most defining visual characteristic.
10. **style_modifier**: 1-2 word modifier to append to keywords for style consistency. Examples: "timelapse", "slow motion", "aerial drone", "macro closeup", "4k cinematic"
11. **allowed_environments**: List of 5-10 specific environments that footage can show. Only footage matching these environments should be used. Use simple English words suitable for Pexels/Pixabay search. (e.g., ["construction site", "building foundation", "crane area", "scaffolding", "city skyline"])
12. **allowed_subjects**: List of 8-15 specific subjects/objects/people that can appear in footage. Use simple, concrete English nouns. (e.g., ["crane", "steel beam", "concrete mixer", "construction workers", "excavator", "building frame", "hard hat", "blueprint"])
13. **forbidden_terms**: List of 5-10 terms that MUST NEVER appear in keywords. These are off-topic or wrong-style terms. (e.g., ["cartoon", "animation", "illustration", "office meeting", "classroom", "abstract art"])

CRITICAL RULES:
- concept_prefix and style_modifier must be actual stock footage search terms (test: "would Pexels find results for this?")
- allowed_subjects/environments must be CONCRETE VISUAL things a camera can see, NOT abstract concepts
- forbidden_terms should block common AI mistakes that would produce wrong footage
- Be EXTREMELY specific — vague descriptions lead to mismatched footage
- Return ONLY valid JSON, no other text

Return format:
{{
  "theme": "...",
  "visual_style": "...",
  "environments": ["...", "..."],
  "subjects": ["...", "..."],
  "mood": "...",
  "color_palette": "...",
  "footage_guidelines": "...",
  "tempo": "...",
  "concept_prefix": "...",
  "style_modifier": "...",
  "allowed_environments": ["...", "..."],
  "allowed_subjects": ["...", "..."],
  "forbidden_terms": ["...", "..."]
}}"""

        def call_ai(p=prompt):
            return ai_client.generate(p, temperature=0.3)

        with concurrent.futures.ThreadPoolExecutor() as pool:
            result_text = await loop.run_in_executor(pool, call_ai)

        import re as re_mod
        json_match = re_mod.search(r'\{[\s\S]*"theme"[\s\S]*\}', result_text)
        if not json_match:
            json_match = re_mod.search(r'\{[\s\S]*\}', result_text)

        if json_match:
            concept_data = json_module.loads(json_match.group())
            logger.info(f"[ConceptAnalysis] theme='{concept_data.get('theme', '')[:50]}', "
                       f"style='{concept_data.get('visual_style', '')[:50]}', "
                       f"envs={len(concept_data.get('environments', []))}, "
                       f"subjects={len(concept_data.get('subjects', []))}")
            return {
                "success": True,
                "concept": concept_data,
            }
        else:
            return {"success": False, "error": "Could not parse AI response", "concept": None}

    except Exception as e:
        logger.error(f"[ConceptAnalysis] Error: {e}")
        return {"success": False, "error": str(e), "concept": None}


# ═══════════════════════════════════════════════════════════════════════════════
# AI KEYWORD & PROMPT GENERATION - Mode-based
# ═══════════════════════════════════════════════════════════════════════════════


def _validate_keyword_against_concept(keyword: str, concept_analysis: dict) -> str:
    """
    Filter 1: Validate and auto-fix a keyword against the concept anchor.
    - Auto-prepend concept_prefix if missing
    - Strip forbidden terms
    - Log violations for debugging
    """
    if not keyword or not concept_analysis:
        return keyword

    kw_lower = keyword.lower().strip()
    original = keyword
    fixed = False

    # 1. Check forbidden terms -> remove them
    forbidden = concept_analysis.get('forbidden_terms', [])
    if forbidden:
        for term in forbidden:
            term_lower = term.lower()
            if term_lower in kw_lower:
                keyword = keyword.replace(term, '').replace(term.lower(), '').strip()
                keyword = ' '.join(keyword.split())  # Clean double spaces
                kw_lower = keyword.lower()
                fixed = True
                print(f"[KeywordValidation] Removed forbidden term '{term}' from '{original}'")

    # 2. Check concept_prefix -> auto-prepend if missing
    concept_prefix = concept_analysis.get('concept_prefix', '')
    style_modifier = concept_analysis.get('style_modifier', '')

    has_prefix = concept_prefix and concept_prefix.lower() in kw_lower
    has_modifier = style_modifier and style_modifier.lower() in kw_lower

    if concept_prefix and not has_prefix and not has_modifier:
        # Prepend the style_modifier (shorter, better for search) or concept_prefix
        prefix_to_add = style_modifier if style_modifier else concept_prefix
        keyword = f"{prefix_to_add} {keyword}"
        fixed = True
        print(f"[KeywordValidation] Added prefix '{prefix_to_add}' -> '{keyword}'")

    # 3. Log if keyword has no allowed subject/environment match (warning only)
    allowed_subjects = [s.lower() for s in concept_analysis.get('allowed_subjects', [])]
    allowed_envs = [e.lower() for e in concept_analysis.get('allowed_environments', [])]

    if allowed_subjects or allowed_envs:
        has_subject = any(any(word in kw_lower for word in sub.split()) for sub in allowed_subjects)
        has_env = any(any(word in kw_lower for word in env.split()) for env in allowed_envs)

        if not has_subject and not has_env:
            print(f"[KeywordValidation] WARNING: '{keyword}' has no matching subject/env from allowed lists")

    if fixed:
        print(f"[KeywordValidation] '{original}' -> '{keyword}'")

    return keyword.strip()


class SceneKeywordItem(BaseModel):
    scene_id: int
    content: str
    audio_duration: Optional[float] = None  # Actual measured audio duration in seconds

class GenerateSceneKeywordsRequest(BaseModel):
    scenes: List[SceneKeywordItem]
    language: Optional[str] = 'vi'
    model: Optional[str] = None
    # Mode-based generation
    mode: Optional[str] = 'footage'  # footage | concept | storytelling | custom
    generate_image_prompt: Optional[bool] = False
    generate_video_prompt: Optional[bool] = False
    generate_keywords: Optional[bool] = True  # Whether to generate keywords (default True for backward compat)
    consistent_characters: Optional[bool] = False
    consistent_settings: Optional[bool] = False
    # User-provided style and character for prompts
    prompt_style: Optional[str] = None  # e.g. "cinematic photorealism, golden hour, 35mm"
    main_character: Optional[str] = None  # e.g. "28yo Vietnamese man, short black hair, glasses"
    # Context from analyze-scene-context (for consistency)
    scene_context: Optional[Dict[str, Any]] = None
    # Concept analysis from /analyze-concept (for concept-aligned keywords)
    concept_analysis: Optional[Dict[str, Any]] = None
    # Context/environment description for full_sync mode
    context_description: Optional[str] = None  # Environment/setting description for consistency
    # Prompt mode hints
    image_prompt_mode: Optional[str] = None   # reference | scene_builder | concept
    video_prompt_mode: Optional[str] = None   # character_sync | scene_sync | full_sync
    # Direction analysis notes (from video_direction step) for informed prompt generation
    directions: Optional[List[Dict[str, Any]]] = None
    # Sync analysis data (characters, settings, visual_style)
    sync_analysis: Optional[Dict[str, Any]] = None


@router.post("/generate-scene-keywords")
async def generate_scene_keywords(request: GenerateSceneKeywordsRequest):
    """
    Generate keywords and prompts for each scene using AI.
    Supports 4 modes: footage (keyword only), concept (keyword + image),
    storytelling (keyword + image + video), custom (user picks).
    """
    if not request.scenes:
        raise HTTPException(status_code=400, detail="Không có scene nào")

    # Determine what to generate based on mode
    gen_image = request.generate_image_prompt
    gen_video = request.generate_video_prompt
    gen_keywords = request.generate_keywords if request.generate_keywords is not None else True
    use_chars = request.consistent_characters
    use_settings = request.consistent_settings

    if request.mode == 'footage':
        gen_image = False
        gen_video = False
        use_chars = False
        use_settings = False
    elif request.mode == 'concept':
        gen_image = True
        gen_video = False
        use_chars = False
        use_settings = False
    elif request.mode == 'storytelling':
        gen_image = True
        gen_video = True
        use_chars = True
        use_settings = True
    # 'custom' uses the flags as-is from request

    async def event_generator():
        try:
            ai_client = get_configured_ai_client(model=request.model)
            import concurrent.futures
            import re as re_mod

            loop = asyncio.get_event_loop()
            lang_name = LANG_NAME_MAP.get(request.language, 'the same language as the scenes')

            total_scenes = len(request.scenes)
            result_map = {}

            mode_label = request.mode or 'footage'
            print(f"[SceneKeywords] Mode={mode_label} | {total_scenes} scenes | image={gen_image} video={gen_video} chars={use_chars} settings={use_settings}")

            # Dynamic batch size based on what's being generated:
            # - Keywords only (~10 words/scene) → no batch needed
            # - Keywords + image prompts (~70 words/scene) → batch 20
            # - Keywords + image + video prompts (~190 words/scene) → batch 10
            if gen_image and gen_video:
                BATCH_SIZE = 10
            elif gen_image or gen_video:
                BATCH_SIZE = 20
            else:
                BATCH_SIZE = total_scenes  # keywords only → no batching

            if total_scenes <= BATCH_SIZE:
                scene_batches = [request.scenes]
                num_batches = 1
            else:
                scene_batches = [request.scenes[i:i + BATCH_SIZE] for i in range(0, total_scenes, BATCH_SIZE)]
                num_batches = len(scene_batches)
            batch_label = f'{num_batches} batch' if num_batches > 1 else '1 lần'

            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Keywords: {total_scenes} scenes ({batch_label})', 'current': 0, 'total': total_scenes, 'percentage': 2}, ensure_ascii=False)}\n\n"

            # Build consistency context block
            consistency_block = ""
            if (use_chars or use_settings) and request.scene_context:
                parts = []
                if use_chars and request.scene_context.get('characters'):
                    chars_desc = "\n".join([
                        f"  - {c.get('name', 'Character')}: {c.get('visual_description', '')}"
                        for c in request.scene_context['characters']
                    ])
                    parts.append(f"RECURRING CHARACTERS (use these descriptions consistently):\n{chars_desc}")
                if use_settings and request.scene_context.get('settings'):
                    sets_desc = "\n".join([
                        f"  - {s.get('name', 'Setting')}: {s.get('visual_description', '')}"
                        for s in request.scene_context['settings']
                    ])
                    parts.append(f"RECURRING SETTINGS (use these descriptions consistently):\n{sets_desc}")
                if parts:
                    consistency_block = "\n" + "\n\n".join(parts) + "\n"



            # ── BATCHED PROMPT GENERATION ──
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Tạo prompts: {total_scenes} scenes ({batch_label})', 'current': 0, 'total': total_scenes, 'percentage': 10}, ensure_ascii=False)}\n\n"

            # Build CONCEPT ANCHOR block
            concept_anchor_block = ""
            has_anchor = False
            if request.concept_analysis:
                ca = request.concept_analysis
                anchor_parts = []
                if ca.get('concept_prefix'):
                    anchor_parts.append(f"CONCEPT PREFIX (MUST appear in EVERY keyword): \"{ca['concept_prefix']}\"")
                if ca.get('style_modifier'):
                    anchor_parts.append(f"STYLE MODIFIER (append to keywords for consistency): \"{ca['style_modifier']}\"")
                if ca.get('allowed_environments') and isinstance(ca['allowed_environments'], list):
                    envs = ', '.join([f'"{e}"' for e in ca['allowed_environments'][:10]])
                    anchor_parts.append(f"ALLOWED ENVIRONMENTS (pick ONLY from this list): [{envs}]")
                if ca.get('allowed_subjects') and isinstance(ca['allowed_subjects'], list):
                    subs = ', '.join([f'"{s}"' for s in ca['allowed_subjects'][:15]])
                    anchor_parts.append(f"ALLOWED SUBJECTS (pick ONLY from this list): [{subs}]")
                if ca.get('forbidden_terms') and isinstance(ca['forbidden_terms'], list):
                    forbidden = ', '.join([f'"{f}"' for f in ca['forbidden_terms'][:10]])
                    anchor_parts.append(f"FORBIDDEN TERMS (NEVER use any of these): [{forbidden}]")
                if ca.get('theme'):
                    anchor_parts.append(f"Theme: {ca['theme']}")
                if ca.get('visual_style'):
                    anchor_parts.append(f"Visual Style: {ca['visual_style']}")
                if ca.get('footage_guidelines'):
                    anchor_parts.append(f"Footage Guidelines: {ca['footage_guidelines']}")

                if anchor_parts:
                    has_anchor = True
                    concept_anchor_block = "\n\n══ CONCEPT ANCHOR (MANDATORY — every keyword MUST obey these rules) ══\n" + "\n".join(anchor_parts) + "\n══ END CONCEPT ANCHOR ══\n"

            concept_prefix_str = request.concept_analysis.get('concept_prefix', '') if request.concept_analysis else ''
            style_modifier_str = request.concept_analysis.get('style_modifier', '') if request.concept_analysis else ''

            # Shared context: direction notes map
            dir_map = {}
            if request.directions and (gen_image or gen_video):
                dir_map = {d.get('scene_id'): d for d in request.directions if d.get('scene_id')}

            # Pre-compute scene metadata for all scenes
            scene_meta = {}
            for scene in request.scenes:
                import math
                if gen_keywords and scene.audio_duration and scene.audio_duration > 0:
                    keyword_count = max(1, math.ceil(scene.audio_duration / 4))
                    target_clip_duration = round(scene.audio_duration / keyword_count, 1)
                else:
                    keyword_count = 1
                    target_clip_duration = 4.0
                scene_meta[scene.scene_id] = {
                    'keyword_count': keyword_count,
                    'target_clip_duration': target_clip_duration,
                }

            # Build example output block (shared)
            first_scene = request.scenes[0]
            first_kw_count = scene_meta[first_scene.scene_id]['keyword_count']
            example_lines = [f"===SCENE {first_scene.scene_id}==="]
            if gen_keywords:
                if first_kw_count > 1:
                    example_lines.append("KEYWORDS: keyword1 | keyword2")
                else:
                    example_lines.append("KEYWORD: visual keyword describing what camera sees")
            if gen_image:
                example_lines.append("IMAGE_PROMPT: A detailed narrative paragraph for AI image generation following the 7-component structure...")
            if gen_video:
                example_lines.append("VIDEO_PROMPT: A detailed narrative paragraph for AI video generation following the 7-component structure...")
            example_output = "\n".join(example_lines)

            # ── 7-COMPONENT UNIVERSAL PROMPTING FRAMEWORK ──
            prompt_framework_block = ""
            if gen_image or gen_video:
                components_for_image = """
══ 7-COMPONENT UNIVERSAL PROMPTING FRAMEWORK ══
You MUST generate structured narrative prompts following this exact framework.
Write each prompt as ONE FLOWING PARAGRAPH in natural English — NOT as a list of tags or keywords ("tag soup" is forbidden).

The 7 components to weave into each prompt:

1. **SUBJECT** (Who/What): The visual anchor. Include identity, age, physical features, clothing, distinguishing marks.
   - BAD: "a man"
   - GOOD: "a weathered 40-year-old fisherman with a salt-and-pepper beard, wearing a faded yellow raincoat"

2. **CONTEXT** (Where): Environment, time of day, weather, spatial details. Describe light sources so the AI can compute shadows.
   - BAD: "in a room"
   - GOOD: "in a sun-drenched Victorian study, dust motes dancing in shafts of light streaming through tall floor-to-ceiling bay windows"

3. **ACTION** (What happens): For images = pose/state. For video = movement verbs + cause-and-effect interactions.
   - Image: "frozen mid-leap", "sitting pensively"
   - Video: "walking with a heavy limp", "water splashing violently as she dives in"

4. **CINEMATOGRAPHY** (How): Shot type + lens + camera movement.
   - Shot types: ECU (extreme close-up), CU (close-up), MS (medium shot), WS (wide shot)
   - Lenses: "35mm natural", "85mm portrait bokeh", "macro 100mm", "fisheye wide-angle"
   - Camera (video): "slow dolly in", "orbit/arc shot", "handheld shaky", "crane up reveal", "tracking shot"

5. **AESTHETICS** (Feel): Art style, lighting technique, color palette, mood/emotion.
   - Styles: "photorealistic", "cinematic", "3D render (Unreal Engine 5)", "oil painting", "anime (Studio Ghibli)"
   - Lighting: "golden hour warm", "blue hour cold", "noir high-contrast", "volumetric god rays", "softbox studio"
   - Colors: describe dominant palette tones

6. **AUDIO** (Soundscape — VIDEO PROMPTS ONLY): Dialogue (in quotes), SFX quality, ambient environment sounds.
   - BAD: "has audio"
   - GOOD: "Audio: crisp crunch of dry leaves underfoot, labored breathing, and the distant plaintive cry of a crow"

7. **CONSTRAINTS** (Guardrails): Aspect ratio, resolution, negative prompt (what to avoid).
   - "No text overlays, no blurry backgrounds, no distorted fingers, 16:9 cinematic"

══ CRITICAL RULES FOR PROMPTS ══
- Write as ONE FLOWING NARRATIVE PARAGRAPH per prompt — NOT bullet points or tag lists
- Use NATURAL LANGUAGE with cause-and-effect reasoning ("because", "as", "while")
- All prompts MUST be in ENGLISH for AI generation tools
- Each scene prompt must be UNIQUE and tell a different visual story
- Maintain CHARACTER CONSISTENCY across all scenes (same descriptions for recurring characters)
- Maintain SETTING CONSISTENCY (same environment details when scenes share locations)
- **WORD COUNT LIMITS (STRICTLY ENFORCED)**:
  - IMAGE_PROMPT: 40-60 words maximum. Be precise and dense — every word must add visual information. Cut filler words ruthlessly.
  - VIDEO_PROMPT: 80-120 words maximum. Include motion, camera, audio — but stay concise. No verbose padding.
  - These limits ensure compatibility with Midjourney (60-word sweet spot), DALL-E 3, Flux (77-token CLIP limit), VEO3, and Runway (1000-char limit).
"""
                prompt_framework_block = components_for_image

                if request.main_character:
                    prompt_framework_block += f"""
══ MAIN CHARACTER (must appear consistently in ALL scenes) ══
{request.main_character}
Use this EXACT description every time the main character appears. Do NOT change their appearance across scenes.
"""
                if request.prompt_style:
                    prompt_framework_block += f"""
══ VISUAL STYLE DIRECTION (apply to ALL prompts) ══
{request.prompt_style}
Weave this style consistently into the Aesthetics and Cinematography components of every prompt.
"""
                if request.context_description:
                    prompt_framework_block += f"""
══ ENVIRONMENT/CONTEXT (maintain consistency across ALL scenes) ══
{request.context_description}
Use this EXACT environment description when the scene takes place in this setting. Maintain spatial continuity, lighting, and atmosphere.
"""
                if request.sync_analysis:
                    sa = request.sync_analysis
                    sync_parts = []
                    if sa.get('characters'):
                        chars = "\n".join([f"  - {c.get('name', '')}: {c.get('visual_description', c.get('description', ''))}" for c in sa['characters'][:5]])
                        sync_parts.append(f"SYNC CHARACTERS (use these descriptions consistently):\n{chars}")
                    if sa.get('settings'):
                        sets = "\n".join([f"  - {s.get('name', '')}: {s.get('visual_description', s.get('description', ''))}" for s in sa['settings'][:5]])
                        sync_parts.append(f"SYNC SETTINGS (use these descriptions consistently):\n{sets}")
                    if sa.get('visual_style'):
                        sync_parts.append(f"SYNC VISUAL STYLE (apply to ALL prompts): {sa['visual_style']}")
                    if sync_parts:
                        prompt_framework_block += "\n══ SYNC ANALYSIS (follow these constraints for consistency) ══\n" + "\n".join(sync_parts) + "\n"

                if request.video_prompt_mode == 'character_sync':
                    prompt_framework_block += """
══ MODE: CHARACTER SYNC ══
PRIORITY: Character identity consistency is the #1 concern. Repeat full character description (Identity Layer) in EVERY prompt.
Ensure the same person is recognizable across all scenes — same face, hair, body type, clothing.
"""
                elif request.video_prompt_mode == 'scene_sync':
                    prompt_framework_block += """
══ MODE: STYLE SYNC ══
PRIORITY: Visual style and aesthetic consistency is the #1 concern.
Maintain identical color grading, lighting style, camera language, and art direction across ALL scenes.
"""
                elif request.video_prompt_mode == 'full_sync':
                    prompt_framework_block += """
══ MODE: FULL SYNC (Character + Style + Context) ══
PRIORITY: Triple consistency — Character identity + Visual style + Environment must ALL remain consistent.
1. Repeat full character description (Identity Layer) in EVERY prompt
2. Maintain identical aesthetics (color grade, lighting, lens) across ALL scenes
3. Keep environment/spatial details consistent when scenes share locations
"""
                if gen_image and not gen_video:
                    prompt_framework_block += """
For "image_prompt": Combine components 1-5 and 7 into a single flowing paragraph (skip Audio). STRICT LIMIT: 40-60 words.
"""
                elif gen_video and not gen_image:
                    prompt_framework_block += """
For "video_prompt": Combine ALL 7 components into a single flowing paragraph. Include camera MOVEMENT verbs and Audio descriptions. STRICT LIMIT: 80-120 words.
"""
                else:
                    prompt_framework_block += """
For "image_prompt": Combine components 1-5 and 7 into a single flowing paragraph (skip Audio). Focus on STATIC composition — pose, framing, lighting. STRICT LIMIT: 40-60 words.
For "video_prompt": Combine ALL 7 components into a single flowing paragraph. Focus on MOTION — camera movement, character action, physics, audio. STRICT LIMIT: 80-120 words.
"""
                prompt_framework_block += "══ END FRAMEWORK ══\n"

            # Build anchor rules (shared)
            anchor_rules = ""
            if has_anchor:
                anchor_rules = f"""\n══ MANDATORY RULES ══
1. Every keyword MUST contain the concept prefix \"{concept_prefix_str}\" OR style modifier \"{style_modifier_str}\"
2. Subjects MUST come from the ALLOWED SUBJECTS list
3. Environments MUST come from the ALLOWED ENVIRONMENTS list
4. Keywords MUST NEVER contain any FORBIDDEN TERMS
5. Keywords must be concrete visual descriptions: what a camera literally sees
6. Use simple English words that Pexels/Pixabay understand
7. NO duplicate keywords across scenes — each scene must have UNIQUE footage
8. Keywords should create a coherent visual STORYBOARD: flowing naturally from scene to scene
9. Think: "If I search this on Pexels, will I find matching video clips?"
{('10. image_prompt and video_prompt must follow the 7-COMPONENT FRAMEWORK above — flowing narrative paragraphs, NOT tag lists' if (gen_image or gen_video) else '')}"""
            else:
                anchor_rules = f"""\n══ RULES ══
1. Keywords MUST describe what a camera literally sees: objects, people, actions, places, lighting
2. Use simple, common English words that stock footage sites understand
3. AVOID abstract concepts, emotions, narrative terms ("journey", "realization", "tension", "discovery")
4. NO duplicate keywords across scenes — each scene must have UNIQUE footage
5. Keywords should create a coherent visual STORYBOARD: flowing naturally from scene to scene
6. Think: "If I search this on Pexels, will I find matching video clips?"
{('7. image_prompt and video_prompt must follow the 7-COMPONENT FRAMEWORK above — flowing narrative paragraphs, NOT tag lists' if (gen_image or gen_video) else '')}"""

            # Build dynamic task description
            task_parts = []
            if gen_keywords:
                task_parts.append('keywords')
            if gen_image and gen_video:
                task_parts.append('image/video prompts')
            elif gen_image:
                task_parts.append('image prompts')
            elif gen_video:
                task_parts.append('video prompts')
            task_desc = ' + '.join(task_parts) if task_parts else 'keywords'

            # ── PER-BATCH LOOP: Build prompt, call AI, parse results ──
            for batch_idx, batch_scenes in enumerate(scene_batches):
                batch_num = batch_idx + 1
                batch_start_pct = 10 + int(80 * batch_idx / num_batches)
                batch_end_pct = 10 + int(80 * (batch_idx + 1) / num_batches)
                batch_scene_count = len(batch_scenes)

                if num_batches > 1:
                    yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Batch {batch_num}/{num_batches}: {batch_scene_count} scenes', 'current': sum(len(b) for b in scene_batches[:batch_idx]), 'total': total_scenes, 'percentage': batch_start_pct}, ensure_ascii=False)}\n\n"

                # Build per-batch scenes block
                scenes_block_parts = []
                for scene in batch_scenes:
                    meta = scene_meta[scene.scene_id]
                    base = f"Scene {scene.scene_id} ({meta['keyword_count']} keywords needed, ~{meta['target_clip_duration']}s each): {scene.content}"
                    d = dir_map.get(scene.scene_id)
                    if d and d.get('direction_notes'):
                        base += f"\n  [DIRECTION]: {d['direction_notes']}"
                    scenes_block_parts.append(base)
                scenes_block = "\n".join(scenes_block_parts)

                prompt = f"""You are a visual STORYBOARD director. Generate {task_desc} for ALL {batch_scene_count} scenes at once to ensure consistency and flow.
The script is in {lang_name}.
{concept_anchor_block if has_anchor else ''}{consistency_block}{prompt_framework_block}
══ SCENES ({batch_scene_count} scenes{f', batch {batch_num}/{num_batches}' if num_batches > 1 else ''}) ══
{scenes_block}
{anchor_rules}

Return EXACTLY {batch_scene_count} scene blocks in this format (NO JSON, plain text only):

{example_output}
===SCENE 2===
...

Return ONLY the scene blocks, no other text."""

                print(f"[SceneKeywords] {'Batch ' + str(batch_num) + '/' + str(num_batches) + ': ' if num_batches > 1 else ''}{batch_scene_count} scenes, anchor={has_anchor}, image={gen_image}, video={gen_video}")

                progress_msg = f'AI: {batch_scene_count} scenes'
                parts = []
                if gen_keywords:
                    parts.append('keywords')
                if gen_image and gen_video:
                    parts.append('image/video prompts')
                elif gen_image:
                    parts.append('image prompts')
                elif gen_video:
                    parts.append('video prompts')
                if parts:
                    progress_msg += f' ({", ".join(parts)})'

                yield f"data: {json_module.dumps({'type': 'progress', 'message': progress_msg, 'current': sum(len(b) for b in scene_batches[:batch_idx]), 'total': total_scenes, 'percentage': batch_start_pct + 10}, ensure_ascii=False)}\n\n"

                def _sanitize_prompt(text: str) -> str:
                    """Strip null bytes and problematic control chars that cause [Errno 22] on Windows"""
                    import unicodedata
                    # Remove null bytes
                    text = text.replace('\x00', '')
                    # Remove other control characters except newline/tab/carriage-return
                    text = ''.join(
                        ch for ch in text
                        if ch in ('\n', '\r', '\t') or not unicodedata.category(ch).startswith('C')
                    )
                    return text

                def call_ai(p=prompt):
                    return ai_client.generate(_sanitize_prompt(p), temperature=0.3)

                try:
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result_text = await loop.run_in_executor(pool, call_ai)

                    print(f"[SceneKeywords] Prompt length: {len(prompt)} chars | AI response length: {len(result_text)} chars")
                    print(f"[SceneKeywords] AI response LAST 200 chars: ...{result_text[-200:]}")
                    scene_blocks = re_mod.split(r'===SCENE\s+(\d+)===', result_text)
                    expected_parts = batch_scene_count * 2 + 1
                    print(f"[SceneKeywords] re.split produced {len(scene_blocks)} parts (expect {expected_parts} for {batch_scene_count} scenes)")
                    parsed_count = 0
                    if len(scene_blocks) >= 3:
                        for i in range(1, len(scene_blocks), 2):
                            try:
                                scene_id = int(scene_blocks[i])
                            except (ValueError, IndexError):
                                continue
                            block = scene_blocks[i + 1] if i + 1 < len(scene_blocks) else ''
                            entry = {'scene_id': scene_id}
                            meta = scene_meta.get(scene_id, {'keyword_count': 1, 'target_clip_duration': 4.0})

                            kw_multi = re_mod.search(r'KEYWORDS?:\s*(.+)', block)
                            if kw_multi:
                                kw_text = kw_multi.group(1).strip()
                                if '|' in kw_text:
                                    raw_keywords = [k.strip() for k in kw_text.split('|') if k.strip()]
                                else:
                                    raw_keywords = [kw_text]
                                if has_anchor:
                                    raw_keywords = [_validate_keyword_against_concept(kw, request.concept_analysis) for kw in raw_keywords]
                                if len(raw_keywords) > 1:
                                    entry['keywords'] = raw_keywords
                                    entry['target_clip_duration'] = meta['target_clip_duration']
                                entry['keyword'] = raw_keywords[0] if raw_keywords else ''
                                print(f"[SceneKeywords] Scene {scene_id}: keyword='{entry['keyword'][:50]}'")
                            else:
                                entry['keyword'] = ''

                            if gen_image:
                                img_match = re_mod.search(r'IMAGE_PROMPT:\s*(.+?)(?=\n(?:VIDEO_PROMPT:|KEYWORD|===SCENE)|$)', block, re_mod.DOTALL)
                                raw_img = img_match.group(1).strip() if img_match else ''
                                # Enforce 60-word limit for image prompts
                                if raw_img and len(raw_img.split()) > 65:
                                    words = raw_img.split()
                                    raw_img = ' '.join(words[:60])
                                    # Try to end at last sentence boundary
                                    for punc in ['. ', ', ']:
                                        last_punc = raw_img.rfind(punc)
                                        if last_punc > len(raw_img) * 0.6:
                                            raw_img = raw_img[:last_punc + 1]
                                            break
                                entry['image_prompt'] = raw_img
                            if gen_video:
                                vid_match = re_mod.search(r'VIDEO_PROMPT:\s*(.+?)(?=\n(?:IMAGE_PROMPT:|KEYWORD|===SCENE)|$)', block, re_mod.DOTALL)
                                raw_vid = vid_match.group(1).strip() if vid_match else ''
                                # Enforce 120-word limit for video prompts
                                if raw_vid and len(raw_vid.split()) > 130:
                                    words = raw_vid.split()
                                    raw_vid = ' '.join(words[:120])
                                    for punc in ['. ', ', ']:
                                        last_punc = raw_vid.rfind(punc)
                                        if last_punc > len(raw_vid) * 0.6:
                                            raw_vid = raw_vid[:last_punc + 1]
                                            break
                                entry['video_prompt'] = raw_vid
                                print(f"[SceneKeywords] Scene {scene_id}: video_prompt len={len(entry.get('video_prompt', ''))}, words={len(entry.get('video_prompt', '').split())}, first 80: '{entry.get('video_prompt', '')[:80]}'")

                            result_map[scene_id] = entry
                            parsed_count += 1

                    if parsed_count == 0:
                        print(f"[SceneKeywords] Separator format not found, trying JSON fallback...")
                        print(f"[SceneKeywords] AI response first 500 chars: {result_text[:500]}")
                        json_match = re_mod.search(r'\[[\s\S]*\]', result_text)
                        if json_match:
                            try:
                                parsed = json_module.loads(json_match.group())
                                if isinstance(parsed, dict):
                                    parsed = [parsed]
                                for item in parsed:
                                    sid = item.get('scene_id')
                                    if sid is None:
                                        continue
                                    entry = {'scene_id': sid}
                                    entry['keyword'] = item.get('keyword', item.get('keywords', [''])[0] if isinstance(item.get('keywords'), list) else '')
                                    if gen_image and item.get('image_prompt', ''):
                                        raw_img = item['image_prompt'].strip()
                                        if len(raw_img.split()) > 65:
                                            wds = raw_img.split()
                                            raw_img = ' '.join(wds[:60])
                                            for punc in ['. ', ', ']:
                                                lp = raw_img.rfind(punc)
                                                if lp > len(raw_img) * 0.6:
                                                    raw_img = raw_img[:lp + 1]
                                                    break
                                        entry['image_prompt'] = raw_img
                                    if gen_video and item.get('video_prompt', ''):
                                        raw_vid = item['video_prompt'].strip()
                                        if len(raw_vid.split()) > 130:
                                            wds = raw_vid.split()
                                            raw_vid = ' '.join(wds[:120])
                                            for punc in ['. ', ', ']:
                                                lp = raw_vid.rfind(punc)
                                                if lp > len(raw_vid) * 0.6:
                                                    raw_vid = raw_vid[:lp + 1]
                                                    break
                                        entry['video_prompt'] = raw_vid
                                    result_map[sid] = entry
                            except json_module.JSONDecodeError:
                                pass

                    # ── Retry missing scenes from this batch ──
                    missing_scenes = [s for s in batch_scenes if s.scene_id not in result_map]
                    if missing_scenes and len(missing_scenes) < len(batch_scenes):
                        print(f"[SceneKeywords] Batch {batch_num}: {len(missing_scenes)} scenes missing, retrying...")
                        yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Retry {len(missing_scenes)} missing scenes', 'current': sum(len(b) for b in scene_batches[:batch_idx + 1]) - len(missing_scenes), 'total': total_scenes, 'percentage': batch_end_pct - 5}, ensure_ascii=False)}\n\n"
                        retry_block_parts = []
                        for scene in missing_scenes:
                            meta = scene_meta[scene.scene_id]
                            base = f"Scene {scene.scene_id} ({meta['keyword_count']} keywords needed, ~{meta['target_clip_duration']}s each): {scene.content}"
                            d = dir_map.get(scene.scene_id)
                            if d and d.get('direction_notes'):
                                base += f"\n  [DIRECTION]: {d['direction_notes']}"
                            retry_block_parts.append(base)
                        retry_scenes_block = "\n".join(retry_block_parts)
                        retry_prompt = f"""You are a visual STORYBOARD director. Generate {task_desc} for ALL {len(missing_scenes)} scenes.
The script is in {lang_name}.
{concept_anchor_block if has_anchor else ''}{consistency_block}{prompt_framework_block}
══ SCENES ({len(missing_scenes)} scenes) ══
{retry_scenes_block}
{anchor_rules}

Return EXACTLY {len(missing_scenes)} scene blocks in this format (NO JSON, plain text only):

{example_output}
===SCENE 2===
...

Return ONLY the scene blocks, no other text."""
                        try:
                            def call_retry(p=retry_prompt):
                                return ai_client.generate(_sanitize_prompt(p), temperature=0.3)
                            with concurrent.futures.ThreadPoolExecutor() as pool:
                                retry_text = await loop.run_in_executor(pool, call_retry)
                            retry_blocks = re_mod.split(r'===SCENE\s+(\d+)===', retry_text)
                            retry_parsed = 0
                            for ri in range(1, len(retry_blocks), 2):
                                try:
                                    rsid = int(retry_blocks[ri])
                                    rblock = retry_blocks[ri + 1] if ri + 1 < len(retry_blocks) else ''
                                    rentry = {'scene_id': rsid}
                                    rkw = re_mod.search(r'KEYWORDS?:\s*(.+)', rblock)
                                    if rkw:
                                        rkw_text = rkw.group(1).strip()
                                        if '|' in rkw_text:
                                            rraw_kws = [k.strip() for k in rkw_text.split('|') if k.strip()]
                                        else:
                                            rraw_kws = [rkw_text]
                                        if len(rraw_kws) > 1:
                                            rentry['keywords'] = rraw_kws
                                            rmeta = scene_meta.get(rsid, {'target_clip_duration': 4.0})
                                            rentry['target_clip_duration'] = rmeta['target_clip_duration']
                                        rentry['keyword'] = rraw_kws[0] if rraw_kws else ''
                                    else:
                                        rentry['keyword'] = ''
                                    if gen_image:
                                        rimg = re_mod.search(r'IMAGE_PROMPT:\s*(.+?)(?=\n(?:VIDEO_PROMPT:|KEYWORD|===SCENE)|$)', rblock, re_mod.DOTALL)
                                        rentry['image_prompt'] = rimg.group(1).strip() if rimg else ''
                                    if gen_video:
                                        rvid = re_mod.search(r'VIDEO_PROMPT:\s*(.+?)(?=\n(?:IMAGE_PROMPT:|KEYWORD|===SCENE)|$)', rblock, re_mod.DOTALL)
                                        rentry['video_prompt'] = rvid.group(1).strip() if rvid else ''
                                    result_map[rsid] = rentry
                                    retry_parsed += 1
                                except (ValueError, IndexError):
                                    pass
                            print(f"[SceneKeywords] Retry recovered {retry_parsed}/{len(missing_scenes)} scenes")
                        except Exception as retry_err:
                            print(f"[SceneKeywords] Retry failed: {retry_err}")

                    # Fill any still-missing scenes after retry
                    for scene in batch_scenes:
                        if scene.scene_id not in result_map:
                            print(f"[SceneKeywords] Scene {scene.scene_id} still missing after retry, using empty")
                            result_map[scene.scene_id] = _empty_result(scene.scene_id, gen_image, gen_video)

                    # Summary stats
                    batch_parsed = sum(1 for s in batch_scenes if s.scene_id in result_map and result_map[s.scene_id].get('keyword', ''))
                    vp_count = sum(1 for v in result_map.values() if v.get('video_prompt', '').strip())
                    ip_count = sum(1 for v in result_map.values() if v.get('image_prompt', '').strip())
                    print(f"[SceneKeywords] Batch {batch_num}/{num_batches}: {batch_parsed}/{batch_scene_count} scenes OK (total: {len(result_map)}/{total_scenes}, video_prompt: {vp_count}, image_prompt: {ip_count})")

                except OSError as os_err:
                    # Retry once with smaller sub-batches on Windows Errno 22
                    print(f"[SceneKeywords] OSError in batch {batch_num}, retrying with smaller batches: {os_err}")
                    import traceback
                    print(traceback.format_exc())
                    half = len(batch_scenes) // 2 or 1
                    for sub_start in range(0, len(batch_scenes), half):
                        sub_scenes = batch_scenes[sub_start:sub_start + half]
                        sub_block_parts = []
                        for scene in sub_scenes:
                            meta = scene_meta[scene.scene_id]
                            base = f"Scene {scene.scene_id} ({meta['keyword_count']} keywords needed, ~{meta['target_clip_duration']}s each): {scene.content}"
                            d = dir_map.get(scene.scene_id)
                            if d and d.get('direction_notes'):
                                base += f"\n  [DIRECTION]: {d['direction_notes']}"
                            sub_block_parts.append(base)
                        sub_scenes_block = "\n".join(sub_block_parts)
                        sub_prompt = f"""You are a visual STORYBOARD director. Generate {task_desc} for ALL {len(sub_scenes)} scenes.
The script is in {lang_name}.
{concept_anchor_block if has_anchor else ''}{consistency_block}{prompt_framework_block}
══ SCENES ({len(sub_scenes)} scenes) ══
{sub_scenes_block}
{anchor_rules}

Return EXACTLY {len(sub_scenes)} scene blocks in this format (NO JSON, plain text only):

{example_output}
===SCENE 2===
...

Return ONLY the scene blocks, no other text."""
                        try:
                            def call_sub(p=sub_prompt):
                                return ai_client.generate(_sanitize_prompt(p), temperature=0.3)
                            with concurrent.futures.ThreadPoolExecutor() as pool:
                                sub_text = await loop.run_in_executor(pool, call_sub)
                            # Parse sub-batch result (same as main parsing)
                            import re as re_sub
                            sub_blocks = re_sub.split(r'===\s*SCENE\s+(\d+)\s*===', sub_text)
                            for j in range(1, len(sub_blocks), 2):
                                try:
                                    sid = int(sub_blocks[j])
                                    content = sub_blocks[j + 1].strip() if j + 1 < len(sub_blocks) else ''
                                    entry = {'scene_id': sid}
                                    for line in content.split('\n'):
                                        line = line.strip()
                                        if line.upper().startswith('KEYWORD:') or line.upper().startswith('KEYWORDS:'):
                                            kw = line.split(':', 1)[1].strip()
                                            entry['keyword'] = kw.split('|')[0].strip() if '|' in kw else kw
                                            if '|' in kw:
                                                entry['keywords'] = [k.strip() for k in kw.split('|')]
                                        elif line.upper().startswith('IMAGE_PROMPT:'):
                                            entry['image_prompt'] = line.split(':', 1)[1].strip()
                                        elif line.upper().startswith('VIDEO_PROMPT:'):
                                            entry['video_prompt'] = line.split(':', 1)[1].strip()
                                    if entry.get('keyword') or entry.get('image_prompt') or entry.get('video_prompt'):
                                        result_map[sid] = entry
                                except (ValueError, IndexError):
                                    pass
                            print(f"[SceneKeywords] Sub-batch retry OK: {len(sub_scenes)} scenes")
                        except Exception as sub_err:
                            print(f"[SceneKeywords] Sub-batch retry also failed: {sub_err}")
                            for scene in sub_scenes:
                                if scene.scene_id not in result_map:
                                    entry = _empty_result(scene.scene_id, gen_image, gen_video)
                                    entry['keyword'] = f'(error: {str(sub_err)[:40]})'
                                    result_map[scene.scene_id] = entry
                    # Fill any still-missing scenes
                    for scene in batch_scenes:
                        if scene.scene_id not in result_map:
                            entry = _empty_result(scene.scene_id, gen_image, gen_video)
                            entry['keyword'] = f'(error: {str(os_err)[:40]})'
                            result_map[scene.scene_id] = entry

                except Exception as ai_err:
                    print(f"[SceneKeywords] Batch AI error: {ai_err}")
                    import traceback
                    print(traceback.format_exc())
                    for scene in batch_scenes:
                        if scene.scene_id not in result_map:
                            entry = _empty_result(scene.scene_id, gen_image, gen_video)
                            entry['keyword'] = f'(error: {str(ai_err)[:40]})'
                            result_map[scene.scene_id] = entry
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Xong: {total_scenes}/{total_scenes} scenes', 'current': total_scenes, 'total': total_scenes, 'percentage': 95}, ensure_ascii=False)}\n\n"

            result_data = {
                "type": "result",
                "success": True,
                "keywords": list(result_map.values()),
                "total": len(result_map),
                "mode": mode_label,
            }
            yield f"event: result\ndata: {json_module.dumps(result_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            print(f"[SceneKeywords] Error: {e}")
            print(traceback.format_exc())
            yield f"event: error\ndata: {json_module.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _empty_result(scene_id: int, gen_image: bool, gen_video: bool) -> dict:
    """Helper to create empty result entry."""
    entry = {'scene_id': scene_id, 'keyword': ''}
    if gen_image:
        entry['image_prompt'] = ''
    if gen_video:
        entry['video_prompt'] = ''
    return entry


# ═══════════════════════════════════════════════════════════════════════════════
# VIDEO PROMPT PIPELINE (5-Step Sequential)
# ═══════════════════════════════════════════════════════════════════════════════


# ── Step 1: Analyze Video Direction ──

class VideoDirectionSceneItem(BaseModel):
    scene_id: int
    content: str

class AnalyzeVideoDirectionRequest(BaseModel):
    scenes: List[VideoDirectionSceneItem]
    language: Optional[str] = 'vi'
    model: Optional[str] = None
    prompt_style: Optional[str] = None
    main_character: Optional[str] = None
    context_description: Optional[str] = None
    sync_analysis: Optional[Dict[str, Any]] = None


@router.post("/analyze-video-direction")
async def analyze_video_direction(request: AnalyzeVideoDirectionRequest):
    """
    Step 1: Analyze text script and create video direction notes per scene.
    Uses the Scene Builder methodology (6 pillars: Subject, Action, Environment, Camera, Lighting, Audio).
    Automatically batches large scene lists (>50 scenes) to avoid token limits and quality degradation.
    """
    if not request.scenes:
        raise HTTPException(status_code=400, detail="Không có scene nào")

    BATCH_SIZE = 50  # Max scenes per AI call

    async def event_generator():
        try:
            ai_client = get_configured_ai_client(model=request.model)
            loop = asyncio.get_event_loop()
            import concurrent.futures
            import re as re_mod

            lang_name = LANG_NAME_MAP.get(request.language, 'the same language as the scenes')

            total = len(request.scenes)

            # Split scenes into batches
            batches = [request.scenes[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
            num_batches = len(batches)

            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Đạo diễn: {total} scenes ({num_batches} batch)', 'percentage': 5}, ensure_ascii=False)}\n\n"

            # Build style block once (shared across all batches)
            style_block = ""
            if request.prompt_style:
                style_block += f"\n══ VISUAL STYLE DIRECTION ══\n{request.prompt_style}\n"
            if request.main_character:
                style_block += f"\n══ MAIN CHARACTER ══\n{request.main_character}\n"
            if request.context_description:
                style_block += f"\n══ ENVIRONMENT/CONTEXT ══\n{request.context_description}\n"
            if request.sync_analysis:
                sa = request.sync_analysis
                sync_parts = []
                if sa.get('characters'):
                    chars = "\n".join([f"  - {c.get('name', '')}: {c.get('visual_description', c.get('description', ''))}" for c in sa['characters'][:5]])
                    sync_parts.append(f"SYNC CHARACTERS (maintain consistency):\n{chars}")
                if sa.get('settings'):
                    sets = "\n".join([f"  - {s.get('name', '')}: {s.get('visual_description', s.get('description', ''))}" for s in sa['settings'][:5]])
                    sync_parts.append(f"SYNC SETTINGS (maintain consistency):\n{sets}")
                if sa.get('visual_style'):
                    sync_parts.append(f"SYNC VISUAL STYLE: {sa['visual_style']}")
                if sync_parts:
                    style_block += "\n══ SYNC ANALYSIS (follow these constraints) ══\n" + "\n".join(sync_parts) + "\n"

            all_directions = []

            for batch_idx, batch_scenes in enumerate(batches):
                batch_num = batch_idx + 1
                batch_total = len(batch_scenes)
                batch_start_pct = 10 + int((batch_idx / num_batches) * 75)
                batch_end_pct = 10 + int(((batch_idx + 1) / num_batches) * 75)

                yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Batch {batch_num}/{num_batches}: {batch_total} scenes', 'percentage': batch_start_pct}, ensure_ascii=False)}\n\n"

                scenes_block = "\n".join([
                    f"Scene {s.scene_id}: {s.content}" for s in batch_scenes
                ])

                prompt = f"""You are an expert VIDEO DIRECTOR converting a text script into a video script with directing notes.
The script is in {lang_name}. Your output must be in English.

══ SCENE BUILDER METHODOLOGY (6 PILLARS) ══
For each scene, you must decompose the text into 6 technical elements:
1. SUBJECT: Who is the center? Identity, age, physical features, clothing, distinguishing marks.
2. ACTION: What specific action? One primary action per scene. Avoid abstract verbs.
3. ENVIRONMENT: Where? Time of day? Weather? Spatial details.
4. CAMERA: Shot size (Wide/Medium/Close-up/ECU), movement (Pan/Tilt/Dolly/Tracking), lens (35mm/85mm).
5. LIGHTING: Light source, quality (Volumetric/Rim/High-contrast/Soft), color temperature.
6. AUDIO: Dialogue (in quotes), SFX, ambient sounds, background music mood.

══ EMOTION MAPPING ══
Translate emotions to visual parameters:
- Positive (Romance/Joy): Golden hour warm light, warm tones, symmetrical composition
- Negative (Sadness/Loneliness): Blue hour cold light, cool tones, distance shots, slow zoom
- Dramatic (Mystery/Tension): High contrast, deep shadows (Film Noir), side lighting

══ RULES ══
- Each scene should be 4-8 seconds of video
- One primary action OR one camera movement per scene
- Decompose complex actions into multiple shots
{style_block}
══ SCENES TO ANALYZE ({batch_total} scenes, batch {batch_num}/{num_batches}) ══
{scenes_block}

Return EXACTLY {batch_total} scene blocks in this format (NO JSON, plain text paragraphs):

===SCENE 1===
A cinematic medium shot of a young woman in a red dress walking through a sunlit garden, warm golden hour lighting casting long shadows, camera slowly dollying forward on 35mm lens, birds chirping in background with soft ambient music...

===SCENE 2===
...

Return ONLY the scene blocks with ===SCENE N=== separators, no other text."""

                yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Batch {batch_num}/{num_batches}: AI phân tích...', 'percentage': batch_start_pct + 5}, ensure_ascii=False)}\n\n"

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    response_text = await loop.run_in_executor(
                        executor,
                        lambda p=prompt: ai_client.generate(p)
                    )

                yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Batch {batch_num}/{num_batches}: xử lý kết quả...', 'percentage': batch_end_pct - 5}, ensure_ascii=False)}\n\n"

                # Parse paragraph separator format: ===SCENE N===\nparagraph...
                scene_blocks = re_mod.split(r'===SCENE\s+(\d+)===', response_text)
                batch_directions = []
                if len(scene_blocks) >= 3:
                    for i in range(1, len(scene_blocks), 2):
                        try:
                            scene_id = int(scene_blocks[i])
                        except (ValueError, IndexError):
                            continue
                        block = scene_blocks[i + 1].strip() if i + 1 < len(scene_blocks) else ''
                        batch_directions.append({"scene_id": scene_id, "direction_notes": block})
                else:
                    # Fallback: try JSON parsing
                    json_match = re_mod.search(r'\[.*\]', response_text, re_mod.DOTALL)
                    if json_match:
                        batch_directions = json_module.loads(json_match.group())
                    else:
                        batch_directions = json_module.loads(response_text)

                all_directions.extend(batch_directions)
                print(f"[VideoDirection] Batch {batch_num}/{num_batches}: parsed {len(batch_directions)} directions (running total: {len(all_directions)}/{total})")

            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Xong: {len(all_directions)}/{total} scenes', 'percentage': 90}, ensure_ascii=False)}\n\n"

            result_data = {
                "type": "result",
                "success": True,
                "directions": all_directions,
                "total": len(all_directions),
            }
            yield f"event: result\ndata: {json_module.dumps(result_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            print(f"[VideoDirection] Error: {e}")
            print(traceback.format_exc())
            yield f"event: error\ndata: {json_module.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


# ── Generate Video Prompts (dedicated endpoint) ──

class VideoPromptSceneItem(BaseModel):
    scene_id: int
    content: str
    direction_notes: Optional[str] = None
    audio_duration: Optional[float] = None

class GenerateVideoPromptsRequest(BaseModel):
    scenes: List[VideoPromptSceneItem]
    language: Optional[str] = 'vi'
    model: Optional[str] = None
    prompt_style: Optional[str] = None
    main_character: Optional[str] = None
    context_description: Optional[str] = None
    video_prompt_mode: Optional[str] = None
    sync_analysis: Optional[Dict[str, Any]] = None


@router.post("/generate-video-prompts")
async def generate_video_prompts_endpoint(request: GenerateVideoPromptsRequest):
    """
    Generate video prompts for each scene using the 7-component framework.
    Input: scenes with direction notes from analyze-video-direction.
    Output: per-scene video prompts (80-120 words each).
    """
    if not request.scenes:
        raise HTTPException(status_code=400, detail="No scenes provided")

    BATCH_SIZE = 20

    async def event_generator():
        try:
            ai_client = get_configured_ai_client(model=request.model)
            loop = asyncio.get_event_loop()
            import concurrent.futures
            import re as re_mod

            lang_name = LANG_NAME_MAP.get(request.language, 'the same language as the scenes')

            total = len(request.scenes)
            batches = [request.scenes[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
            num_batches = len(batches)

            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Video prompts: {total} scenes', 'percentage': 5}, ensure_ascii=False)}\n\n"

            # Build style/consistency block
            style_block = ""
            if request.prompt_style:
                style_block += f"\n== VISUAL STYLE DIRECTION ==\n{request.prompt_style}\n"
            if request.main_character:
                style_block += f"\n== MAIN CHARACTER (consistent in ALL scenes) ==\n{request.main_character}\n"
            if request.context_description:
                style_block += f"\n== ENVIRONMENT/CONTEXT ==\n{request.context_description}\n"
            if request.sync_analysis:
                sa = request.sync_analysis
                sync_parts = []
                if sa.get('characters'):
                    chars = "\n".join([f"  - {c.get('name', '')}: {c.get('visual_description', c.get('description', ''))}" for c in sa['characters'][:5]])
                    sync_parts.append(f"SYNC CHARACTERS:\n{chars}")
                if sa.get('settings'):
                    sets = "\n".join([f"  - {s.get('name', '')}: {s.get('visual_description', s.get('description', ''))}" for s in sa['settings'][:5]])
                    sync_parts.append(f"SYNC SETTINGS:\n{sets}")
                if sa.get('visual_style'):
                    sync_parts.append(f"SYNC VISUAL STYLE: {sa['visual_style']}")
                if sync_parts:
                    style_block += "\n== SYNC ANALYSIS ==\n" + "\n".join(sync_parts) + "\n"

            mode_block = ""
            if request.video_prompt_mode == 'character_sync':
                mode_block = "\n== MODE: CHARACTER SYNC ==\nRepeat full character description in EVERY prompt.\n"
            elif request.video_prompt_mode == 'scene_sync':
                mode_block = "\n== MODE: STYLE SYNC ==\nMaintain identical color grading, lighting, camera language across ALL scenes.\n"
            elif request.video_prompt_mode == 'full_sync':
                mode_block = "\n== MODE: FULL SYNC ==\nCharacter identity + Visual style + Environment must ALL remain consistent.\n"

            all_results = {}

            for batch_idx, batch_scenes in enumerate(batches):
                batch_num = batch_idx + 1
                batch_total = len(batch_scenes)
                batch_start_pct = 10 + int((batch_idx / num_batches) * 75)
                batch_end_pct = 10 + int(((batch_idx + 1) / num_batches) * 75)

                if num_batches > 1:
                    yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Batch {batch_num}/{num_batches}: {batch_total} scenes', 'percentage': batch_start_pct}, ensure_ascii=False)}\n\n"

                scenes_block_parts = []
                for s in batch_scenes:
                    line = f"Scene {s.scene_id}: {s.content}"
                    if s.direction_notes:
                        line += f"\n  [DIRECTION]: {s.direction_notes}"
                    scenes_block_parts.append(line)
                scenes_block = "\n".join(scenes_block_parts)

                prompt = f"""You are an expert VIDEO PROMPT WRITER for Veo 3.1 — a reasoning-based generative AI that understands physics, cinematography, and narrative logic. Generate a video generation prompt for each scene.
The script is in {lang_name}. All prompts must be in ENGLISH.

== UNIVERSAL 7-COMPONENT VIDEO PROMPTING FRAMEWORK ==
Combine ALL 7 components into ONE FLOWING NARRATIVE PARAGRAPH per scene.
NEVER use tag-soup, bullet points, or comma-separated keywords — use natural language with cause-and-effect reasoning.

1. SUBJECT (Who/What — the visual anchor):
   - Identity: name, age, gender, build, ethnicity
   - Physical details: face shape, eye color, hair (color/length/style/texture), skin tone, distinguishing marks (scars, tattoos)
   - Wardrobe: specific clothing, color palette, accessories (glasses, jewelry)
   - Expression/Posture: emotional state that influences body language
   - For recurring characters: repeat the FULL description in EVERY prompt for identity consistency

2. CONTEXT (Where — environment + light source):
   - Location: specific setting (not just "a room" but "a Victorian study bathed in afternoon sunlight")
   - Time of day + weather: affects lighting calculations
   - Light source: describe WHERE light comes from (window, neon sign, campfire) — Veo uses this to compute shadows and volumetric effects
   - Spatial relationships: foreground/midground/background layers

3. ACTION (What happens — verbs + physics):
   - Use movement verbs: "sprints", "stumbles", "lunges", "drifts"
   - Cause-and-effect interactions: "She flinches as the glass shatters" (triggers temporal reasoning)
   - Physical interactions: describe material behavior (water splashing, cloth billowing, dust rising)

4. CINEMATOGRAPHY (How — camera as storytelling tool):
   - Shot type: ECU (extreme detail), CU (emotion), MS (dialogue), WS (environment), Establishing (scale)
   - Lens: 35mm (natural/human eye), 85mm (portrait/flattened BG), macro (extreme detail), fisheye (dynamic distortion)
   - Camera movement (pick ONE that serves the narrative):
     * Dolly in/out: physically moves camera, changes perspective (intimacy/isolation)
     * Truck/Track left/right: follows subject movement laterally
     * Pan/Tilt: rotates on fixed axis, reveals environment
     * Crane up/down: vertical reveal, shows scale
     * Orbit/Arc: circles subject (hero shot emphasis)
     * Handheld: simulates realistic camera shake (chaos/urgency)
   - Advanced: Rack focus (shift focus foreground↔background), Bullet time (slow-mo + camera movement)

5. AESTHETICS (Feel — render engine + mood):
   - Style: photorealistic, cinematic, 3D render, anime (specify studio), oil painting
   - Lighting technique: golden hour, blue hour, noir (high contrast), softbox, volumetric/god rays, Rembrandt, rim light
   - Color palette: specific tones (warm amber, desaturated teal, neon cyan-magenta)
   - Mood/atmosphere: tension, serenity, melancholy, wonder

6. AUDIO (Soundscape — describe QUALITY not just names):
   - Dialogue: use direct quotes with emotional tone ("he whispers 'We need to leave, now'" — triggers lip-sync)
   - SFX: describe texture and quality ("the sharp crack of a branch snapping", "the wet slap of footsteps on marble")
   - Ambience: layered background ("distant traffic hum beneath the patter of rain on tin roofing")

7. CONSTRAINTS (Guardrails):
   - Aspect ratio: 16:9 for cinematic, 9:16 for social
   - Negative: "no text overlays, no watermarks, no extra limbs, no floating objects, no blurry faces"

CRITICAL RULES:
- Output as ONE FLOWING NARRATIVE PARAGRAPH — weave all 7 components naturally
- Each prompt: 80-120 words STRICTLY
- Use the [DIRECTION] notes to guide your visual decisions for each scene
- Maintain CHARACTER identity and SETTING consistency across ALL scenes
- Describe light SOURCES (not just "good lighting") so Veo can compute shadows
- Use cause-and-effect language to trigger Veo's temporal reasoning engine
{style_block}{mode_block}
== SCENES ({batch_total} scenes) ==
{scenes_block}

Return EXACTLY {batch_total} scene blocks:

===SCENE 1===
VIDEO_PROMPT: A cinematic medium shot of...

===SCENE 2===
VIDEO_PROMPT: ...

Return ONLY the scene blocks, no other text."""

                yield f"data: {json_module.dumps({'type': 'progress', 'message': 'AI generating video prompts...', 'percentage': batch_start_pct + 5}, ensure_ascii=False)}\n\n"

                try:
                    def call_ai(p=prompt):
                        return ai_client.generate(p, temperature=0.3)

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        result_text = await loop.run_in_executor(pool, call_ai)

                    print(f"[VideoPrompts] Batch {batch_num}/{num_batches}: AI response {len(result_text)} chars")

                    scene_blocks = re_mod.split(r'===SCENE\s+(\d+)===', result_text)
                    parsed_count = 0
                    if len(scene_blocks) >= 3:
                        for i in range(1, len(scene_blocks), 2):
                            try:
                                scene_id = int(scene_blocks[i])
                            except (ValueError, IndexError):
                                continue
                            block = scene_blocks[i + 1] if i + 1 < len(scene_blocks) else ''
                            vp_match = re_mod.search(r'VIDEO_PROMPT:\s*(.+?)(?=\n(?:===SCENE)|$)', block, re_mod.DOTALL)
                            video_prompt = vp_match.group(1).strip() if vp_match else block.strip()
                            if video_prompt:
                                all_results[scene_id] = {'scene_id': scene_id, 'video_prompt': video_prompt}
                                parsed_count += 1

                    print(f"[VideoPrompts] Batch {batch_num}/{num_batches}: parsed {parsed_count}/{batch_total} (total: {len(all_results)}/{total})")

                    # Retry missing scenes
                    missing = [s for s in batch_scenes if s.scene_id not in all_results]
                    if missing and len(missing) < batch_total:
                        print(f"[VideoPrompts] Retrying {len(missing)} missing scenes...")
                        retry_scenes = "\n".join([
                            f"Scene {s.scene_id}: {s.content}" + (f"\n  [DIRECTION]: {s.direction_notes}" if s.direction_notes else "")
                            for s in missing
                        ])
                        retry_prompt = f"""Generate video prompts for these {len(missing)} scenes. 80-120 words each, ONE FLOWING PARAGRAPH in English.
{style_block}
{retry_scenes}

===SCENE N===
VIDEO_PROMPT: ..."""
                        try:
                            def call_retry(p=retry_prompt):
                                return ai_client.generate(p, temperature=0.3)
                            with concurrent.futures.ThreadPoolExecutor() as pool:
                                retry_text = await loop.run_in_executor(pool, call_retry)
                            retry_blocks = re_mod.split(r'===SCENE\s+(\d+)===', retry_text)
                            retry_ok = 0
                            for ri in range(1, len(retry_blocks), 2):
                                try:
                                    rsid = int(retry_blocks[ri])
                                    rblock = retry_blocks[ri + 1] if ri + 1 < len(retry_blocks) else ''
                                    rvp = re_mod.search(r'VIDEO_PROMPT:\s*(.+?)(?=\n(?:===SCENE)|$)', rblock, re_mod.DOTALL)
                                    rvideo = rvp.group(1).strip() if rvp else rblock.strip()
                                    if rvideo:
                                        all_results[rsid] = {'scene_id': rsid, 'video_prompt': rvideo}
                                        retry_ok += 1
                                except (ValueError, IndexError):
                                    pass
                            print(f"[VideoPrompts] Retry recovered {retry_ok}/{len(missing)}")
                        except Exception as retry_err:
                            print(f"[VideoPrompts] Retry failed: {retry_err}")

                except Exception as ai_err:
                    print(f"[VideoPrompts] Batch {batch_num} error: {ai_err}")

                yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Batch {batch_num}/{num_batches}: done', 'percentage': batch_end_pct}, ensure_ascii=False)}\n\n"

            # Fill missing with empty
            for s in request.scenes:
                if s.scene_id not in all_results:
                    all_results[s.scene_id] = {'scene_id': s.scene_id, 'video_prompt': ''}

            result_list = sorted(all_results.values(), key=lambda x: x['scene_id'])
            ok_count = sum(1 for r in result_list if r['video_prompt'])
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Done: {ok_count}/{total} prompts', 'percentage': 95}, ensure_ascii=False)}\n\n"

            result_data = {
                "type": "result",
                "success": True,
                "video_prompts": result_list,
                "total": len(result_list),
            }
            yield f"event: result\ndata: {json_module.dumps(result_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            print(f"[VideoPrompts] Error: {e}")
            print(traceback.format_exc())
            yield f"event: error\ndata: {json_module.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


# ── Step 2: Extract Entities (Characters, Settings, Props appearing ≥2 times) ──

class ExtractEntitiesRequest(BaseModel):
    video_prompts: List[Dict[str, Any]]  # [{scene_id, video_prompt, direction_notes?}]
    language: Optional[str] = 'vi'
    model: Optional[str] = None
    script_scenes: Optional[List[Dict[str, Any]]] = None  # Original script scenes for name extraction


@router.post("/extract-entities")
async def extract_entities(request: ExtractEntitiesRequest):
    """
    Step 3: Scan all video prompts and extract characters, settings, props
    that appear 2+ times. Assign a single-word name (min 3 chars) from the script.
    """
    if not request.video_prompts:
        raise HTTPException(status_code=400, detail="Không có video prompts")

    async def event_generator():
        try:
            ai_client = get_configured_ai_client(model=request.model)
            loop = asyncio.get_event_loop()
            import concurrent.futures

            total = len(request.video_prompts)
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Trích xuất entities: {total} prompts', 'percentage': 5}, ensure_ascii=False)}\n\n"

            prompts_block = "\n".join([
                f"Scene {p.get('scene_id', i+1)}: {p.get('video_prompt', p.get('direction_notes', ''))}"
                for i, p in enumerate(request.video_prompts)
            ])

            # Include original script text for name extraction
            script_block = ""
            if request.script_scenes:
                script_block = "\n══ ORIGINAL SCRIPT (for extracting names) ══\n" + "\n".join([
                    f"Scene {s.get('scene_id', i+1)}: {s.get('content', '')}"
                    for i, s in enumerate(request.script_scenes)
                ]) + "\n"

            prompt = f"""You are an entity extraction specialist for video production.

Analyze ALL the video prompts below and identify recurring entities that appear in 2 or MORE scenes.

ENTITY TYPES:
1. **character** — People, animals, recurring figures
2. **environment** — Locations, settings, rooms, landscapes
3. **prop** — Objects, tools, vehicles, items

NAMING RULES:
- Extract the name from the original script text below (use a single word, minimum 3 characters)
- If no name exists in the script, create a descriptive English name (min 3 chars)
- Names must be unique, short, and recognizable
- Format: CamelCase, e.g. "Minh", "Office", "RedCar", "Beach"
{script_block}
══ VIDEO PROMPTS ({total} scenes) ══
{prompts_block}

══ OUTPUT FORMAT ══
Return a JSON object:
{{
  "entities": [
    {{
      "name": "EntityName",
      "type": "character|environment|prop",
      "description": "Detailed visual description used consistently across scenes",
      "scene_ids": [1, 3, 5],
      "count": 3
    }}
  ]
}}

RULES:
- ONLY include entities appearing in 2+ scenes
- Each entity must have a detailed visual description
- For characters: include age, gender, hair, skin, distinguishing features
- For environments: include spatial details, lighting, atmosphere
- For props: include color, size, material, distinctive features
- Sort by count (most frequent first)

Return ONLY the JSON object, no other text."""

            yield f"data: {json_module.dumps({'type': 'progress', 'message': 'AI phân tích entities...', 'percentage': 30}, ensure_ascii=False)}\n\n"

            with concurrent.futures.ThreadPoolExecutor() as executor:
                response_text = await loop.run_in_executor(
                    executor,
                    lambda: ai_client.generate(prompt)
                )

            yield f"data: {json_module.dumps({'type': 'progress', 'message': 'Xử lý kết quả...', 'percentage': 80}, ensure_ascii=False)}\n\n"

            import re as re_mod
            json_match = re_mod.search(r'\{.*\}', response_text, re_mod.DOTALL)
            if json_match:
                entities_data = json_module.loads(json_match.group())
            else:
                entities_data = json_module.loads(response_text)

            entities = entities_data.get('entities', [])

            # Validate min 3 chars for names
            for entity in entities:
                if len(entity.get('name', '')) < 3:
                    entity['name'] = entity.get('name', 'Ent') + 'Ref'

            result_data = {
                "type": "result",
                "success": True,
                "entities": entities,
                "total": len(entities),
            }
            yield f"event: result\ndata: {json_module.dumps(result_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            print(f"[ExtractEntities] Error: {e}")
            print(traceback.format_exc())
            yield f"event: error\ndata: {json_module.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


# ── Step 4: Generate Reference Image Prompts (VEO3 methodology) ──

class GenerateReferencePromptsRequest(BaseModel):
    entities: List[Dict[str, Any]]  # [{name, type, description, ...}]
    model: Optional[str] = None
    prompt_style: Optional[str] = None
    sync_analysis: Optional[Dict[str, Any]] = None  # From metadata style analysis


@router.post("/generate-reference-prompts")
async def generate_reference_prompts(request: GenerateReferencePromptsRequest):
    """
    Step 4: Generate multi-panel reference sheet prompts for each entity.
    - Characters: 1 prompt → 3-panel sheet (front + three-quarter + profile) on white background
    - Environments: 1 prompt → 2-panel sheet (establishing + detail close-up)
    - Props: 1 prompt → 2-panel sheet (full product + macro detail)
    Output has 2 parts: entity names list + reference prompts.
    """
    if not request.entities:
        raise HTTPException(status_code=400, detail="Không có entities")

    async def event_generator():
        try:
            ai_client = get_configured_ai_client(model=request.model)
            loop = asyncio.get_event_loop()
            import concurrent.futures

            total = len(request.entities)
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Tạo reference: {total} entities', 'percentage': 5}, ensure_ascii=False)}\n\n"

            # Build entity descriptions
            entities_block = ""
            for e in request.entities:
                entities_block += f"- [{e['name']}] (type: {e['type']}): {e.get('description', '')}\n"

            # Sync analysis context
            sync_block = ""
            if request.sync_analysis:
                sa = request.sync_analysis
                if sa.get('characters'):
                    chars = ", ".join([c.get('name', '') for c in sa['characters'][:5]])
                    sync_block += f"\nSYNC ANALYSIS CHARACTERS: {chars}\n"
                if sa.get('settings'):
                    sets = ", ".join([s.get('name', '') for s in sa['settings'][:5]])
                    sync_block += f"SYNC ANALYSIS SETTINGS: {sets}\n"
                if sa.get('visual_style'):
                    sync_block += f"SYNC ANALYSIS VISUAL STYLE: {sa['visual_style']}\n"

            style_block = ""
            if request.prompt_style:
                style_block = f"\n══ VISUAL STYLE TO APPLY ══\n{request.prompt_style}\n"

            prompt = f"""You are a VEO 3.1 Reference Image Specialist.
Generate ONE single multi-panel reference sheet prompt per entity. Each prompt describes a SINGLE IMAGE containing multiple panels/views arranged side by side.
{sync_block}{style_block}
══ ENTITIES ══
{entities_block}

══ MULTI-PANEL REFERENCE SHEET RULES ══

FOR CHARACTERS (type=character):
Generate 1 prompt describing a 3-panel reference sheet in ONE image:
"A professional character reference sheet on a pure white background, divided into three equal panels arranged horizontally. LEFT PANEL: front-facing portrait of [FULL DESCRIPTION], facing directly toward the camera, neutral expression, eyes looking straight into the lens, [CLOTHING], full visible face with no obstructions. CENTER PANEL: three-quarter view of the same [CHARACTER], turned approximately 45 degrees to the right, showing depth and volume of the face, the transition between nose bridge and cheekbone clearly visible, ear partially visible, same [CLOTHING]. RIGHT PANEL: side profile of the same [CHARACTER], facing 90 degrees to the right, showing full silhouette, clear definition of chin projection, nose shape, and hair thickness. All three panels share identical soft diffused studio lighting, no harsh shadows, 4K resolution, sharp details, professional quality, consistent appearance across all panels."

FOR ENVIRONMENTS (type=environment):
Generate 1 prompt describing a 2-panel reference sheet:
"A cinematic environment reference sheet divided into two panels. LEFT PANEL: wide establishing shot of [DETAILED ENVIRONMENT], [TIME OF DAY] lighting with [LIGHT DESCRIPTION], shot on 35mm wide-angle lens, [COLOR GRADE], 16:9 widescreen, no people. RIGHT PANEL: detail close-up crop of a key architectural or textural element from the same environment, showing surface materials and lighting interaction. Both panels share consistent color grading and atmosphere, 4K quality."

FOR PROPS (type=prop):
Generate 1 prompt describing a 2-panel reference sheet:
"A professional product reference sheet on a pure white background, divided into two panels. LEFT PANEL: full product shot of [DETAILED PROP DESCRIPTION], soft studio lighting from above and both sides, no harsh shadows, clean composition. RIGHT PANEL: macro close-up detail shot of the same [PROP] showing surface texture, material quality, and fine details. Shot on 100mm macro lens, sharp details, 4K quality, consistent lighting across both panels."

══ WORD COUNT LIMIT ══
Each reference sheet prompt must be 60-100 words. Be precise — every word must add visual information.

══ OUTPUT FORMAT ══
Return a JSON object:
{{
  "entities_header": "[Name1], [Name2], [Name3], ...",
  "reference_prompts": [
    {{
      "entity_name": "EntityName",
      "entity_type": "character|environment|prop",
      "prompts": [
        {{"angle": "REFERENCE_SHEET", "prompt": "The full multi-panel reference sheet prompt..."}}
      ]
    }}
  ]
}}

Each entity has EXACTLY 1 prompt with angle "REFERENCE_SHEET". The prompt describes ALL panels within ONE single image.

Return ONLY the JSON object, no other text."""

            yield f"data: {json_module.dumps({'type': 'progress', 'message': 'AI tạo reference prompts...', 'percentage': 30}, ensure_ascii=False)}\n\n"

            with concurrent.futures.ThreadPoolExecutor() as executor:
                response_text = await loop.run_in_executor(
                    executor,
                    lambda: ai_client.generate(prompt)
                )

            yield f"data: {json_module.dumps({'type': 'progress', 'message': 'Xử lý kết quả...', 'percentage': 85}, ensure_ascii=False)}\n\n"

            import re as re_mod
            json_match = re_mod.search(r'\{.*\}', response_text, re_mod.DOTALL)
            if json_match:
                ref_data = json_module.loads(json_match.group())
            else:
                ref_data = json_module.loads(response_text)

            result_data = {
                "type": "result",
                "success": True,
                "entities_header": ref_data.get('entities_header', ''),
                "reference_prompts": ref_data.get('reference_prompts', []),
                "total": len(ref_data.get('reference_prompts', [])),
            }
            yield f"event: result\ndata: {json_module.dumps(result_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            print(f"[ReferencePrompts] Error: {e}")
            print(traceback.format_exc())
            yield f"event: error\ndata: {json_module.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


# ── Step 5: Generate Scene Builder Prompts (inject [Name] references) ──

class GenerateSceneBuilderPromptsRequest(BaseModel):
    video_prompts: List[Dict[str, Any]]  # [{scene_id, video_prompt}]
    entities: List[Dict[str, Any]]  # [{name, type, description, scene_ids}]
    directions: Optional[List[Dict[str, Any]]] = None  # From step 1
    model: Optional[str] = None
    prompt_style: Optional[str] = None
    sync_analysis: Optional[Dict[str, Any]] = None


@router.post("/generate-scene-builder-prompts")
async def generate_scene_builder_prompts(request: GenerateSceneBuilderPromptsRequest):
    """
    Step 5: Take video prompts + entity list, inject [Name] references
    to create Scene Builder prompts that link to reference images.
    """
    if not request.video_prompts:
        raise HTTPException(status_code=400, detail="Không có video prompts")

    async def event_generator():

        try:
            ai_client = get_configured_ai_client(model=request.model)
            loop = asyncio.get_event_loop()
            import concurrent.futures
            import re as re_mod

            total = len(request.video_prompts)
            yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Scene builder: {total} scenes', 'percentage': 5}, ensure_ascii=False)}\n\n"

            # Build entity reference map
            entity_names = ", ".join([f"[{e['name']}]" for e in request.entities])
            entity_descriptions = "\n".join([
                f"- [{e['name']}] ({e['type']}): {e.get('description', '')}"
                for e in request.entities
            ])

            # Build entity-to-scene mapping
            entity_scene_map = {}
            for e in request.entities:
                for sid in e.get('scene_ids', []):
                    if sid not in entity_scene_map:
                        entity_scene_map[sid] = []
                    entity_scene_map[sid].append(e['name'])

            # Include direction notes if available
            direction_block = ""
            if request.directions:
                direction_block = "\n══ DIRECTION NOTES ══\n" + "\n".join([
                    f"Scene {d.get('scene_id', 0)}: {d.get('direction_notes', '')}"
                    for d in request.directions
                ]) + "\n"

            style_block = ""
            if request.prompt_style:
                style_block = f"\n══ VISUAL STYLE ══\n{request.prompt_style}\n"

            sync_block = ""
            if request.sync_analysis:
                sa = request.sync_analysis
                sync_sb_parts = []
                if sa.get('characters'):
                    chars = "\n".join([f"  - {c.get('name', '')}: {c.get('visual_description', c.get('description', ''))}" for c in sa['characters'][:5]])
                    sync_sb_parts.append(f"SYNC CHARACTERS (maintain consistency):\n{chars}")
                if sa.get('settings'):
                    sets = "\n".join([f"  - {s.get('name', '')}: {s.get('visual_description', s.get('description', ''))}" for s in sa['settings'][:5]])
                    sync_sb_parts.append(f"SYNC SETTINGS (maintain consistency):\n{sets}")
                if sa.get('visual_style'):
                    sync_sb_parts.append(f"SYNC VISUAL STYLE: {sa['visual_style']}")
                if sync_sb_parts:
                    sync_block = "\n══ SYNC ANALYSIS (follow for consistency) ══\n" + "\n".join(sync_sb_parts) + "\n"

            # Batching: split into batches of 50 scenes
            BATCH_SIZE = 50
            scene_batches = [request.video_prompts[i:i + BATCH_SIZE] for i in range(0, total, BATCH_SIZE)]
            num_batches = len(scene_batches)
            all_results = []

            for batch_idx, batch_prompts in enumerate(scene_batches):
                batch_num = batch_idx + 1
                batch_count = len(batch_prompts)
                batch_start_pct = 10 + int(70 * batch_idx / num_batches)

                if num_batches > 1:
                    yield f"data: {json_module.dumps({'type': 'progress', 'message': f'Batch {batch_num}/{num_batches}: {batch_count} scenes', 'current': sum(len(b) for b in scene_batches[:batch_idx]), 'total': total, 'percentage': batch_start_pct}, ensure_ascii=False)}\n\n"

                # Build per-batch prompts block
                prompts_block = ""
                for p in batch_prompts:
                    sid = p.get('scene_id', 0)
                    entities_in_scene = entity_scene_map.get(sid, [])
                    entities_hint = f" (entities: {', '.join(['['+n+']' for n in entities_in_scene])})" if entities_in_scene else ""
                    prompts_block += f"Scene {sid}{entities_hint}: {p.get('video_prompt', '')}\n"

                prompt = f"""You are a Scene Builder IMAGE specialist for Google VEO 3.

Your task: Generate a SCENE IMAGE PROMPT for each scene that uses [Name] reference tokens for entities.
These are IMAGE prompts — describing a STATIC scene composition (not video). They serve as visual blueprints for VEO3 scene generation.

══ AVAILABLE ENTITY REFERENCES ══
{entity_names}

Entity details:
{entity_descriptions}
{direction_block}{style_block}{sync_block}
══ VIDEO PROMPTS (context for {batch_count} scenes{f', batch {batch_num}/{num_batches}' if num_batches > 1 else ''}) ══
{prompts_block}

══ SCENE BUILDER IMAGE PROMPT RULES ══
1. Generate an IMAGE prompt for each scene (STATIC composition, not video)
2. Use [Name] tokens to reference entities instead of full descriptions:
   - Character: "[MinhAnh] stands in front of..."
   - Environment: "in [Office], afternoon golden hour lighting..."
   - Prop: "[Journal] lies open on the table..."

3. Focus on STATIC image composition:
   - Pose, position, framing (not movement or camera motion)
   - Lighting, color palette, mood
   - Spatial arrangement of characters and props within the environment
   - Shot size: Wide/Medium/Close-up/ECU
   - Lens: 35mm/50mm/85mm

4. Each image prompt should capture the KEY VISUAL MOMENT of the scene
5. Write as ONE FLOWING PARAGRAPH — not bullet points or tags
6. All prompts MUST be in English
7. **WORD COUNT LIMIT: 40-60 words per scene builder prompt.** Be precise and dense — every word must add visual information.

══ OUTPUT FORMAT ══
Return EXACTLY {batch_count} scene blocks in this format (NO JSON, plain text only):

===SCENE 1===
SCENE_BUILDER_PROMPT: A cinematic medium close-up, shot on 35mm lens. [MinhAnh] sits at a desk in [Office], looking up from [Laptop] and smiling gently, soft golden hour light streaming through the window, warm color palette, shallow depth of field...

===SCENE 2===
SCENE_BUILDER_PROMPT: ...

Return ONLY the scene blocks, no other text."""

                batch_label = f' (batch {batch_num}/{num_batches})' if num_batches > 1 else ''
                yield f"data: {json_module.dumps({'type': 'progress', 'message': f'AI tạo scene builder{batch_label}...', 'percentage': batch_start_pct + 10}, ensure_ascii=False)}\n\n"

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    response_text = await loop.run_in_executor(
                        executor,
                        lambda p=prompt: ai_client.generate(p)
                    )

                # Parse paragraph separator format
                scene_blocks = re_mod.split(r'===SCENE\s+(\d+)===', response_text)
                parsed_count = 0

                if len(scene_blocks) >= 3:
                    for i in range(1, len(scene_blocks), 2):
                        try:
                            scene_id = int(scene_blocks[i])
                        except (ValueError, IndexError):
                            continue
                        block = scene_blocks[i + 1] if i + 1 < len(scene_blocks) else ''
                        sb_match = re_mod.search(r'SCENE_BUILDER_PROMPT:\s*(.+?)(?=\n===SCENE|$)', block, re_mod.DOTALL)
                        sb_prompt = sb_match.group(1).strip() if sb_match else block.strip()
                        all_results.append({
                            'scene_id': scene_id,
                            'scene_builder_prompt': sb_prompt
                        })
                        parsed_count += 1

                # Fallback: try JSON parsing if separator format failed
                if parsed_count == 0:
                    print(f"[SceneBuilder] Separator format not found, trying JSON fallback...")
                    json_match = re_mod.search(r'\[.*\]', response_text, re_mod.DOTALL)
                    if json_match:
                        try:
                            parsed = json_module.loads(json_match.group())
                            if isinstance(parsed, list):
                                all_results.extend(parsed)
                                parsed_count = len(parsed)
                        except json_module.JSONDecodeError:
                            pass

                print(f"[SceneBuilder] {'Batch ' + str(batch_num) + ': ' if num_batches > 1 else ''}parsed {parsed_count} scenes (total: {len(all_results)}/{total})")

            yield f"data: {json_module.dumps({'type': 'progress', 'message': 'Xử lý kết quả...', 'percentage': 90}, ensure_ascii=False)}\n\n"

            result_data = {
                "type": "result",
                "success": True,
                "scene_builder_prompts": all_results,
                "total": len(all_results),
            }
            yield f"event: result\ndata: {json_module.dumps(result_data, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            print(f"[SceneBuilder] Error: {e}")
            print(traceback.format_exc())
            yield f"event: error\ndata: {json_module.dumps({'success': False, 'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SSE STREAMING ENDPOINTS - Real-time progress
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/analyze-to-style-a-stream")
async def analyze_to_style_a_stream(request: AnalyzeToStyleARequest):
    """
    SSE streaming endpoint for StyleA analysis.
    Sends real-time progress events to the frontend.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    if not request.scripts or len(request.scripts) < 1:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 kịch bản mẫu")
    
    if len(request.scripts) > 20:
        raise HTTPException(status_code=400, detail="Tối đa 20 kịch bản mẫu")
    
    for i, script in enumerate(request.scripts):
        if len(script.strip()) < 50:
            raise HTTPException(status_code=400, detail=f"Kịch bản #{i+1} cần ít nhất 50 ký tự")
    
    progress_queue: asyncio.Queue = asyncio.Queue()
    main_loop = asyncio.get_running_loop()
    
    def progress_callback(step: str, percentage: int, message: str):
        """Thread-safe callback that puts progress into the async queue"""
        main_loop.call_soon_threadsafe(
            progress_queue.put_nowait,
            {"step": step, "percentage": percentage, "message": message}
        )
    
    async def event_generator():
        try:
            ai_client = get_configured_ai_client(model=request.model)
            analyzer = ConversationStyleAnalyzer(ai_client)
            
            loop = asyncio.get_event_loop()
            
            # ── PRE-TRANSLATION: Translate scripts to output language if needed ──
            scripts_to_analyze = list(request.scripts)
            output_lang = request.output_language.strip()
            
            if output_lang:
                # Auto-detect input language from first script
                detected_input = _detect_language(request.scripts[0])
                
                if detected_input != output_lang:
                    lang_names = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "es": "Spanish", "fr": "French", "th": "Thai", "de": "German", "pt": "Portuguese", "ru": "Russian"}
                    src_name = lang_names.get(detected_input, detected_input)
                    out_name = lang_names.get(output_lang, output_lang)
                    
                    progress_callback("translate", 2, f"Đang dịch {len(scripts_to_analyze)} script {src_name} → {out_name}...")
                    
                    translated_scripts = []
                    for i, script in enumerate(scripts_to_analyze):
                        try:
                            translate_prompt = f"""You are a professional translator. Translate the following script from {src_name} to {out_name}.

Rules:
- Preserve the STRUCTURE (paragraphs, line breaks) exactly.
- Prioritize NATURAL, fluent {out_name} over rigid literal translation.
- Adapt idioms and cultural references to feel natural in {out_name}.
- Keep proper nouns and technical terms unchanged.
- Output ONLY the translated text, no commentary.

--- SCRIPT ---
{script}
--- END ---

Translated {out_name} script:"""
                            translated = await loop.run_in_executor(
                                None,
                                lambda p=translate_prompt: ai_client.generate(p, temperature=0.3)
                            )
                            if translated and len(translated.strip()) > 50:
                                translated_scripts.append(translated.strip())
                            else:
                                translated_scripts.append(script)  # fallback
                        except Exception as e:
                            import logging
                            logging.getLogger(__name__).warning(f"Translation failed for script {i+1}: {e}")
                            translated_scripts.append(script)  # fallback
                        
                        progress_callback("translate", 2 + int(8 * (i + 1) / len(scripts_to_analyze)), f"Đã dịch {i+1}/{len(scripts_to_analyze)} script")
                    
                    scripts_to_analyze = translated_scripts
                    progress_callback("translate_done", 10, f"Đã dịch xong {len(translated_scripts)} script sang {out_name}")
            
            # Run analysis in thread with progress callback
            task = loop.run_in_executor(
                None,
                lambda: analyzer.analyze_to_style_a(
                    scripts_to_analyze, 
                    progress_callback=progress_callback,
                    analysis_language=request.analysis_language
                )
            )
            
            # Yield progress events while waiting for completion
            while not task.done():
                try:
                    progress = await asyncio.wait_for(progress_queue.get(), timeout=1.0)
                    yield f"data: {json_module.dumps(progress, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    yield f": heartbeat\n\n"
            
            # Drain remaining progress events
            while not progress_queue.empty():
                progress = progress_queue.get_nowait()
                yield f"data: {json_module.dumps(progress, ensure_ascii=False)}\n\n"
            
            # Get the result
            style_a, individual_analyses = task.result()
            
            # Send final result as a special event
            result_data = {
                "success": True,
                "style_a": style_a.to_dict(),
                "individual_analyses": individual_analyses,
                "scripts_analyzed": len(individual_analyses)
            }
            yield f"event: result\ndata: {json_module.dumps(result_data, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            error_data = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            yield f"event: error\ndata: {json_module.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/advanced-remake/full-pipeline-conversation-stream")
async def advanced_full_pipeline_conversation_stream(request: AdvancedFullPipelineConversationRequest):
    """
    SSE streaming endpoint for conversation-based pipeline.
    Sends real-time progress events as each step completes.
    """
    if not request.original_script or len(request.original_script.strip()) < 50:
        raise HTTPException(status_code=400, detail="Kịch bản gốc cần ít nhất 50 ký tự")
    
    progress_queue: asyncio.Queue = asyncio.Queue()
    main_loop = asyncio.get_running_loop()
    
    def progress_callback(step: str, percentage: int, message: str):
        """Thread-safe callback that puts progress into the async queue"""
        main_loop.call_soon_threadsafe(
            progress_queue.put_nowait,
            {"step": step, "percentage": percentage, "message": message}
        )
    
    async def event_generator():
        try:
            logger.info(f"[STREAM] Starting pipeline. Model={request.model}, script_len={len(request.original_script)}")
            ai_client = get_configured_ai_client(model=request.model)
            workflow = AdvancedRemakeWorkflow(ai_client)
            
            loop = asyncio.get_event_loop()
            
            # Run pipeline in thread with progress callback
            task = loop.run_in_executor(
                None,
                lambda: workflow.full_pipeline_conversation(
                    original_script=request.original_script,
                    target_word_count=request.target_word_count,
                    source_language=request.source_language,
                    language=request.language,
                    dialect=request.dialect,
                    channel_name=request.channel_name,
                    country=request.country,
                    add_quiz=request.add_quiz,
                    value_type=request.value_type,
                    storytelling_style=request.storytelling_style,
                    narrative_voice=request.narrative_voice,
                    custom_narrative_voice=request.custom_narrative_voice,
                    audience_address=request.audience_address,
                    custom_audience_address=request.custom_audience_address,
                    style_profile=request.style_profile,
                    custom_value=request.custom_value,
                    progress_callback=progress_callback
                )
            )
            
            # Yield progress events while waiting for completion
            while not task.done():
                try:
                    progress = await asyncio.wait_for(progress_queue.get(), timeout=2.0)
                    yield f"data: {json_module.dumps(progress, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    yield f": heartbeat\n\n"
            
            # Drain remaining progress events
            while not progress_queue.empty():
                progress = progress_queue.get_nowait()
                yield f"data: {json_module.dumps(progress, ensure_ascii=False)}\n\n"
            
            # Get the result (may raise if pipeline failed)
            results = task.result()
            
            # Build response same as original endpoint
            response_data = {
                "success": True,
                "final_script": results.get("final_script", ""),
                "word_count": results.get("word_count", 0)
            }
            
            if "original_analysis" in results:
                response_data["original_analysis"] = results["original_analysis"].to_dict() if hasattr(results["original_analysis"], "to_dict") else results["original_analysis"]
            if "structure_analysis" in results:
                response_data["structure_analysis"] = results["structure_analysis"].to_dict() if hasattr(results["structure_analysis"], "to_dict") else results["structure_analysis"]
            if "outline_a" in results:
                response_data["outline_a"] = results["outline_a"].to_dict() if hasattr(results["outline_a"], "to_dict") else results["outline_a"]
            if "draft_sections" in results:
                response_data["draft_sections"] = [d.to_dict() if hasattr(d, "to_dict") else d for d in results["draft_sections"]]
            if "refined_sections" in results:
                response_data["refined_sections"] = [r.to_dict() if hasattr(r, "to_dict") else r for r in results["refined_sections"]]
            
            logger.info(f"[STREAM] Pipeline complete! {response_data.get('word_count', 0)} words")
            yield f"event: result\ndata: {json_module.dumps(response_data, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            tb = traceback.format_exc()
            logger.error(f"[STREAM] Pipeline FAILED: {error_msg}")
            logger.error(f"[STREAM] Traceback:\n{tb}")
            error_data = {
                "success": False,
                "error": error_msg,
                "traceback": tb
            }
            yield f"event: error\ndata: {json_module.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ═══════════════════════════════════════════════════════════════════════════════
# YOUTUBE METADATA GENERATION - Title, Description, Thumbnail Prompt
# ═══════════════════════════════════════════════════════════════════════════════

class GenerateYoutubeMetadataRequest(BaseModel):
    script: str
    style_profile: Optional[Dict[str, Any]] = None
    title_samples: List[str] = []
    description_samples: List[str] = []
    title_style_analysis: Optional[Dict[str, Any]] = None  # Analyzed title style patterns
    description_style_analysis: Optional[Dict[str, Any]] = None  # Analyzed description style patterns
    thumbnail_style_analysis: Optional[Dict[str, Any]] = None  # Analyzed thumbnail style patterns
    generate_title: bool = True
    generate_description: bool = True
    generate_thumbnail_prompt: bool = True
    model: Optional[str] = None
    custom_cta: Optional[str] = None  # User's custom CTA template for descriptions
    sync_analysis: Optional[Dict[str, Any]] = None  # Sync analysis data for thumbnail
    voice_timestamps: Optional[List[Dict[str, Any]]] = None  # [{scene_id, timestamp, content, duration}]
    total_duration: Optional[str] = None  # e.g. "12:34"
    language: Optional[str] = None  # Content language e.g. "vi", "en", "ja"


@router.post("/generate-youtube-metadata")
async def generate_youtube_metadata(request: GenerateYoutubeMetadataRequest):
    """
    Generate YouTube metadata (Title, Description, Thumbnail Prompt)
    based on the generated script, style profile, and SEO best practices.
    
    Uses AI to create optimized:
    - Title: Hook-based, curiosity-driven, SEO-optimized (~60 chars)
    - Description: Multi-layered structure with timestamps, CTAs, keywords
    - Thumbnail Prompt: Visual storytelling prompt with 7-component formula
    """
    if not request.script or len(request.script.strip()) < 50:
        raise HTTPException(status_code=400, detail="Script cần ít nhất 50 ký tự")

    try:
        ai_client = get_configured_ai_client(model=request.model)
        
        # Build context from style profile
        style_context = ""
        if request.style_profile:
            style_summary = request.style_profile.get("style_summary", "")
            tone = request.style_profile.get("tone", "")
            if style_summary:
                style_context += f"\n\nPhong cách kênh: {style_summary}"
            if tone:
                style_context += f"\nTone: {tone}"

        # Script preview (first 3000 chars for better context with timestamps)
        script_preview = request.script.strip()[:3000]
        
        # Detect content language
        content_lang = request.language or 'vi'
        lang_name = LANG_NATIVE_MAP.get(content_lang, content_lang)
        lang_name_en = LANG_NAME_MAP.get(content_lang, 'the detected language')
        
        # Build timestamps text from voice data
        timestamps_text = ""
        if request.voice_timestamps and len(request.voice_timestamps) > 0:
            ts_lines = []
            for ts in request.voice_timestamps:
                time_str = ts.get('timestamp', '00:00')
                content = ts.get('content', '')[:100]  # First 100 chars of scene content
                ts_lines.append(f"{time_str} — {content}")
            timestamps_text = "\n".join(ts_lines)
            logger.info(f"[YT-Meta] Received {len(request.voice_timestamps)} timestamps, total duration: {request.total_duration}")
        
        results = {
            "success": True,
            "title": "",
            "description": "",
            "thumbnail_prompt": "",
        }
        
        # ── Generate Title ──
        if request.generate_title:
            title_samples_text = ""
            if request.title_samples:
                title_samples_text = "\n\nMẫu title tham khảo từ kênh:\n" + "\n".join(
                    f"- {s}" for s in request.title_samples[:10]
                )
            
            # Inject analyzed title style patterns
            title_style_text = ""
            if request.title_style_analysis:
                tsa = request.title_style_analysis
                parts = []
                if tsa.get("style_summary"):
                    parts.append(f"Tóm tắt phong cách: {tsa['style_summary']}")
                if tsa.get("title_formulas"):
                    formulas = "; ".join(tsa["title_formulas"][:5])
                    parts.append(f"Signature title formulas: {formulas}")
                if tsa.get("dominant_hooks"):
                    hooks = ", ".join(tsa["dominant_hooks"][:5])
                    parts.append(f"Dominant hooks: {hooks}")
                if tsa.get("power_words"):
                    pw = ", ".join(tsa["power_words"][:10])
                    parts.append(f"Power words: {pw}")
                if tsa.get("emotional_tone"):
                    parts.append(f"Emotional tone: {tsa['emotional_tone']}")
                # NOTE: Separator deliberately NOT injected — let AI decide naturally
                if tsa.get("avg_length"):
                    parts.append(f"Average length: ~{tsa['avg_length']} characters")
                if parts:
                    title_style_text = "\n\n📊 ANALYZED TITLE STYLE (apply this style):\n" + "\n".join(f"- {p}" for p in parts)
            
            title_prompt = f"""You are a YouTube content creator. Generate 1 natural, compelling VIDEO TITLE.

IMPORTANT RULES:
- Write as a native {lang_name_en} speaker would naturally SAY it, not like an SEO formula
- Maximum 60 characters
- Create natural curiosity — viewers click because they're CURIOUS, not because they feel baited
- Do NOT use "|" or "—" to split the title
- Do NOT force numbers (e.g., "3 layers", "5 steps", "7 things") unless the content truly revolves around that number
- Do NOT start with clichés like "The Truth", "Secret", "Top" unless truly appropriate
- Accurately reflect the script content, no clickbait
- Write the title in {lang_name} (match the script language)
- Prioritize a natural, approachable voice: title should feel like you're telling a friend
{style_context}
{title_style_text}
{title_samples_text}

SCRIPT:
{script_preview}

Return EXACTLY 1 TITLE, no explanation, no numbering, no quotes."""

            try:
                title_result = await asyncio.to_thread(
                    ai_client.generate, title_prompt, temperature=0.8
                )
                results["title"] = title_result.strip().strip('"').strip("'").strip()
                logger.info(f"[YT-Meta] Title generated: {results['title']}")
            except Exception as e:
                logger.error(f"[YT-Meta] Title generation failed: {e}")
                results["title"] = f"[Error generating title: {str(e)[:100]}]"
        
        # ── Generate Description ──
        if request.generate_description:
            desc_samples_text = ""
            if request.description_samples:
                desc_samples_text = "\n\nReference description samples from the channel:\n" + "\n".join(
                    f"---\n{s}" for s in request.description_samples[:5]
                )
            
            # Inject analyzed description style patterns
            desc_style_text = ""
            if request.description_style_analysis:
                dsa = request.description_style_analysis
                parts = []
                if dsa.get("style_summary"):
                    parts.append(f"Style summary: {dsa['style_summary']}")
                if dsa.get("hook_style"):
                    parts.append(f"Hook style: {dsa['hook_style']}")
                if dsa.get("body_style"):
                    bs = dsa["body_style"]
                    if bs.get("writing_approach"):
                        parts.append(f"Writing approach: {bs['writing_approach']}")
                if dsa.get("cta_patterns"):
                    cta = "; ".join(dsa["cta_patterns"][:3])
                    parts.append(f"CTA patterns: {cta}")
                if dsa.get("brand_voice"):
                    bv = dsa["brand_voice"]
                    if bv.get("tone"):
                        parts.append(f"Tone: {bv['tone']}")
                    if bv.get("addressing"):
                        parts.append(f"Audience addressing: {bv['addressing']}")
                if dsa.get("hashtag_strategy"):
                    hs = dsa["hashtag_strategy"]
                    if hs.get("avg_count"):
                        parts.append(f"Hashtags: ~{hs['avg_count']} tags")
                if dsa.get("structure_template"):
                    parts.append(f"Structure template: {dsa['structure_template']}")
                if parts:
                    desc_style_text = "\n\n📊 ANALYZED DESCRIPTION STYLE (apply this style):\n" + "\n".join(f"- {p}" for p in parts)
            
            # Build timestamps block for description
            timestamps_block = ""
            if timestamps_text:
                timestamps_block = f"""

LAYER 2.5 — TIMESTAMPS/CHAPTERS (required if video has multiple sections):
Below are scenes with exact timestamps from voice generation.
READ each scene's content and CREATE short, engaging chapter titles that accurately reflect the content.

TIMESTAMP DATA (time — scene content):
{timestamps_text}

CHAPTER TITLE RULES:
- Write chapter titles in {lang_name} (SAME language as the script)
- Each chapter title 3-8 words, intriguing but accurate
- Do NOT copy scene content verbatim — SUMMARIZE into an engaging title
- Do NOT use ordinal numbers (1., 2., 3.) — just timestamp + title
- Group consecutive scenes into larger chapters if they share a topic (do NOT list every scene)
- Example format:
  00:00 Opening — The 3AM Fear
  02:15 Childhood Fears
  05:30 Growing Up and Real Fears
  08:12 "The Elephant in the Room"
Total video duration: {request.total_duration or 'N/A'}
"""
            else:
                timestamps_block = """

(No voice data available — skip timestamps section)
"""
            
            desc_prompt = f"""You are a YouTube content creator. Write a natural, compelling video description.

⚠️ IMPORTANT RULES ABOUT CTA/PERSONALIZATION:
- Analyze the sample descriptions below (if provided)
- DETECT and REMOVE all PERSONAL/ORGANIZATIONAL content from original samples:
  + Specific channel names, specific YouTube/social media links
  + Handles (@username), contact emails
  + Channel-specific taglines/slogans
  + Specific disclaimers, sponsor acknowledgments
- Do NOT COPY personalized content from samples into the new description

DESCRIPTION ARCHITECTURE:

LAYER 1 — THE HOOK (first 1-2 lines — "Golden Zone"):
- The ONLY part visible before the "Show more" button
- Include main keywords in the first 150 characters
- Get straight to the point, do NOT write "Hey everyone, today I will..."
- Natural curiosity-inducing hook line

LAYER 2 — DETAILED CONTENT (Mini Blog):
- 150-300 words summarizing the video's key points
- Write as if telling a story to friends, naturally
- Weave in keywords naturally, do NOT stuff them
{timestamps_block}
LAYER 3 — CTA & LINKS:
{f"USE EXACTLY the following CTA provided by the user (do NOT modify content, only format appropriately):{chr(10)}{request.custom_cta}" if request.custom_cta else f"- Subscribe: [Subscribe link]{chr(10)}- Related videos / Playlists on the same topic{chr(10)}- Resource links if appropriate"}

LAYER 4 — HASHTAGS:
- Exactly 3-5 hashtags, placed at the very end
- 1 brand hashtag + 1 broad topic hashtag + 1-3 niche hashtags
{style_context}
{desc_style_text}
{desc_samples_text}

SCRIPT:
{script_preview}

Return a COMPLETE DESCRIPTION. Write in {lang_name}."""

            try:
                desc_result = await asyncio.to_thread(
                    ai_client.generate, desc_prompt, temperature=0.7
                )
                results["description"] = desc_result.strip()
                logger.info(f"[YT-Meta] Description generated: {len(results['description'])} chars")
            except Exception as e:
                logger.error(f"[YT-Meta] Description generation failed: {e}")
                results["description"] = f"[Error generating description: {str(e)[:100]}]"
        
        # ── Generate Thumbnail Prompt ──
        if request.generate_thumbnail_prompt:
            # Inject analyzed thumbnail style patterns
            thumb_style_text = ""
            if request.thumbnail_style_analysis:
                tsa = request.thumbnail_style_analysis
                parts = []
                if tsa.get("style_summary"):
                    parts.append(f"Overall style: {tsa['style_summary']}")
                if tsa.get("composition"):
                    comp = tsa["composition"]
                    if comp.get("layout"):
                        parts.append(f"Layout: {comp['layout']}")
                    if comp.get("subject_position"):
                        parts.append(f"Subject position: {comp['subject_position']}")
                if tsa.get("color_scheme"):
                    cs = tsa["color_scheme"]
                    if cs.get("dominant_colors"):
                        colors = ", ".join(cs["dominant_colors"][:5])
                        parts.append(f"Dominant colors: {colors}")
                    if cs.get("contrast_style"):
                        parts.append(f"Contrast: {cs['contrast_style']}")
                if tsa.get("typography"):
                    typo = tsa["typography"]
                    if typo.get("font_style"):
                        parts.append(f"Font style: {typo['font_style']}")
                    if typo.get("effects"):
                        effects = ", ".join(typo["effects"][:3])
                        parts.append(f"Text effects: {effects}")
                if tsa.get("emotional_signals"):
                    es = tsa["emotional_signals"]
                    if es.get("dominant_emotion"):
                        parts.append(f"Dominant emotion: {es['dominant_emotion']}")
                if tsa.get("thumbnail_formula"):
                    parts.append(f"Thumbnail formula: {tsa['thumbnail_formula']}")
                if parts:
                    thumb_style_text = "\n\n📊 ANALYZED THUMBNAIL STYLE (apply this visual style):\n" + "\n".join(f"- {p}" for p in parts)
            
            thumb_prompt = f"""You are a YouTube thumbnail design expert. Create 1 detailed prompt for AI to generate a compelling thumbnail for this video.

7-COMPONENT THUMBNAIL FORMULA:
1. Subject/Focal Point — main character or object, based on script content
2. Expression/Emotion — strong expression, matching the theme
3. Background/Setting — setting appropriate to video content
4. Color Scheme — high contrast colors (complementary colors)
5. Text Overlay — 2-4 large, bold words, readable on mobile, MUST BE WRITTEN IN {lang_name.upper()}
6. Composition — Rule of thirds, clear focal point
7. Style — Professional, cinematic, high contrast

IMPORTANT LANGUAGE RULES:
- Visual description prompt should be in English (for AI image generator compatibility)
- BUT the TEXT OVERLAY on the thumbnail MUST be in {lang_name} (because the audience reads {lang_name})
- Example: if the script is in Vietnamese → text overlay must be Vietnamese like "NỖI SỢ?" not "ADULT FEAR?"

REQUIREMENTS:
- Write the prompt in English (visual description part)
- Text overlay content in {lang_name} (text shown on thumbnail)
- Detailed, specific description
- Optimized for 1280x720 (16:9)
- Must be eye-catching at small sizes (mobile)
{style_context}
{thumb_style_text}
"""
            # Inject sync analysis into thumbnail prompt (full descriptions for visual consistency)
            if request.sync_analysis:
                sa = request.sync_analysis
                sync_thumb_parts = []
                if sa.get('characters'):
                    for c in sa['characters'][:2]:  # Top 2 characters with full detail
                        name = c.get('name', 'Unknown')
                        desc = c.get('description', '')
                        if desc:
                            sync_thumb_parts.append(f"CHARACTER — {name}: {desc}")
                        else:
                            sync_thumb_parts.append(f"CHARACTER — {name}")
                if sa.get('visual_style'):
                    sync_thumb_parts.append(f"VISUAL STYLE: {sa['visual_style']}")
                if sa.get('settings'):
                    for s in sa['settings'][:2]:  # Top 2 settings with full detail
                        name = s.get('name', 'Unknown')
                        desc = s.get('description', '')
                        if desc:
                            sync_thumb_parts.append(f"SETTING — {name}: {desc}")
                        else:
                            sync_thumb_parts.append(f"SETTING — {name}")
                if sync_thumb_parts:
                    thumb_prompt += "\n\nSYNC ANALYSIS CONTEXT (use these exact visual details for consistency):\n" + "\n".join([f"- {p}" for p in sync_thumb_parts]) + "\n"

            thumb_prompt += f"""SCRIPT:
{script_preview}

Return EXACTLY 1 THUMBNAIL PROMPT in English (visual description), with TEXT OVERLAY in {lang_name}. No additional explanation."""

            try:
                thumb_result = await asyncio.to_thread(
                    ai_client.generate, thumb_prompt, temperature=0.8
                )
                results["thumbnail_prompt"] = thumb_result.strip()
                logger.info(f"[YT-Meta] Thumbnail prompt generated: {len(results['thumbnail_prompt'])} chars")
            except Exception as e:
                logger.error(f"[YT-Meta] Thumbnail prompt generation failed: {e}")
                results["thumbnail_prompt"] = f"[Error generating thumbnail prompt: {str(e)[:100]}]"

        return results

    except Exception as e:
        import traceback
        logger.error(f"[YT-Meta] Error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ===== Metadata Style Analysis (Title / Description / Thumbnail) =====

class AnalyzeMetadataStylesRequest(BaseModel):
    title_samples: List[str] = []          # 5-20 sample YouTube titles
    description_samples: List[str] = []    # 5-20 sample YouTube descriptions
    thumbnail_descriptions: List[str] = [] # Text descriptions of thumbnail visuals (legacy)
    thumbnail_images: List[str] = []       # Base64 data URIs of thumbnail images for Vision API
    model: Optional[str] = None
    output_language: str = ""  # Target output language - if set and differs from input, title/desc will be translated first


# ═══════════════════════════════════════════════════════════════════════════
# HELPER: Parse JSON from AI response (strips markdown fences, etc.)
# ═══════════════════════════════════════════════════════════════════════════
def _parse_metadata_json(text: str) -> dict:
    """Parse JSON from AI response, handling markdown code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
    try:
        return json_module.loads(cleaned)
    except Exception:
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{[\s\S]*\}', cleaned)
        if json_match:
            try:
                return json_module.loads(json_match.group())
            except Exception:
                pass
        return None


@router.post("/analyze-metadata-styles-stream")
async def analyze_metadata_styles_stream(request: AnalyzeMetadataStylesRequest):
    """
    SSE streaming endpoint to analyze title, description, and thumbnail styles in parallel.
    
    🔄 CONVERSATION-BASED ANALYSIS (same pattern as StyleA voice analysis):
    STEP 1: Create conversation with domain-specific system prompt
    STEP 2: Analyze each sample individually in conversation (AI builds memory)
    STEP 3: Send synthesis prompt to produce final profile from accumulated memory
    STEP 4: Parse and return structured JSON profile
    
    All 3 analysis types run in parallel via ThreadPoolExecutor.
    Falls back to single-shot when conversation support is unavailable.
    """
    has_titles = len(request.title_samples) > 0
    has_descriptions = len(request.description_samples) > 0
    has_thumbnails = len(request.thumbnail_images) > 0 or len(request.thumbnail_descriptions) > 0

    if not has_titles and not has_descriptions and not has_thumbnails:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 loại mẫu (title/description/thumbnail)")

    ai_client = get_configured_ai_client(request.model)
    supports_conversation = ai_client.has_conversation_support()

    async def stream_analysis():
        import concurrent.futures
        import queue as queue_module

        results = {
            "title_style": None,
            "description_style": None,
            "thumbnail_style": None,
        }
        total_tasks = sum([has_titles, has_descriptions, has_thumbnails])

        # Thread-safe progress queue for real-time updates from workers
        progress_queue = queue_module.Queue()

        def send_event(event_type: str, data: dict) -> str:
            return f"event: {event_type}\ndata: {json_module.dumps(data, ensure_ascii=False)}\n\n"

        def report_progress(step: str, percentage: int, message: str):
            """Thread-safe progress reporting from worker threads."""
            progress_queue.put({"step": step, "percentage": percentage, "message": message})

        yield send_event("progress", {
            "step": "init", "percentage": 0,
            "message": f"Bắt đầu phân tích {total_tasks} mục {'(conversation mode)' if supports_conversation else '(single-shot mode)'}..."
        })

        # ── PRE-TRANSLATION: Translate title/description samples if output language differs ──
        translated_titles = list(request.title_samples)
        translated_descs = list(request.description_samples)
        output_lang = request.output_language.strip()
        
        if output_lang and (has_titles or has_descriptions):
            # Auto-detect input language from first available sample
            detect_text = (request.title_samples[0] if has_titles else request.description_samples[0])
            detected_input = _detect_language(detect_text)
            
            if detected_input != output_lang:
                lang_names = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese", "es": "Spanish", "fr": "French", "th": "Thai", "de": "German", "pt": "Portuguese", "ru": "Russian"}
                src_name = lang_names.get(detected_input, detected_input)
                out_name = lang_names.get(output_lang, output_lang)
                
                loop = asyncio.get_event_loop()
                
                # Translate titles
                if has_titles:
                    yield send_event("progress", {"step": "translate_title", "percentage": 1, "message": f"Đang dịch {len(translated_titles)} tiêu đề {src_name} → {out_name}..."})
                    new_titles = []
                    for i, title in enumerate(translated_titles):
                        try:
                            prompt = f"Translate this YouTube title from {src_name} to {out_name}. Output ONLY the translated title, nothing else:\n\n{title}"
                            result = await loop.run_in_executor(None, lambda p=prompt: ai_client.generate(p, temperature=0.3))
                            new_titles.append(result.strip() if result and len(result.strip()) > 3 else title)
                        except Exception:
                            new_titles.append(title)
                    translated_titles = new_titles
                    yield send_event("progress", {"step": "translate_title_done", "percentage": 3, "message": f"Đã dịch {len(new_titles)} tiêu đề sang {out_name}"})
                
                # Translate descriptions
                if has_descriptions:
                    yield send_event("progress", {"step": "translate_desc", "percentage": 3, "message": f"Đang dịch {len(translated_descs)} mô tả {src_name} → {out_name}..."})
                    new_descs = []
                    for i, desc in enumerate(translated_descs):
                        try:
                            prompt = f"""Translate this YouTube description from {src_name} to {out_name}.
Rules: Preserve structure, line breaks, links. Output ONLY the translated text.\n\n{desc}"""
                            result = await loop.run_in_executor(None, lambda p=prompt: ai_client.generate(p, temperature=0.3))
                            new_descs.append(result.strip() if result and len(result.strip()) > 10 else desc)
                        except Exception:
                            new_descs.append(desc)
                    translated_descs = new_descs
                    yield send_event("progress", {"step": "translate_desc_done", "percentage": 5, "message": f"Đã dịch {len(new_descs)} mô tả sang {out_name}"})
                
                # Update request samples with translated versions
                request.title_samples = translated_titles
                request.description_samples = translated_descs

        # ═══════════════════════════════════════════════════════════════════════
        # TITLE ANALYSIS — Conversation-based
        # ═══════════════════════════════════════════════════════════════════════
        def analyze_titles() -> dict:
            samples = request.title_samples[:20]
            num_samples = len(samples)
            
            if supports_conversation:
                # ── STEP 1: Create conversation ──
                system_prompt = """Bạn là chuyên gia phân tích tiêu đề YouTube với kinh nghiệm SEO và CTR optimization.

NHIỆM VỤ: Phân tích TỪNG tiêu đề được gửi đến và GHI NHỚ tất cả đặc điểm để cuối cùng tổng hợp thành "PHONG CÁCH ĐẶT TIÊU ĐỀ".

QUY TẮC:
1. Mỗi tiêu đề: Trả về phân tích ngắn gọn dạng JSON
2. GHI NHỚ: Tất cả patterns, hooks, power words, cấu trúc qua từng tiêu đề
3. Khi được yêu cầu TỔNG HỢP: Đúc kết từ TẤT CẢ tiêu đề đã phân tích
4. Output PHẢI viết bằng tiếng Việt CÓ DẤU

Hãy sẵn sàng phân tích!"""
                
                try:
                    conv_id = ai_client.start_conversation(system_prompt)
                    logger.info(f"[Title] Conversation started: {conv_id[:8]}...")
                    report_progress("title_start", 5, "🏷️ Bắt đầu phân tích tiêu đề...")
                except Exception as e:
                    logger.error(f"[Title] Failed to start conversation: {e}, falling back to single-shot")
                    return _analyze_titles_single_shot(ai_client, samples)
                
                # ── STEP 2: Analyze each title individually ──
                individual_results = []
                for i, title in enumerate(samples, 1):
                    report_progress("title_sample", 5 + int((i / num_samples) * 25), f"🏷️ Phân tích tiêu đề {i}/{num_samples}...")
                    analysis_prompt = f"""Phân tích TIÊU ĐỀ #{i}/{num_samples}:

"{title}"

Trả về JSON ngắn gọn:
{{
    "hook_type": "curiosity_gap/negativity_bias/authority/specificity/how_to/listicle/social_proof",
    "power_words": ["từ mạnh 1", "từ mạnh 2"],
    "emotional_trigger": "cảm xúc kích hoạt",
    "structure": "mô tả cấu trúc ngắn",
    "length": {len(title)},
    "effectiveness": "1-10 và lý do ngắn"
}}"""
                    try:
                        response = ai_client.send_message(conv_id, analysis_prompt, temperature=0.3)
                        parsed = _parse_metadata_json(response)
                        if parsed:
                            parsed['title'] = title
                            parsed['index'] = i
                            individual_results.append(parsed)
                        logger.info(f"[Title] ✅ Analyzed {i}/{num_samples}")
                    except Exception as e:
                        logger.error(f"[Title] ❌ Error analyzing title {i}: {e}")
                
                report_progress("title_synth", 30, "🏷️ Tổng hợp phong cách tiêu đề...")
                # ── STEP 3: Synthesize ──
                synthesis_prompt = f"""Bây giờ, dựa trên TẤT CẢ {num_samples} tiêu đề bạn vừa phân tích, hãy ĐÚC KẾT thành "PHONG CÁCH ĐẶT TIÊU ĐỀ".

⚠️ QUY TẮC:
1. KHÔNG nhắc đến nội dung cụ thể của bất kỳ tiêu đề nào
2. CHỈ mô tả PATTERNS và TECHNIQUES chung xuất hiện xuyên suốt {num_samples} tiêu đề
3. Mỗi trường phải là MÔ TẢ TỔNG QUÁT áp dụng được cho tất cả tiêu đề

TRẢ VỀ JSON (không giải thích thêm):
{{
  "hook_patterns": ["pattern mô tả 1", "pattern 2"],
  "dominant_hooks": ["loại hook chủ đạo 1", "loại 2"],
  "avg_length": 45,
  "syntax_patterns": {{
    "front_loading": true hoặc false,
    "separator": "|" hoặc "-" hoặc ":" hoặc "none",
    "capitalization": "title_case" hoặc "strategic_caps" hoặc "all_caps"
  }},
  "power_words": ["từ1", "từ2", "từ3"],
  "emotional_tone": "mô tả tông cảm xúc",
  "title_formulas": ["công thức 1", "công thức 2"],
  "style_summary": "Tóm tắt 2-3 câu về phong cách đặt tiêu đề"
}}"""
                try:
                    response = ai_client.send_message(conv_id, synthesis_prompt, temperature=0.3)
                    parsed = _parse_metadata_json(response)
                    if parsed:
                        logger.info(f"[Title] ✅ Synthesis complete")
                        return parsed
                except Exception as e:
                    logger.error(f"[Title] Synthesis failed: {e}")
                
                # Fallback if synthesis fails
                return {"style_summary": f"Phân tích {num_samples} tiêu đề thành công nhưng tổng hợp thất bại", "individual_count": len(individual_results)}
            else:
                return _analyze_titles_single_shot(ai_client, samples)

        # ═══════════════════════════════════════════════════════════════════════
        # DESCRIPTION ANALYSIS — Conversation-based
        # ═══════════════════════════════════════════════════════════════════════
        def analyze_descriptions() -> dict:
            samples = request.description_samples[:20]
            num_samples = len(samples)
            
            if supports_conversation:
                # ── STEP 1: Create conversation ──
                system_prompt = """Bạn là chuyên gia phân tích mô tả video YouTube, chuyên về SEO và audience engagement.

NHIỆM VỤ: Phân tích TỪNG mô tả video được gửi đến và GHI NHỚ tất cả đặc điểm để cuối cùng tổng hợp thành "PHONG CÁCH MÔ TẢ".

QUY TẮC:
1. Mỗi mô tả: Trả về phân tích ngắn gọn dạng JSON
2. GHI NHỚ: Cấu trúc, hooks, CTA, hashtags, brand voice qua từng mô tả
3. Khi được yêu cầu TỔNG HỢP: Đúc kết từ TẤT CẢ mô tả đã phân tích
4. Output PHẢI viết bằng tiếng Việt CÓ DẤU

Hãy sẵn sàng phân tích!"""
                
                try:
                    conv_id = ai_client.start_conversation(system_prompt)
                    logger.info(f"[Description] Conversation started: {conv_id[:8]}...")
                    report_progress("desc_start", 35, "📝 Bắt đầu phân tích mô tả...")
                except Exception as e:
                    logger.error(f"[Description] Failed to start conversation: {e}, falling back to single-shot")
                    return _analyze_descriptions_single_shot(ai_client, samples)
                
                # ── STEP 2: Analyze each description individually ──
                individual_results = []
                for i, desc in enumerate(samples, 1):
                    report_progress("desc_sample", 35 + int((i / num_samples) * 25), f"📝 Phân tích mô tả {i}/{num_samples}...")
                    # Truncate very long descriptions to avoid token limits
                    desc_content = desc[:3000] if len(desc) > 3000 else desc
                    
                    analysis_prompt = f"""Phân tích MÔ TẢ #{i}/{num_samples}:

\"\"\"
{desc_content}
\"\"\"

Trả về JSON ngắn gọn:
{{
    "hook_line": "dòng hook đầu tiên",
    "word_count": {len(desc.split())},
    "has_timestamps": true/false,
    "has_cta": true/false,
    "cta_type": "subscribe/like/link/none",
    "hashtag_count": 0,
    "tone": "thân mật/trang trọng/hài hước",
    "structure": "mô tả cấu trúc ngắn",
    "key_elements": ["yếu tố 1", "yếu tố 2"]
}}"""
                    try:
                        response = ai_client.send_message(conv_id, analysis_prompt, temperature=0.3)
                        parsed = _parse_metadata_json(response)
                        if parsed:
                            parsed['index'] = i
                            individual_results.append(parsed)
                        logger.info(f"[Description] ✅ Analyzed {i}/{num_samples}")
                    except Exception as e:
                        logger.error(f"[Description] ❌ Error analyzing description {i}: {e}")
                
                # ── STEP 3: Synthesize ──
                synthesis_prompt = f"""Bây giờ, dựa trên TẤT CẢ {num_samples} mô tả video bạn vừa phân tích, hãy ĐÚC KẾT thành "PHONG CÁCH MÔ TẢ".

⚠️ QUY TẮC:
1. KHÔNG nhắc đến nội dung cụ thể của bất kỳ mô tả nào
2. CHỈ mô tả PATTERNS và TECHNIQUES chung
3. Mỗi trường phải là MÔ TẢ TỔNG QUÁT

PHÂN TÍCH KIẾN TRÚC MÔ TẢ 5 TẦNG dựa trên patterns đã thấy.

TRẢ VỀ JSON (không giải thích thêm):
{{
  "hook_style": "mô tả cách viết hook (2 dòng đầu)",
  "body_style": {{
    "avg_word_count": 200,
    "writing_approach": "tóm tắt/kể chuyện/liệt kê",
    "uses_lsi_keywords": true/false
  }},
  "uses_timestamps": true/false,
  "timestamp_style": "mô tả phong cách timestamps nếu có",
  "cta_patterns": ["CTA pattern 1", "CTA pattern 2"],
  "cta_position": "top/middle/bottom/distributed",
  "hashtag_strategy": {{
    "avg_count": 3,
    "types": ["brand", "topic", "niche"]
  }},
  "brand_voice": {{
    "tone": "thân mật/trang trọng/hài hước",
    "vocabulary": ["từ đặc trưng 1", "từ 2"],
    "addressing": "cách xưng hô"
  }},
  "structure_template": "Mô tả cấu trúc mẫu cho description mới (template)",
  "style_summary": "Tóm tắt 2-3 câu về phong cách mô tả"
}}"""
                try:
                    response = ai_client.send_message(conv_id, synthesis_prompt, temperature=0.3)
                    parsed = _parse_metadata_json(response)
                    if parsed:
                        logger.info(f"[Description] ✅ Synthesis complete")
                        return parsed
                except Exception as e:
                    logger.error(f"[Description] Synthesis failed: {e}")
                
                return {"style_summary": f"Phân tích {num_samples} mô tả thành công nhưng tổng hợp thất bại", "individual_count": len(individual_results)}
            else:
                return _analyze_descriptions_single_shot(ai_client, samples)

        # ═══════════════════════════════════════════════════════════════════════
        # THUMBNAIL ANALYSIS — Conversation-based
        # ═══════════════════════════════════════════════════════════════════════
        def analyze_thumbnails() -> dict:
            thumb_images = request.thumbnail_images[:10]
            thumb_descs = request.thumbnail_descriptions[:10]
            num_images = len(thumb_images)
            num_samples = max(num_images, len(thumb_descs))

            # ── VISION-BASED ANALYSIS (when real images are provided) ──
            if num_images > 0:
                report_progress("thumb_start", 65, "🖼️ Phân tích thumbnail bằng Vision AI...")
                logger.info(f"[Thumbnail] Vision analysis with {num_images} images")

                vision_prompt = f"""Bạn là chuyên gia phân tích thumbnail YouTube, chuyên về visual design và CTR optimization.

PHÂN TÍCH {num_images} THUMBNAIL ĐÍNH KÈM và đúc kết thành "PHONG CÁCH THUMBNAIL".

CHO MỖI THUMBNAIL, phân tích:
- Bố cục (layout, rule of thirds, subject position)
- Màu sắc (dominant colors, contrast, saturation)
- Typography (text overlay, font style, word count)
- Cảm xúc (facial expressions, emotion, eye contact)
- Visual storytelling (before/after, curiosity gap, arrows)

⚠️ QUY TẮC:
1. KHÔNG nhắc đến nội dung cụ thể của bất kỳ thumbnail nào
2. CHỈ mô tả PATTERNS và DESIGN PRINCIPLES chung xuất hiện xuyên suốt
3. Mỗi trường phải là MÔ TẢ TỔNG QUÁT áp dụng được cho tất cả thumbnail
4. Output PHẢI viết bằng tiếng Việt CÓ DẤU

TRẢ VỀ JSON (không giải thích thêm):
{{
  "composition": {{
    "layout": "rule_of_thirds/centered/asymmetric",
    "subject_position": "left/right/center",
    "visual_hierarchy": "mô tả phân cấp thị giác"
  }},
  "color_scheme": {{
    "dominant_colors": ["màu chủ đạo 1", "màu 2"],
    "contrast_style": "high/medium/low",
    "saturation": "hyper/normal/muted",
    "emotional_mapping": "mô tả cảm xúc từ màu sắc"
  }},
  "typography": {{
    "avg_word_count": 3,
    "font_style": "bold_sans_serif/custom/minimal",
    "effects": ["stroke", "shadow"]
  }},
  "emotional_signals": {{
    "uses_faces": true/false,
    "dominant_emotion": "shock/joy/curiosity/fear",
    "eye_contact": true/false,
    "exaggeration_level": "high/medium/low"
  }},
  "storytelling_techniques": ["before_after", "curiosity_gap", "arrows"],
  "overall_style": "professional/casual/cinematic",
  "text_strategy": "complementary/repetitive/curiosity_gap",
  "thumbnail_formula": "Công thức thumbnail đặc trưng nhất",
  "style_summary": "Tóm tắt 2-3 câu về phong cách thumbnail"
}}"""
                try:
                    report_progress("thumb_sample", 75, f"🖼️ Gửi {num_images} ảnh đến Vision AI...")
                    response = ai_client.generate_with_images(
                        vision_prompt, thumb_images, temperature=0.3, max_tokens=4000
                    )
                    parsed = _parse_metadata_json(response)
                    if parsed:
                        logger.info(f"[Thumbnail] ✅ Vision analysis complete")
                        report_progress("thumb_done", 90, "Hoàn thành phân tích thumbnail ✓")
                        return parsed
                    else:
                        logger.warning(f"[Thumbnail] Vision response not valid JSON, raw: {response[:300]}")
                        return {"style_summary": response.strip()[:500], "raw": True}
                except Exception as e:
                    logger.error(f"[Thumbnail] Vision analysis failed: {e}, falling back to text-based")
                    # Fall through to conversation-based analysis with descriptions
                    if not thumb_descs:
                        return {"style_summary": f"Vision analysis failed: {str(e)[:200]}", "error": True}

            # ── TEXT-BASED ANALYSIS (fallback: when only descriptions are available) ──
            samples = thumb_descs
            num_samples = len(samples)
            if num_samples == 0:
                return {"style_summary": "Không có dữ liệu thumbnail để phân tích", "error": True}

            if supports_conversation:
                # ── STEP 1: Create conversation ──
                system_prompt = """Bạn là chuyên gia phân tích thumbnail YouTube, chuyên về visual design và CTR optimization.

NHIỆM VỤ: Phân tích TỪNG mô tả thumbnail được gửi đến và GHI NHỚ tất cả đặc điểm để cuối cùng tổng hợp thành "PHONG CÁCH THUMBNAIL".

QUY TẮC:
1. Mỗi thumbnail: Trả về phân tích ngắn gọn dạng JSON
2. GHI NHỚ: Bố cục, màu sắc, cảm xúc, typography, storytelling qua từng thumbnail
3. Khi được yêu cầu TỔNG HỢP: Đúc kết từ TẤT CẢ thumbnail đã phân tích
4. Output PHẢI viết bằng tiếng Việt CÓ DẤU

Hãy sẵn sàng phân tích!"""
                
                try:
                    conv_id = ai_client.start_conversation(system_prompt)
                    logger.info(f"[Thumbnail] Conversation started: {conv_id[:8]}...")
                    report_progress("thumb_start", 65, "🖼️ Bắt đầu phân tích thumbnail (text)...")
                except Exception as e:
                    logger.error(f"[Thumbnail] Failed to start conversation: {e}, falling back to single-shot")
                    return _analyze_thumbnails_single_shot(ai_client, samples)
                
                # ── STEP 2: Analyze each thumbnail individually ──
                individual_results = []
                for i, thumb_desc in enumerate(samples, 1):
                    report_progress("thumb_sample", 65 + int((i / num_samples) * 25), f"🖼️ Phân tích thumbnail {i}/{num_samples}...")
                    analysis_prompt = f"""Phân tích THUMBNAIL #{i}/{num_samples}:

Mô tả:
\"\"\"{thumb_desc}\"\"\"

Trả về JSON ngắn gọn:
{{
    "layout": "rule_of_thirds/centered/asymmetric",
    "dominant_colors": ["màu 1", "màu 2"],
    "has_text": true/false,
    "text_words": 0,
    "has_face": true/false,
    "emotion": "shock/joy/curiosity/fear/neutral",
    "contrast": "high/medium/low",
    "storytelling": "before_after/curiosity_gap/reveal/arrows/none",
    "overall_feel": "mô tả ngắn"
}}"""
                    try:
                        response = ai_client.send_message(conv_id, analysis_prompt, temperature=0.3)
                        parsed = _parse_metadata_json(response)
                        if parsed:
                            parsed['index'] = i
                            individual_results.append(parsed)
                        logger.info(f"[Thumbnail] ✅ Analyzed {i}/{num_samples}")
                    except Exception as e:
                        logger.error(f"[Thumbnail] ❌ Error analyzing thumbnail {i}: {e}")
                
                # ── STEP 3: Synthesize ──
                synthesis_prompt = f"""Bây giờ, dựa trên TẤT CẢ {num_samples} thumbnail bạn vừa phân tích, hãy ĐÚC KẾT thành "PHONG CÁCH THUMBNAIL".

⚠️ QUY TẮC:
1. KHÔNG nhắc đến nội dung cụ thể của bất kỳ thumbnail nào
2. CHỈ mô tả PATTERNS và DESIGN PRINCIPLES chung
3. Mỗi trường phải là MÔ TẢ TỔNG QUÁT

PHÂN TÍCH PHÁP Y HÌNH ẢNH: Bố cục, Màu sắc, Typography, Cảm xúc, Visual Storytelling, Phong cách tổng thể, Text Strategy.

TRẢ VỀ JSON (không giải thích thêm):
{{
  "composition": {{
    "layout": "rule_of_thirds/centered/asymmetric",
    "subject_position": "left/right/center",
    "visual_hierarchy": "mô tả phân cấp thị giác"
  }},
  "color_scheme": {{
    "dominant_colors": ["màu chủ đạo 1", "màu 2"],
    "contrast_style": "high/medium/low",
    "saturation": "hyper/normal/muted",
    "emotional_mapping": "mô tả cảm xúc từ màu sắc"
  }},
  "typography": {{
    "avg_word_count": 3,
    "font_style": "bold_sans_serif/custom/minimal",
    "effects": ["stroke", "shadow"]
  }},
  "emotional_signals": {{
    "uses_faces": true/false,
    "dominant_emotion": "shock/joy/curiosity/fear",
    "eye_contact": true/false,
    "exaggeration_level": "high/medium/low"
  }},
  "storytelling_techniques": ["before_after", "curiosity_gap", "arrows"],
  "overall_style": "professional/casual/cinematic",
  "text_strategy": "complementary/repetitive/curiosity_gap",
  "thumbnail_formula": "Công thức thumbnail đặc trưng nhất",
  "style_summary": "Tóm tắt 2-3 câu về phong cách thumbnail"
}}"""
                try:
                    response = ai_client.send_message(conv_id, synthesis_prompt, temperature=0.3)
                    parsed = _parse_metadata_json(response)
                    if parsed:
                        logger.info(f"[Thumbnail] ✅ Synthesis complete")
                        return parsed
                except Exception as e:
                    logger.error(f"[Thumbnail] Synthesis failed: {e}")
                
                return {"style_summary": f"Phân tích {num_samples} thumbnail thành công nhưng tổng hợp thất bại", "individual_count": len(individual_results)}
            else:
                return _analyze_thumbnails_single_shot(ai_client, samples)

        # ═══════════════════════════════════════════════════════════════════════
        # RUN ALL 3 IN PARALLEL
        # ═══════════════════════════════════════════════════════════════════════
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}
            if has_titles:
                futures["title"] = loop.run_in_executor(executor, analyze_titles)
            if has_descriptions:
                futures["description"] = loop.run_in_executor(executor, analyze_descriptions)
            if has_thumbnails:
                futures["thumbnail"] = loop.run_in_executor(executor, analyze_thumbnails)

            # Gather all futures as asyncio tasks
            all_tasks = list(futures.items())
            pending_futures = {key: future for key, future in all_tasks}
            completed_keys = set()

            # Drain progress queue and await futures concurrently
            while pending_futures:
                # Drain all queued progress events
                while not progress_queue.empty():
                    try:
                        prog = progress_queue.get_nowait()
                        yield send_event("progress", prog)
                    except Exception:
                        break

                # Check which futures are done
                done_keys = []
                for key, future in pending_futures.items():
                    if future.done():
                        done_keys.append(key)
                        try:
                            result = future.result()
                            results[f"{key}_style"] = result
                            completed_keys.add(key)
                            label_map = {"title": "tiêu đề", "description": "mô tả", "thumbnail": "thumbnail"}
                            yield send_event("progress", {
                                "step": f"{key}_done",
                                "percentage": int((len(completed_keys) / total_tasks) * 80) + 10,
                                "message": f"Hoàn thành phân tích {label_map.get(key, key)} ✓"
                            })
                        except Exception as e:
                            logger.error(f"[Metadata-Analysis] Error analyzing {key}: {e}")
                            results[f"{key}_style"] = {"error": str(e)}
                            completed_keys.add(key)

                for key in done_keys:
                    del pending_futures[key]

                if pending_futures:
                    await asyncio.sleep(0.3)

            # Final drain of any remaining progress events
            while not progress_queue.empty():
                try:
                    prog = progress_queue.get_nowait()
                    yield send_event("progress", prog)
                except Exception:
                    break

        yield send_event("progress", {"step": "done", "percentage": 100, "message": "Hoàn thành phân tích toàn bộ!"})
        yield send_event("result", {
            "success": True,
            "title_style": results["title_style"],
            "description_style": results["description_style"],
            "thumbnail_style": results["thumbnail_style"],
        })

    return StreamingResponse(
        stream_analysis(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ═══════════════════════════════════════════════════════════════════════════
# SINGLE-SHOT FALLBACKS (when conversation is not supported)
# ═══════════════════════════════════════════════════════════════════════════

def _analyze_titles_single_shot(ai_client, samples: list) -> dict:
    """Fallback: Analyze all titles in a single prompt."""
    samples_text = "\n".join([f"{i+1}. {t}" for i, t in enumerate(samples)])
    prompt = f"""Bạn là chuyên gia phân tích tiêu đề YouTube. Phân tích {len(samples)} tiêu đề mẫu và đúc kết thành "PHONG CÁCH ĐẶT TIÊU ĐỀ".

CÁC TIÊU ĐỀ MẪU:
{samples_text}

TRẢ VỀ JSON:
{{
  "hook_patterns": ["pattern1", "pattern2"],
  "dominant_hooks": ["curiosity_gap", "specificity"],
  "avg_length": 45,
  "syntax_patterns": {{"front_loading": true, "separator": "|", "capitalization": "title_case"}},
  "power_words": ["từ1", "từ2", "từ3"],
  "emotional_tone": "mô tả tông cảm xúc",
  "title_formulas": ["công thức 1", "công thức 2"],
  "style_summary": "Tóm tắt 2-3 câu về phong cách đặt tiêu đề"
}}"""
    result = ai_client.generate(prompt, temperature=0.3)
    parsed = _parse_metadata_json(result)
    return parsed if parsed else {"style_summary": result.strip(), "raw": True}


def _analyze_descriptions_single_shot(ai_client, samples: list) -> dict:
    """Fallback: Analyze all descriptions in a single prompt."""
    samples_text = "\n---\n".join([f"MẪU {i+1}:\n{d[:2000]}" for i, d in enumerate(samples)])
    prompt = f"""Bạn là chuyên gia phân tích mô tả video YouTube. Phân tích {len(samples)} mô tả mẫu và đúc kết thành "PHONG CÁCH MÔ TẢ".

CÁC MÔ TẢ MẪU:
{samples_text}

TRẢ VỀ JSON:
{{
  "hook_style": "mô tả cách viết hook",
  "body_style": {{"avg_word_count": 200, "writing_approach": "tóm tắt/kể chuyện/liệt kê", "uses_lsi_keywords": true}},
  "uses_timestamps": true,
  "timestamp_style": "mô tả phong cách timestamps nếu có",
  "cta_patterns": ["CTA 1", "CTA 2"],
  "cta_position": "top/middle/bottom/distributed",
  "hashtag_strategy": {{"avg_count": 3, "types": ["brand", "topic", "niche"]}},
  "brand_voice": {{"tone": "thân mật/trang trọng/hài hước", "vocabulary": ["từ 1", "từ 2"], "addressing": "cách xưng hô"}},
  "structure_template": "Mô tả cấu trúc mẫu cho description mới",
  "style_summary": "Tóm tắt 2-3 câu về phong cách mô tả"
}}"""
    result = ai_client.generate(prompt, temperature=0.3)
    parsed = _parse_metadata_json(result)
    return parsed if parsed else {"style_summary": result.strip(), "raw": True}


def _analyze_thumbnails_single_shot(ai_client, samples: list) -> dict:
    """Fallback: Analyze all thumbnails in a single prompt."""
    samples_text = "\n---\n".join([f"THUMBNAIL {i+1}:\n{t}" for i, t in enumerate(samples)])
    prompt = f"""Bạn là chuyên gia phân tích thumbnail YouTube. Phân tích {len(samples)} mô tả thumbnail mẫu và đúc kết thành "PHONG CÁCH THUMBNAIL".

CÁC MÔ TẢ THUMBNAIL MẪU:
{samples_text}

TRẢ VỀ JSON:
{{
  "composition": {{"layout": "rule_of_thirds/centered/asymmetric", "subject_position": "left/right/center", "visual_hierarchy": "mô tả"}},
  "color_scheme": {{"dominant_colors": ["màu 1", "màu 2"], "contrast_style": "high/medium/low", "saturation": "hyper/normal/muted", "emotional_mapping": "mô tả"}},
  "typography": {{"avg_word_count": 3, "font_style": "bold_sans_serif/custom/minimal", "effects": ["stroke", "shadow"]}},
  "emotional_signals": {{"uses_faces": true, "dominant_emotion": "shock/joy/curiosity/fear", "eye_contact": true, "exaggeration_level": "high/medium/low"}},
  "storytelling_techniques": ["before_after", "curiosity_gap", "arrows"],
  "overall_style": "professional/casual/cinematic",
  "text_strategy": "complementary/repetitive/curiosity_gap",
  "thumbnail_formula": "Công thức thumbnail đặc trưng",
  "style_summary": "Tóm tắt 2-3 câu về phong cách thumbnail"
}}"""
    result = ai_client.generate(prompt, temperature=0.3)
    parsed = _parse_metadata_json(result)
    return parsed if parsed else {"style_summary": result.strip(), "raw": True}


# ═══════════════════════════════════════════════════════════════════════════════
# SYNC REFERENCE ANALYSIS (Character / Style / Context) — SSE Streaming
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyzeSyncReferencesRequest(BaseModel):
    character_text: str = ""
    style_text: str = ""
    context_text: str = ""
    character_images: List[str] = []  # base64 data URIs
    style_images: List[str] = []
    context_images: List[str] = []
    model: Optional[str] = None
    output_language: str = "vi"


@router.post("/analyze-sync-references-stream")
async def analyze_sync_references_stream(request: AnalyzeSyncReferencesRequest):
    """
    SSE streaming endpoint to analyze sync reference inputs (character, style, context).
    For each enabled sync type, uses AI (with Vision for images) to produce
    a refined, structured description optimized for downstream prompt generation.
    """
    has_character = bool(request.character_text.strip()) or len(request.character_images) > 0
    has_style = bool(request.style_text.strip()) or len(request.style_images) > 0
    has_context = bool(request.context_text.strip()) or len(request.context_images) > 0

    if not has_character and not has_style and not has_context:
        raise HTTPException(status_code=400, detail="Cần ít nhất 1 loại sync reference")

    ai_client = get_configured_ai_client(request.model)
    lang_map = {"en": "English", "vi": "Vietnamese", "ja": "Japanese", "ko": "Korean", "zh": "Chinese"}
    lang_name = lang_map.get(request.output_language, request.output_language)

    async def stream_analysis():
        def send_event(event_type: str, data: dict) -> str:
            return f"event: {event_type}\ndata: {json_module.dumps(data, ensure_ascii=False)}\n\n"

        results = {"sync_character_analysis": None, "sync_style_analysis": None, "sync_context_analysis": None}
        total = sum([has_character, has_style, has_context])
        done_count = 0

        yield send_event("progress", {"step": "sync_init", "percentage": 0, "message": f"Bắt đầu phân tích {total} sync reference..."})

        loop = asyncio.get_event_loop()

        # ── CHARACTER ──
        if has_character:
            yield send_event("progress", {"step": "sync_character", "percentage": 5, "message": "Đang phân tích nhân vật..."})
            try:
                prompt = f"""You are a visual character description expert for AI video/image generation.
Analyze the character reference below and produce a DETAILED character description optimized for AI prompt generation.

USER INPUT:
{f'Text: {request.character_text}' if request.character_text.strip() else '(No text)'}
{f'{len(request.character_images)} reference image(s)' if request.character_images else '(No images)'}

OUTPUT a detailed character description in {lang_name} covering: physical appearance, face details, hair, clothing, expression/pose.
Format as a single cohesive paragraph (3-5 sentences). Output ONLY the description."""

                if request.character_images:
                    result = await loop.run_in_executor(None, lambda: ai_client.generate_with_images(prompt, request.character_images, temperature=0.3, max_tokens=1000))
                else:
                    result = await loop.run_in_executor(None, lambda: ai_client.generate(prompt, temperature=0.3))
                results["sync_character_analysis"] = result.strip() if result else None
                done_count += 1
                yield send_event("progress", {"step": "sync_character_done", "percentage": int((done_count / total) * 90) + 5, "message": "Hoàn tất phân tích nhân vật"})
            except Exception as e:
                logger.error(f"[SyncAnalysis] Character error: {e}")
                done_count += 1
                yield send_event("progress", {"step": "sync_character_done", "percentage": int((done_count / total) * 90) + 5, "message": f"Lỗi: {str(e)[:50]}"})

        # ── STYLE ──
        if has_style:
            yield send_event("progress", {"step": "sync_style", "percentage": int((done_count / total) * 90) + 5, "message": "Đang phân tích phong cách..."})
            try:
                prompt = f"""You are a visual style analysis expert for AI video/image generation.
Analyze the style reference below and produce a DETAILED visual style specification optimized for AI prompt generation.

USER INPUT:
{f'Text: {request.style_text}' if request.style_text.strip() else '(No text)'}
{f'{len(request.style_images)} reference image(s)' if request.style_images else '(No images)'}

OUTPUT a detailed style specification in {lang_name} covering: visual style, lighting, color palette, camera/lens, mood/atmosphere.
Format as a single cohesive paragraph (3-5 sentences). Output ONLY the description."""

                if request.style_images:
                    result = await loop.run_in_executor(None, lambda: ai_client.generate_with_images(prompt, request.style_images, temperature=0.3, max_tokens=1000))
                else:
                    result = await loop.run_in_executor(None, lambda: ai_client.generate(prompt, temperature=0.3))
                results["sync_style_analysis"] = result.strip() if result else None
                done_count += 1
                yield send_event("progress", {"step": "sync_style_done", "percentage": int((done_count / total) * 90) + 5, "message": "Hoàn tất phân tích phong cách"})
            except Exception as e:
                logger.error(f"[SyncAnalysis] Style error: {e}")
                done_count += 1
                yield send_event("progress", {"step": "sync_style_done", "percentage": int((done_count / total) * 90) + 5, "message": f"Lỗi: {str(e)[:50]}"})

        # ── CONTEXT ──
        if has_context:
            yield send_event("progress", {"step": "sync_context", "percentage": int((done_count / total) * 90) + 5, "message": "Đang phân tích bối cảnh..."})
            try:
                prompt = f"""You are a scene/environment description expert for AI video/image generation.
Analyze the context/environment reference below and produce a DETAILED environment description optimized for AI prompt generation.

USER INPUT:
{f'Text: {request.context_text}' if request.context_text.strip() else '(No text)'}
{f'{len(request.context_images)} reference image(s)' if request.context_images else '(No images)'}

OUTPUT a detailed environment description in {lang_name} covering: location type, architecture/landscape, props/details, lighting/time, atmosphere.
Format as a single cohesive paragraph (3-5 sentences). Output ONLY the description."""

                if request.context_images:
                    result = await loop.run_in_executor(None, lambda: ai_client.generate_with_images(prompt, request.context_images, temperature=0.3, max_tokens=1000))
                else:
                    result = await loop.run_in_executor(None, lambda: ai_client.generate(prompt, temperature=0.3))
                results["sync_context_analysis"] = result.strip() if result else None
                done_count += 1
                yield send_event("progress", {"step": "sync_context_done", "percentage": int((done_count / total) * 90) + 5, "message": "Hoàn tất phân tích bối cảnh"})
            except Exception as e:
                logger.error(f"[SyncAnalysis] Context error: {e}")
                done_count += 1
                yield send_event("progress", {"step": "sync_context_done", "percentage": int((done_count / total) * 90) + 5, "message": f"Lỗi: {str(e)[:50]}"})

        yield send_event("result", {"success": True, **results})

    return StreamingResponse(
        stream_analysis(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
