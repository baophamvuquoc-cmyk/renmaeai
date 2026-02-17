from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from modules.ai_automation import HybridAIClient, AIProvider, OPENAI_MODELS, DEFAULT_OPENAI_MODEL
from modules.nlp_processor import NLPProcessor
from modules.ai_settings_db import get_settings_db
import json
import re

router = APIRouter()


class AISettings(BaseModel):
    """AI Settings from frontend"""
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    openai_model: Optional[str] = None
    gemini_api_key: Optional[str] = None


class GenerateScenesRequest(BaseModel):
    script: str
    language: str = "vi"
    provider: str = "gemini_api"  # openai, gemini_api, auto
    use_smart_model: bool = False
    ai_settings: Optional[AISettings] = None


class TestConnectionRequest(BaseModel):
    provider: str = "gemini_api"
    ai_settings: Optional[AISettings] = None


class AIProviderInfo(BaseModel):
    id: str
    name: str
    description: str
    available: bool
    requires_api_key: bool


@router.get("/providers")
async def get_providers() -> List[AIProviderInfo]:
    """Get list of available AI providers - checks actual configuration"""
    # Check actual configuration from database
    settings_db = get_settings_db()
    all_settings = settings_db.get_all_settings()
    
    # Check if API keys are configured
    openai_configured = bool(
        all_settings.get('openai_api', {}).get('api_key')
    )
    gemini_configured = bool(
        all_settings.get('gemini_api', {}).get('api_key')
    )
    
    # Auto is available if any provider is configured
    auto_available = openai_configured or gemini_configured
    
    return [
        {
            "id": "openai",
            "name": "OpenAI (GPT-4o)",
            "description": "OpenAI API - Best quality, requires API key",
            "available": openai_configured,
            "requires_api_key": True
        },
        {
            "id": "gemini_api",
            "name": "Gemini API (Free)",
            "description": "Google Gemini Flash API - Fast and free",
            "available": gemini_configured,
            "requires_api_key": True
        },
        {
            "id": "auto",
            "name": "Auto (Smart Selection)",
            "description": "Automatically choose the best available provider",
            "available": auto_available,
            "requires_api_key": False
        }
    ]


@router.get("/models")
async def get_available_models():
    """Get list of available AI models - fetches from API dynamically"""
    import requests
    
    # Get settings to check configuration
    db = get_settings_db()
    all_settings = db.get_all_settings()
    openai_settings = all_settings.get('openai_api', {})
    gemini_settings = all_settings.get('gemini_api', {})
    
    base_url = openai_settings.get('base_url')
    api_key = openai_settings.get('api_key')
    saved_model = openai_settings.get('model')
    gemini_api_key = gemini_settings.get('api_key')
    
    models = []
    
    # Try to fetch models from OpenAI API or custom proxy
    if api_key:
        try:
            # Use custom base_url if configured, otherwise use official OpenAI
            endpoint = f"{base_url}/models" if base_url else "https://api.openai.com/v1/models"
            
            response = requests.get(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and isinstance(data["data"], list):
                    # Filter and format chat models
                    for m in data["data"]:
                        model_id = m.get("id", "")
                        
                        # Only include GPT and o-series chat models
                        if not any(prefix in model_id for prefix in ['gpt-4', 'gpt-3.5', 'o1', 'o3', 'chatgpt']):
                            continue
                        
                        # Skip non-chat models
                        if any(skip in model_id for skip in ['embedding', 'tts', 'whisper', 'dall-e', 'davinci', 'babbage', 'realtime', 'transcribe', 'moderation']):
                            continue
                        
                        # Get display name and description
                        display_name, description = _get_model_display_info(model_id)
                        
                        models.append({
                            "id": model_id,
                            "name": display_name,
                            "description": description,
                            "provider": "openai"
                        })
                    
                    # Sort models by priority
                    models = _sort_models(models)
                    
                    # Remove duplicates by display name
                    seen_names = set()
                    unique_models = []
                    for model in models:
                        if model["name"] not in seen_names:
                            seen_names.add(model["name"])
                            unique_models.append(model)
                    models = unique_models
                    
        except Exception as e:
            print(f"Failed to fetch models from API: {e}")
    
    # Fallback to hardcoded models if no models fetched
    if not models:
        for model_id, config in OPENAI_MODELS.items():
            models.append({
                "id": model_id,
                "name": config["name"],
                "description": config["description"],
                "provider": "openai"
            })
    
    # Add Gemini model if configured
    if gemini_api_key:
        models.append({
            "id": "gemini-2.0-flash-exp",
            "name": "Gemini 2.0 Flash",
            "description": "Fast and capable",
            "provider": "gemini_api"
        })
    
    return {
        "models": models,
        "default": saved_model or DEFAULT_OPENAI_MODEL
    }


def _get_model_display_info(model_id: str) -> tuple:
    """Get display name and description for a model ID"""
    # ═══════════════════════════════════════════════════════════════
    # GPT-5.2 Series (Latest Flagship - Feb 2026)
    # ═══════════════════════════════════════════════════════════════
    if 'gpt-5.2-pro' in model_id:
        return ("GPT-5.2 Pro", "Research-grade, most powerful")
    if 'gpt-5.2-thinking' in model_id:
        return ("GPT-5.2 Thinking", "Step-by-step reasoning")
    if 'gpt-5.2-instant' in model_id:
        return ("GPT-5.2 Instant", "Ultra-fast responses")
    if 'gpt-5.2' in model_id:
        return ("GPT-5.2 Auto", "Auto-selects best mode")
    
    # GPT-5.1 Series
    if 'gpt-5.1-pro' in model_id:
        return ("GPT-5.1 Pro", "High capability")
    if 'gpt-5.1-thinking' in model_id:
        return ("GPT-5.1 Thinking", "Reasoning mode")
    if 'gpt-5.1-instant' in model_id:
        return ("GPT-5.1 Instant", "Fast responses")
    if 'gpt-5.1' in model_id:
        return ("GPT-5.1", "Previous flagship")
    
    # ═══════════════════════════════════════════════════════════════
    # O-Series Reasoning Models
    # ═══════════════════════════════════════════════════════════════
    if 'o4-mini' in model_id:
        return ("o4-mini", "Lightweight reasoning, STEM optimized")
    if 'o3-pro' in model_id:
        return ("o3-pro", "Extended thinking, best performance")
    if 'o3-mini' in model_id:
        return ("o3-mini", "Fast reasoning, cost-effective")
    if model_id == 'o3' or model_id.startswith('o3-2'):
        return ("o3", "Advanced reasoning for coding/math")
    if 'o1-pro' in model_id:
        return ("o1-pro", "Advanced reasoning with extended thinking")
    if model_id == 'o1' or model_id.startswith('o1-2'):
        return ("o1", "Advanced reasoning model")
    if 'o1-mini' in model_id:
        return ("o1-mini", "Fast reasoning model")
    if 'o1-preview' in model_id:
        return ("o1-preview", "Preview reasoning")
    
    # ═══════════════════════════════════════════════════════════════
    # GPT-4 Series (Legacy)
    # ═══════════════════════════════════════════════════════════════
    if 'gpt-4.5' in model_id:
        return ("GPT-4.5 Preview", "Latest preview model")
    
    if 'gpt-4.1-nano' in model_id:
        return ("GPT-4.1 Nano", "Ultra-fast, lightweight")
    if 'gpt-4.1-mini' in model_id:
        return ("GPT-4.1 Mini", "Balanced speed & capability")
    if 'gpt-4.1' in model_id:
        return ("GPT-4.1", "Improved GPT-4")
    
    if 'gpt-4o-audio' in model_id:
        return ("GPT-4o Audio", "Audio input/output")
    if 'gpt-4o-mini-audio' in model_id:
        return ("GPT-4o Mini Audio", "Fast audio model")
    if 'gpt-4o-search' in model_id:
        return ("GPT-4o Search", "Web search enabled")
    if 'gpt-4o-mini' in model_id:
        return ("GPT-4o Mini", "Fast and affordable")
    if 'chatgpt-4o-latest' in model_id:
        return ("ChatGPT-4o Latest", "Dynamic ChatGPT model")
    if model_id == 'gpt-4o' or 'gpt-4o-2024' in model_id:
        return ("GPT-4o", "Multimodal model (legacy flagship)")
    
    if 'gpt-4-turbo-preview' in model_id:
        return ("GPT-4 Turbo Preview", "Latest GPT-4 preview")
    if 'gpt-4-turbo' in model_id:
        return ("GPT-4 Turbo", "Fast GPT-4")
    
    if model_id == 'gpt-4' or model_id.startswith('gpt-4-0'):
        return ("GPT-4", "Original GPT-4")
    
    if 'gpt-3.5-turbo' in model_id:
        return ("GPT-3.5 Turbo", "Fast, budget option")
    
    # Default
    return (model_id, "OpenAI model")


def _sort_models(models: list) -> list:
    """Sort models by priority: gpt-5 -> o-series -> gpt-4 -> gpt-3.5"""
    def sort_key(m):
        model_id = m["id"]
        # GPT-5 Series (Highest priority)
        if "gpt-5.2" in model_id:
            return (0, model_id)
        if "gpt-5.1" in model_id:
            return (1, model_id)
        if "gpt-5" in model_id:
            return (2, model_id)
        # O-Series Reasoning
        if model_id.startswith("o4"):
            return (3, model_id)
        if model_id.startswith("o3"):
            return (4, model_id)
        if model_id.startswith("o1"):
            return (5, model_id)
        # GPT-4 Series (Legacy)
        if "gpt-4.5" in model_id:
            return (6, model_id)
        if "gpt-4.1" in model_id:
            return (7, model_id)
        if "gpt-4o" in model_id or "chatgpt-4o" in model_id:
            return (8, model_id)
        if "gpt-4-turbo" in model_id:
            return (9, model_id)
        if "gpt-4" in model_id:
            return (10, model_id)
        if "gpt-3.5" in model_id:
            return (11, model_id)
        return (99, model_id)
    
    return sorted(models, key=sort_key)


@router.post("/generate")
async def generate_scenes_with_ai(request: GenerateScenesRequest):
    """
    Generate scenes from script using selected AI provider
    
    This endpoint uses the Hybrid AI Client to route requests to:
    - OpenAI API (GPT-4o) for high quality
    - Gemini API for fast and free processing
    """
    try:
        # Map string provider to enum
        provider_map = {
            "openai": AIProvider.OPENAI,
            "gemini_api": AIProvider.GEMINI_API,
            "auto": AIProvider.AUTO
        }
        
        provider = provider_map.get(request.provider, AIProvider.GEMINI_API)
        
        # Initialize Hybrid AI Client with settings from request or env
        ai_settings = request.ai_settings
        ai_client = HybridAIClient(
            openai_api_key=ai_settings.openai_api_key if ai_settings else None,
            openai_base_url=ai_settings.openai_base_url if ai_settings else None,
            openai_model=ai_settings.openai_model if ai_settings else None,
            gemini_api_key=ai_settings.gemini_api_key if ai_settings else None
        )
        
        # Create optimized prompt for scene generation
        prompt = f"""
Bạn là một AI chuyên về video production. Hãy phân tích kịch bản sau và chia thành các scenes.

Mỗi scene cần có:
- scene_id: số thứ tự
- duration: thời lượng tính bằng giây (3-7 giây)
- voiceover: lời thoại/bình luận cho scene này
- visual_query: từ khóa tìm kiếm stock footage (tiếng Anh, ngắn gọn)
- ai_prompt: mô tả chi tiết để tạo video AI (tiếng Anh, cinematic)
- mood: phong cách/tâm trạng (ví dụ: cinematic, energetic, calm)

Trả về CHÍNH XÁC định dạng JSON array, không có text khác:

Kịch bản:
{request.script}

JSON output:
"""
        
        # Generate with AI
        response_text = ai_client.generate(
            prompt=prompt,
            provider=provider,
            use_smart_model=request.use_smart_model,
            temperature=0.7
        )
        
        # Parse JSON from response
        scenes = _extract_json_from_response(response_text)
        
        if not scenes:
            # Fallback to NLP processor if AI fails
            print("AI response didn't contain valid JSON, using fallback...")
            nlp = NLPProcessor()
            scenes = nlp._fallback_scene_generation(request.script)
        
        return {
            "success": True,
            "scenes": scenes,
            "provider_used": request.provider,
            "scene_count": len(scenes)
        }
        
    except Exception as e:
        print(f"Error in generate_scenes_with_ai: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test-connection")
async def test_ai_connection(request: TestConnectionRequest):
    """Test connection to specified AI provider"""
    try:
        provider_map = {
            "openai": AIProvider.OPENAI,
            "gemini_api": AIProvider.GEMINI_API,
            "auto": AIProvider.AUTO
        }
        
        provider = provider_map.get(request.provider, AIProvider.GEMINI_API)
        
        # Load settings from database if not provided in request
        ai_settings = request.ai_settings
        if not ai_settings or (not ai_settings.openai_api_key and not ai_settings.gemini_api_key):
            # Load from database — respect active_provider setting
            settings_db = get_settings_db()
            all_settings = settings_db.get_all_settings()
            # active_provider is in app_settings table, not ai_settings
            active_provider = settings_db.get_active_provider()
            
            openai_api_key = None
            openai_base_url = None
            openai_model = None
            gemini_api_key = None
            
            if active_provider == 'custom':
                custom_settings = all_settings.get('custom_api', {})
                openai_api_key = custom_settings.get('api_key')
                openai_base_url = custom_settings.get('base_url')
                openai_model = custom_settings.get('model')
            elif active_provider == 'openai':
                openai_settings = all_settings.get('openai_api', {})
                openai_api_key = openai_settings.get('api_key')
                openai_base_url = openai_settings.get('base_url')
                openai_model = openai_settings.get('model')
            elif active_provider == 'gemini_api':
                gemini_api_key = all_settings.get('gemini_api', {}).get('api_key')
            else:
                openai_api_key = all_settings.get('openai_api', {}).get('api_key')
                openai_base_url = all_settings.get('openai_api', {}).get('base_url')
                openai_model = all_settings.get('openai_api', {}).get('model')
                gemini_api_key = all_settings.get('gemini_api', {}).get('api_key')
            
            ai_client = HybridAIClient(
                openai_api_key=openai_api_key,
                openai_base_url=openai_base_url,
                openai_model=openai_model,
                gemini_api_key=gemini_api_key
            )
        else:
            # Use settings from request
            ai_client = HybridAIClient(
                openai_api_key=ai_settings.openai_api_key,
                openai_base_url=ai_settings.openai_base_url,
                openai_model=ai_settings.openai_model,
                gemini_api_key=ai_settings.gemini_api_key
            )
        
        result = ai_client.test_connection(provider)
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "provider": request.provider,
            "error": str(e)
        }


def _extract_json_from_response(text: str) -> Optional[List[Dict]]:
    """
    Extract JSON array from AI response text
    Handles cases where AI includes markdown formatting or extra text
    """
    try:
        # Remove markdown code blocks if present
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Try to find JSON array in response
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            scenes = json.loads(json_match.group())
            
            # Validate scene structure
            if isinstance(scenes, list) and len(scenes) > 0:
                required_fields = ['scene_id', 'voiceover', 'visual_query']
                if all(field in scenes[0] for field in required_fields):
                    return scenes
        
        return None
        
    except (json.JSONDecodeError, Exception) as e:
        print(f"Error parsing JSON from AI response: {e}")
        return None
