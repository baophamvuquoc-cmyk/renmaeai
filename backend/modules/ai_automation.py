"""
AI Automation Module - Direct API Integration

Integrates:
1. OpenAI API (GPT-4o, GPT-4o-mini)
2. Gemini API (gemini-2.0-flash-exp)
"""

from enum import Enum
from typing import Optional, List
import os
from dotenv import load_dotenv
from .logging_config import get_automation_logger
from .exceptions import (
    ProviderNotConfiguredError,
    AllProvidersFailedError,
)

load_dotenv()

# Initialize logger
logger = get_automation_logger()

# Lazy-load google.generativeai to prevent blocking server startup
_genai = None

def _get_genai():
    """Lazy import google.generativeai to avoid blocking on startup."""
    global _genai
    if _genai is None:
        import google.generativeai as genai
        _genai = genai
    return _genai


class AIProvider(Enum):
    OPENAI = "openai"  # OpenAI API (GPT-4o, GPT-4o-mini)
    GEMINI_API = "gemini_api"  # Google Gemini API
    AUTO = "auto"  # Automatic selection


# OpenAI available models - Unified with frontend (Feb 2026)
# Primary source of truth for fallback model list
OPENAI_MODELS = {
    # ═══════════════════════════════════════════════════════════════
    # GPT-5.2 Series (Latest Flagship - Feb 2026)
    # ═══════════════════════════════════════════════════════════════
    "gpt-5.2": {"name": "GPT-5.2 Auto", "description": "Auto-selects best mode"},
    "gpt-5.2-pro": {"name": "GPT-5.2 Pro", "description": "Research-grade, most powerful"},
    "gpt-5.2-thinking": {"name": "GPT-5.2 Thinking", "description": "Step-by-step reasoning"},
    "gpt-5.2-instant": {"name": "GPT-5.2 Instant", "description": "Ultra-fast responses"},
    # GPT-5.1 Series
    "gpt-5.1": {"name": "GPT-5.1", "description": "Previous flagship"},
    "gpt-5.1-pro": {"name": "GPT-5.1 Pro", "description": "High capability"},
    "gpt-5.1-thinking": {"name": "GPT-5.1 Thinking", "description": "Reasoning mode"},
    "gpt-5.1-instant": {"name": "GPT-5.1 Instant", "description": "Fast responses"},
    # ═══════════════════════════════════════════════════════════════
    # O-Series Reasoning Models
    # ═══════════════════════════════════════════════════════════════
    "o4-mini": {"name": "o4-mini", "description": "Lightweight reasoning, STEM optimized"},
    "o3": {"name": "o3", "description": "Advanced reasoning for coding/math"},
    "o3-pro": {"name": "o3-pro", "description": "Extended thinking, best performance"},
    "o3-mini": {"name": "o3-mini", "description": "Fast reasoning, cost-effective"},
    "o1": {"name": "o1", "description": "Advanced reasoning, complex tasks"},
    "o1-mini": {"name": "o1-mini", "description": "Faster reasoning model"},
    "o1-preview": {"name": "o1-preview", "description": "Preview of o1 reasoning"},
    # ═══════════════════════════════════════════════════════════════
    # GPT-4 Series (Legacy - still available via API)
    # ═══════════════════════════════════════════════════════════════
    "gpt-4.5-preview": {"name": "GPT-4.5 Preview", "description": "Latest preview model"},
    "gpt-4.1": {"name": "GPT-4.1", "description": "Improved GPT-4 variant"},
    "gpt-4.1-mini": {"name": "GPT-4.1 Mini", "description": "Faster GPT-4.1"},
    "gpt-4.1-nano": {"name": "GPT-4.1 Nano", "description": "Ultra-fast, lightweight"},
    "gpt-4o": {"name": "GPT-4o", "description": "Multimodal model (legacy flagship)"},
    "gpt-4o-mini": {"name": "GPT-4o Mini", "description": "Fast and affordable"},
    "chatgpt-4o-latest": {"name": "ChatGPT-4o Latest", "description": "Dynamic ChatGPT model"},
    "gpt-4o-audio-preview": {"name": "GPT-4o Audio", "description": "Audio input/output"},
    "gpt-4-turbo": {"name": "GPT-4 Turbo", "description": "Previous generation turbo"},
    "gpt-4-turbo-preview": {"name": "GPT-4 Turbo Preview", "description": "Latest GPT-4 preview"},
    "gpt-4": {"name": "GPT-4", "description": "Original GPT-4"},
    "gpt-3.5-turbo": {"name": "GPT-3.5 Turbo", "description": "Fast, budget option"},
}

# Default model - synced with frontend useAISettingsStore.ts
DEFAULT_OPENAI_MODEL = "gpt-5.2"


class OpenAIClient:
    """OpenAI API Client"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")  # Optional custom endpoint
        self.client = None
        self.model = model or os.getenv("OPENAI_MODEL") or DEFAULT_OPENAI_MODEL
        self._conversations: dict = {}
        
        if self.api_key:
            try:
                from openai import OpenAI
                # Use custom base_url if provided (for Azure, local models, etc.)
                # Add 60 second timeout to prevent hanging
                if self.base_url:
                    self.client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=180.0)
                else:
                    self.client = OpenAI(api_key=self.api_key, timeout=180.0)
            except ImportError:
                logger.warning("OpenAI package not installed. Run: pip install openai")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.client)

    def generate(self, prompt: str, model: Optional[str] = None, temperature: float = 0.7) -> str:
        """Generate response using OpenAI API with model fallback"""
        if not self.is_configured():
            raise Exception("OpenAI API key not configured")

        use_model = model or self.model
        logger.info(f"[OpenAI.generate] Calling model={use_model}, prompt_len={len(prompt)}")
        
        # Build fallback model list
        models_to_try = [use_model]
        # Add fallback models - try same family first, then cross-provider
        primary = use_model.lower()
        fallbacks = []
        if "gpt" in primary:
            fallbacks = ["gpt-5.1", "gpt-5", "gpt-4o", "gpt-4o-mini", "gemini-2.5-flash", "claude-sonnet-4-5"]
        elif "gemini" in primary:
            fallbacks = ["gemini-2.5-flash", "gemini-3-flash", "gpt-5.1", "gpt-5"]
        elif "claude" in primary:
            fallbacks = ["claude-sonnet-4-5", "gemini-2.5-flash", "gpt-5.1", "gpt-5"]
        for fb in fallbacks:
            if fb.lower() != primary and fb not in models_to_try:
                models_to_try.append(fb)
        
        last_error = None
        for model_attempt in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_attempt,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                )
                result = response.choices[0].message.content
                if model_attempt != use_model:
                    logger.warning(f"[OpenAI.generate] Model '{use_model}' failed, used '{model_attempt}' instead")
                    self.model = model_attempt  # Update default for future calls
                logger.info(f"[OpenAI.generate] Got response of {len(result)} chars (model={model_attempt})")
                return result
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_model_error = any(x in error_str for x in ['model', '404', '500', 'not found', 'server_error', 'internal'])
                if is_model_error and model_attempt != models_to_try[-1]:
                    logger.warning(f"[OpenAI.generate] Model '{model_attempt}' failed ({e}), trying next...")
                    continue
                break
        
        logger.error(f"[OpenAI.generate] All models failed. Last error: {last_error}")
        raise Exception(f"OpenAI API error: {str(last_error)}")

    def generate_with_images(
        self,
        prompt: str,
        image_urls: list[str],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate response using AI Vision — sends text + images.

        Args:
            prompt: Text prompt describing what to analyze
            image_urls: List of image URLs or base64 data URIs
            model: Specific model (default: self.model)
            temperature: Lower = more deterministic ranking
            max_tokens: Max response tokens

        Returns:
            AI response text
        """
        if not self.is_configured():
            raise Exception("OpenAI API key not configured")

        use_model = model or self.model
        logger.info(f"[OpenAI.vision] model={use_model}, images={len(image_urls)}, prompt_len={len(prompt)}")

        # Build multimodal content: text + images
        content = [{"type": "text", "text": prompt}]
        for img_url in image_urls:
            content.append({
                "type": "image_url",
                "image_url": {"url": img_url, "detail": "low"},
            })

        # Fallback model list (vision-capable only)
        models_to_try = [use_model]
        primary = use_model.lower()
        fallbacks = []
        if "gpt" in primary:
            fallbacks = ["gpt-5.1", "gpt-5", "gpt-4o", "gemini-2.5-flash", "claude-sonnet-4-5"]
        elif "gemini" in primary:
            fallbacks = ["gemini-2.5-flash", "gemini-3-flash", "gpt-5.1", "gpt-5"]
        elif "claude" in primary:
            fallbacks = ["claude-sonnet-4-5", "gemini-2.5-flash", "gpt-5.1", "gpt-5"]
        for fb in fallbacks:
            if fb.lower() != primary and fb not in models_to_try:
                models_to_try.append(fb)

        last_error = None
        for model_attempt in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_attempt,
                    messages=[{"role": "user", "content": content}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                result = response.choices[0].message.content
                if model_attempt != use_model:
                    logger.warning(f"[OpenAI.vision] Fallback: '{use_model}' -> '{model_attempt}'")
                logger.info(f"[OpenAI.vision] Response {len(result)} chars (model={model_attempt})")
                return result
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_model_error = any(x in error_str for x in ['model', '404', '500', 'not found', 'server_error', 'internal'])
                if is_model_error and model_attempt != models_to_try[-1]:
                    logger.warning(f"[OpenAI.vision] Model '{model_attempt}' failed ({e}), trying next...")
                    continue
                break

        logger.error(f"[OpenAI.vision] All models failed. Last error: {last_error}")
        raise Exception(f"OpenAI Vision API error: {str(last_error)}")

    def start_conversation(self, system_prompt: str = None) -> str:
        """
        Start a new chat conversation session.
        
        Args:
            system_prompt: Optional system message to set context for the conversation
        
        Returns:
            conversation_id: Unique identifier for this conversation
        """
        if not self.is_configured():
            raise Exception("OpenAI API key not configured")
        
        import uuid
        conversation_id = str(uuid.uuid4())
        
        # Initialize conversation history with optional system prompt
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        self._conversations[conversation_id] = {
            "messages": messages,
            "model": self.model
        }
        
        logger.info(f"Started OpenAI conversation: {conversation_id[:8]}... (system: {bool(system_prompt)})")
        return conversation_id

    def send_message(self, conversation_id: str, message: str, temperature: float = 0.7) -> str:
        """
        Send a message within an existing conversation.
        Includes model fallback and threading-based timeout to prevent hanging.
        
        Args:
            conversation_id: ID from start_conversation()
            message: The message to send
            temperature: Response temperature
            
        Returns:
            AI response text
        """
        import threading
        
        if conversation_id not in self._conversations:
            raise Exception(f"Conversation {conversation_id} not found")
        
        conv = self._conversations[conversation_id]
        conv["messages"].append({"role": "user", "content": message})
        
        msg_count = len(conv["messages"])
        prompt_preview = message[:80].replace('\n', ' ')
        logger.info(f"[OpenAI.send_message] conv={conversation_id[:8]}, msg#{msg_count}, model={conv['model']}, prompt='{prompt_preview}...'")
        
        # Try primary model first, then fallbacks
        models_to_try = [conv["model"]]
        primary = conv["model"].lower()
        fallbacks = []
        if "gpt" in primary:
            fallbacks = ["gpt-5.1", "gpt-5", "gpt-4o", "gpt-4o-mini", "gemini-2.5-flash", "claude-sonnet-4-5"]
        elif "gemini" in primary:
            fallbacks = ["gemini-2.5-flash", "gemini-3-flash", "gpt-5.1", "gpt-5"]
        elif "claude" in primary:
            fallbacks = ["claude-sonnet-4-5", "gemini-2.5-flash", "gpt-5.1", "gpt-5"]
        for fb in fallbacks:
            if fb.lower() != primary and fb not in models_to_try:
                models_to_try.append(fb)
        
        last_error = None
        for model_attempt in models_to_try:
            # Use threading to implement request-level timeout (prevents infinite hang)
            result_container = {"response": None, "error": None}
            completed = threading.Event()
            
            def _call_openai(model=model_attempt):
                try:
                    response = self.client.chat.completions.create(
                        model=model,
                        messages=conv["messages"],
                        temperature=temperature,
                    )
                    result_container["response"] = response
                except Exception as e:
                    result_container["error"] = e
                finally:
                    completed.set()
            
            thread = threading.Thread(target=_call_openai, daemon=True)
            thread.start()
            
            # Wait up to 180 seconds for API to respond
            if not completed.wait(timeout=180):
                logger.error(f"[OpenAI.send_message] TIMEOUT after 180s waiting for model '{model_attempt}'")
                last_error = Exception(f"OpenAI API timeout: No response after 180 seconds (model={model_attempt})")
                # Try next model
                continue
            
            if result_container["error"]:
                last_error = result_container["error"]
                error_str = str(last_error).lower()
                is_model_error = any(x in error_str for x in ['model', '404', '500', 'not found', 'server_error', 'internal'])
                if is_model_error and model_attempt != models_to_try[-1]:
                    logger.warning(f"[OpenAI.send_message] Model '{model_attempt}' failed ({last_error}), trying next...")
                    continue
                else:
                    break
            
            response = result_container["response"]
            assistant_message = response.choices[0].message.content
            conv["messages"].append({"role": "assistant", "content": assistant_message})
            
            if model_attempt != conv["model"]:
                logger.warning(f"[OpenAI.send_message] Model '{conv['model']}' failed, switched to '{model_attempt}'")
                conv["model"] = model_attempt
            
            logger.info(f"[OpenAI.send_message] Got {len(assistant_message)} chars response (model={model_attempt})")
            return assistant_message
        
        logger.error(f"[OpenAI.send_message] All models failed. Last error: {last_error}")
        # Remove the failed user message from history so conversation stays valid
        if conv["messages"] and conv["messages"][-1]["role"] == "user":
            conv["messages"].pop()
        raise Exception(f"OpenAI conversation error: {str(last_error)}")

    def end_conversation(self, conversation_id: str) -> None:
        """
        End a conversation and cleanup resources.
        
        Args:
            conversation_id: ID from start_conversation()
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info(f"Ended OpenAI conversation: {conversation_id[:8]}...")

    def list_models(self) -> list:
        """
        Fetch available models from OpenAI API.
        
        Returns:
            List of model objects with id, name, description
        """
        if not self.is_configured():
            return []
        
        try:
            # Fetch models from API
            models_response = self.client.models.list()
            
            # Filter and format chat models only
            chat_models = []
            for model in models_response.data:
                model_id = model.id
                # Only include GPT and o-series chat models
                if any(prefix in model_id for prefix in ['gpt-4', 'gpt-3.5', 'o1', 'o3', 'chatgpt']):
                    # Skip embedding, tts, whisper, dall-e models
                    if any(skip in model_id for skip in ['embedding', 'tts', 'whisper', 'dall-e', 'davinci', 'babbage', 'realtime', 'transcribe']):
                        continue
                    
                    # Create display name and description
                    display_name = model_id
                    description = ""
                    
                    # Enhanced naming based on model type
                    if 'o3-mini' in model_id:
                        display_name = "o3-mini"
                        description = "Latest reasoning model"
                    elif 'o1-pro' in model_id:
                        display_name = "o1-pro"
                        description = "Advanced reasoning with extended thinking"
                    elif 'o1-mini' in model_id:
                        display_name = "o1-mini"
                        description = "Fast reasoning model"
                    elif 'o1-preview' in model_id:
                        display_name = "o1-preview"
                        description = "Preview reasoning model"
                    elif model_id == 'o1':
                        display_name = "o1"
                        description = "Advanced reasoning model"
                    elif 'gpt-4.5' in model_id:
                        display_name = "GPT-4.5 Preview"
                        description = "Latest preview model"
                    elif 'gpt-4.1-nano' in model_id:
                        display_name = "GPT-4.1 Nano"
                        description = "Ultra-fast, lightweight"
                    elif 'gpt-4.1-mini' in model_id:
                        display_name = "GPT-4.1 Mini"
                        description = "Balanced speed & capability"
                    elif 'gpt-4.1' in model_id:
                        display_name = "GPT-4.1"
                        description = "Improved GPT-4"
                    elif 'gpt-4o-audio' in model_id:
                        display_name = "GPT-4o Audio"
                        description = "Audio input/output"
                    elif 'gpt-4o-mini-audio' in model_id:
                        display_name = "GPT-4o Mini Audio"
                        description = "Fast audio model"
                    elif 'gpt-4o-mini' in model_id:
                        display_name = "GPT-4o Mini"
                        description = "Fast and affordable"
                    elif 'gpt-4o-search' in model_id:
                        display_name = "GPT-4o Search"
                        description = "Web search enabled"
                    elif 'chatgpt-4o-latest' in model_id:
                        display_name = "ChatGPT-4o Latest"
                        description = "Dynamic ChatGPT model"
                    elif model_id == 'gpt-4o' or 'gpt-4o-2024' in model_id:
                        display_name = "GPT-4o"
                        description = "Multimodal flagship model"
                    elif 'gpt-4-turbo-preview' in model_id:
                        display_name = "GPT-4 Turbo Preview"
                        description = "Latest GPT-4 preview"
                    elif 'gpt-4-turbo' in model_id:
                        display_name = "GPT-4 Turbo"
                        description = "Fast GPT-4"
                    elif model_id == 'gpt-4' or 'gpt-4-0' in model_id:
                        display_name = "GPT-4"
                        description = "Original GPT-4"
                    elif 'gpt-3.5-turbo' in model_id:
                        display_name = "GPT-3.5 Turbo"
                        description = "Fast, budget option"
                    else:
                        description = "OpenAI model"
                    
                    chat_models.append({
                        "id": model_id,
                        "name": display_name,
                        "description": description,
                        "provider": "openai"
                    })
            
            # Sort models: o-series first, then gpt-4.x, then gpt-4o, then gpt-4, then gpt-3.5
            def model_sort_key(m):
                model_id = m["id"]
                if model_id.startswith("o3"):
                    return (0, model_id)
                if model_id.startswith("o1"):
                    return (1, model_id)
                if "gpt-4.5" in model_id:
                    return (2, model_id)
                if "gpt-4.1" in model_id:
                    return (3, model_id)
                if "gpt-4o" in model_id or "chatgpt-4o" in model_id:
                    return (4, model_id)
                if "gpt-4-turbo" in model_id:
                    return (5, model_id)
                if "gpt-4" in model_id:
                    return (6, model_id)
                if "gpt-3.5" in model_id:
                    return (7, model_id)
                return (8, model_id)
            
            chat_models.sort(key=model_sort_key)
            
            # Remove duplicates based on display name (keep first occurrence)
            seen_names = set()
            unique_models = []
            for model in chat_models:
                if model["name"] not in seen_names:
                    seen_names.add(model["name"])
                    unique_models.append(model)
            
            logger.info(f"Fetched {len(unique_models)} chat models from OpenAI API")
            return unique_models
            
        except Exception as e:
            logger.warning(f"Failed to fetch models from API: {e}")
            # Fallback to hardcoded list
            return [
                {"id": model_id, "name": info["name"], "description": info["description"], "provider": "openai"}
                for model_id, info in OPENAI_MODELS.items()
            ]

    def test_connection(self) -> dict:
        """Test OpenAI API connection with model fallback"""
        if not self.is_configured():
            return {
                "success": False,
                "message": "OpenAI API key not configured"
            }
        
        # Build fallback model list same as generate/send_message
        models_to_try = [self.model]
        primary = self.model.lower()
        fallbacks = []
        if "gpt" in primary:
            fallbacks = ["gpt-5.1", "gpt-5", "gpt-4o", "gpt-4o-mini", "gemini-2.5-flash", "claude-sonnet-4-5"]
        elif "gemini" in primary:
            fallbacks = ["gemini-2.5-flash", "gemini-3-flash", "gpt-5.1", "gpt-5"]
        elif "claude" in primary:
            fallbacks = ["claude-sonnet-4-5", "gemini-2.5-flash", "gpt-5.1", "gpt-5"]
        for fb in fallbacks:
            if fb.lower() != primary and fb not in models_to_try:
                models_to_try.append(fb)
        
        last_error = None
        for model_attempt in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_attempt,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_tokens=5
                )
                msg = f"Connected successfully (model: {model_attempt})"
                if model_attempt != self.model:
                    msg += f" [fallback from {self.model}]"
                    self.model = model_attempt  # Update for future calls
                return {
                    "success": True,
                    "message": msg,
                    "response": response.choices[0].message.content,
                    "model_used": model_attempt
                }
            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                is_model_error = any(x in error_str for x in ['model', '404', '500', 'not found', 'server_error', 'internal'])
                if is_model_error and model_attempt != models_to_try[-1]:
                    logger.warning(f"[OpenAI.test_connection] Model '{model_attempt}' failed ({e}), trying next...")
                    continue
                break
        
        return {
            "success": False,
            "message": f"Connection failed: {str(last_error)}"
        }



class GeminiAPIClient:
    """Official Gemini API Client"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            _get_genai().configure(api_key=self.api_key)
            self.model = _get_genai().GenerativeModel('gemini-2.0-flash-exp')
        else:
            self.model = None
        # Store active chat sessions for conversation management
        self._conversations: dict = {}

    def is_configured(self) -> bool:
        return self.api_key is not None and self.model is not None

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate response using Gemini API"""
        if not self.is_configured():
            raise Exception("Gemini API key not configured")

        try:
            response = self.model.generate_content(
                prompt,
                generation_config=_get_genai().types.GenerationConfig(
                    temperature=temperature
                )
            )
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API error: {str(e)}")

    def generate_with_video(
        self,
        prompt: str,
        video_path: str,
        temperature: float = 0.3,
    ) -> str:
        """
        Analyze a video file using Gemini's native video understanding.

        Uploads the video via genai.upload_file(), waits for processing,
        then sends it with the text prompt.

        Args:
            prompt: Text prompt for analysis
            video_path: Local path to video file
            temperature: Lower = more deterministic

        Returns:
            AI response text
        """
        if not self.is_configured():
            raise Exception("Gemini API key not configured")

        import threading
        import time as time_mod

        logger.info(f"[Gemini.vision] Uploading video: {video_path}")

        result_container = {"response": None, "error": None}
        completed = threading.Event()
        uploaded_file = None

        def _analyze():
            nonlocal uploaded_file
            try:
                # Upload video to Gemini
                uploaded_file = _get_genai().upload_file(video_path)
                logger.info(f"[Gemini.vision] Uploaded: {uploaded_file.name}, waiting for processing...")

                # Wait for video processing
                while uploaded_file.state.name == "PROCESSING":
                    time_mod.sleep(2)
                    uploaded_file = _get_genai().get_file(uploaded_file.name)

                if uploaded_file.state.name != "ACTIVE":
                    raise Exception(f"Video processing failed: state={uploaded_file.state.name}")

                logger.info(f"[Gemini.vision] Video ready, generating response...")

                # Send video + prompt to model
                response = self.model.generate_content(
                    [uploaded_file, prompt],
                    generation_config=_get_genai().types.GenerationConfig(
                        temperature=temperature
                    ),
                )
                result_container["response"] = response.text

            except Exception as e:
                result_container["error"] = e
            finally:
                # Cleanup: delete uploaded file from Gemini
                if uploaded_file:
                    try:
                        _get_genai().delete_file(uploaded_file.name)
                        logger.debug(f"[Gemini.vision] Cleaned up: {uploaded_file.name}")
                    except Exception:
                        pass
                completed.set()

        thread = threading.Thread(target=_analyze, daemon=True)
        thread.start()

        # Wait up to 180 seconds
        if not completed.wait(timeout=180):
            logger.error("[Gemini.vision] TIMEOUT after 180s")
            raise Exception("Gemini video analysis timeout: No response after 180 seconds")

        if result_container["error"]:
            raise Exception(f"Gemini video analysis error: {result_container['error']}")

        response_text = result_container["response"]
        logger.info(f"[Gemini.vision] Response: {len(response_text)} chars")
        return response_text

    def start_conversation(self) -> str:
        """
        Start a new chat conversation session.
        
        Returns:
            conversation_id: Unique identifier for this conversation
        """
        if not self.is_configured():
            raise Exception("Gemini API key not configured")
        
        import uuid
        conversation_id = str(uuid.uuid4())
        
        # Create a new chat session
        chat = self.model.start_chat(history=[])
        self._conversations[conversation_id] = chat
        
        logger.info(f"Started Gemini conversation: {conversation_id[:8]}...")
        return conversation_id
    
    def send_message(self, conversation_id: str, message: str, temperature: float = 0.7) -> str:
        """
        Send a message within an existing conversation.
        Uses threading timeout to prevent hanging forever.
        
        Args:
            conversation_id: ID from start_conversation()
            message: The message to send
            temperature: Response temperature
            
        Returns:
            AI response text
        """
        import threading
        
        if conversation_id not in self._conversations:
            raise Exception(f"Conversation {conversation_id} not found")
        
        chat = self._conversations[conversation_id]
        prompt_preview = message[:80].replace('\n', ' ')
        logger.info(f"[Gemini.send_message] conv={conversation_id[:8]}, prompt='{prompt_preview}...'")
        
        # Use a threading event + container to implement timeout
        result_container = {"response": None, "error": None}
        completed = threading.Event()
        
        def _call_gemini():
            try:
                response = chat.send_message(
                    message,
                    generation_config=_get_genai().types.GenerationConfig(
                        temperature=temperature
                    )
                )
                result_container["response"] = response.text
            except Exception as e:
                result_container["error"] = e
            finally:
                completed.set()
        
        thread = threading.Thread(target=_call_gemini, daemon=True)
        thread.start()
        
        # Wait up to 180 seconds for Gemini to respond
        if not completed.wait(timeout=180):
            logger.error(f"[Gemini.send_message] TIMEOUT after 180s")
            raise Exception("Gemini API timeout: No response after 180 seconds")
        
        if result_container["error"]:
            logger.error(f"[Gemini.send_message] Error: {result_container['error']}")
            raise Exception(f"Gemini conversation error: {str(result_container['error'])}")
        
        response_text = result_container["response"]
        logger.info(f"[Gemini.send_message] Got {len(response_text)} chars response")
        return response_text
    
    def end_conversation(self, conversation_id: str) -> None:
        """
        End a conversation and cleanup resources.
        
        Args:
            conversation_id: ID from start_conversation()
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info(f"Ended Gemini conversation: {conversation_id[:8]}...")

    def test_connection(self) -> dict:
        """Test Gemini API connection"""
        if not self.is_configured():
            return {
                "success": False,
                "message": "Gemini API key not configured"
            }
        
        try:
            response = self.model.generate_content("Hello, respond with 'OK'")
            return {
                "success": True,
                "message": "Gemini API connected successfully",
                "response": response.text
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }


class HybridAIClient:
    """Main AI Client with OpenAI + Gemini API Support"""

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        openai_base_url: Optional[str] = None,
        openai_model: Optional[str] = None,
        gemini_api_key: Optional[str] = None,
        # Legacy parameters (kept for backward compatibility, but unused)
        gpm_api_token: Optional[str] = None,
        chatgpt_profile_id: Optional[str] = None,
        gemini_profile_id: Optional[str] = None
    ):
        self.openai = OpenAIClient(openai_api_key, base_url=openai_base_url, model=openai_model)
        self.gemini_api = GeminiAPIClient(gemini_api_key)
        self._conversation_providers: dict = {}  # Track which provider owns each conversation
        
        # Set default provider based on what's configured
        if self.openai.is_configured():
            self.default_provider = AIProvider.OPENAI
        elif self.gemini_api.is_configured():
            self.default_provider = AIProvider.GEMINI_API
        else:
            self.default_provider = AIProvider.AUTO

    def generate(
        self,
        prompt: str,
        provider: AIProvider = AIProvider.AUTO,
        use_smart_model: bool = True,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """
        Generate response using specified provider
        
        Args:
            prompt: The prompt to send
            provider: Which AI provider to use
            use_smart_model: Whether to fallback to another provider on failure
            temperature: Response temperature
            model: Specific model to use (for OpenAI)
        """
        logger.info(f"[HybridAI.generate] Called with provider={provider.value}")
        logger.info(f"[HybridAI.generate] OpenAI configured: {self.openai.is_configured()}")
        logger.info(f"[HybridAI.generate] Gemini configured: {self.gemini_api.is_configured()}")
        
        # Auto-select provider
        if provider == AIProvider.AUTO:
            if self.openai.is_configured():
                provider = AIProvider.OPENAI
            elif self.gemini_api.is_configured():
                provider = AIProvider.GEMINI_API
            else:
                raise AllProvidersFailedError(["openai", "gemini_api"])
        
        logger.info(f"[HybridAI.generate] Final provider: {provider.value}")

        # Try primary provider
        try:
            if provider == AIProvider.OPENAI:
                if not self.openai.is_configured():
                    raise ProviderNotConfiguredError("openai")
                logger.info(f"[HybridAI.generate] Calling OpenAI with model={self.openai.model}...")
                result = self.openai.generate(prompt, model=model, temperature=temperature)
                logger.info(f"[HybridAI.generate] OpenAI returned {len(result)} chars")
                return result
            
            elif provider == AIProvider.GEMINI_API:
                if not self.gemini_api.is_configured():
                    raise ProviderNotConfiguredError("gemini_api")
                logger.info(f"[HybridAI.generate] Calling Gemini API...")
                result = self.gemini_api.generate(prompt, temperature)
                logger.info(f"[HybridAI.generate] Gemini returned {len(result)} chars")
                return result
            
            else:
                raise Exception(f"Unknown provider: {provider}")
                
        except Exception as e:
            logger.error(f"[HybridAI.generate] Error from {provider.value}: {e}")
            # Fallback to other provider if enabled
            if use_smart_model:
                logger.warning(f"{provider.value} failed, trying fallback: {e}")
                
                if provider == AIProvider.OPENAI and self.gemini_api.is_configured():
                    logger.info(f"[HybridAI.generate] Falling back to Gemini...")
                    return self.gemini_api.generate(prompt, temperature)
                elif provider == AIProvider.GEMINI_API and self.openai.is_configured():
                    logger.info(f"[HybridAI.generate] Falling back to OpenAI...")
                    return self.openai.generate(prompt, model=model, temperature=temperature)
            
            raise

    def test_connection(self, provider: AIProvider) -> dict:
        """Test connection for specific provider"""
        if provider == AIProvider.OPENAI:
            return self.openai.test_connection()
        elif provider == AIProvider.GEMINI_API:
            return self.gemini_api.test_connection()
        else:
            return {"success": False, "message": f"Unknown provider: {provider}"}

    def get_available_providers(self) -> list:
        """Get list of available providers with their status"""
        providers = []

        # OpenAI API
        providers.append({
            "id": "openai",
            "name": "OpenAI (GPT-4o)",
            "available": self.openai.is_configured(),
            "type": "api"
        })

        # Gemini API
        providers.append({
            "id": "gemini_api",
            "name": "Gemini API",
            "available": self.gemini_api.is_configured(),
            "type": "api"
        })

        # Auto (if any provider available)
        any_available = any(p["available"] for p in providers)
        providers.append({
            "id": "auto",
            "name": "Auto (Smart Selection)",
            "available": any_available,
            "type": "hybrid"
        })

        return providers
    
    def generate_with_images(
        self,
        prompt: str,
        image_urls: list[str],
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """
        Generate response using Vision API — sends text + images.

        Delegates to OpenAI's generate_with_images which supports both
        regular image URLs and base64 data URIs (data:image/jpeg;base64,...).

        Args:
            prompt: Text prompt describing what to analyze
            image_urls: List of image URLs or base64 data URIs
            temperature: Lower = more deterministic
            max_tokens: Max response tokens

        Returns:
            AI response text
        """
        if self.openai.is_configured():
            return self.openai.generate_with_images(
                prompt, image_urls, temperature=temperature, max_tokens=max_tokens
            )
        else:
            # Fallback: text-only generation with description of images
            logger.warning("[HybridAI.generate_with_images] No vision-capable provider, falling back to text-only")
            fallback_prompt = f"{prompt}\n\n(Note: {len(image_urls)} images were provided but vision API is unavailable. Analyze based on any text descriptions available.)"
            return self.generate(prompt=fallback_prompt, temperature=temperature)

    def get_available_models(self) -> list:
        """Get list of available models from API"""
        models = []
        
        # OpenAI models - fetch from API
        if self.openai.is_configured():
            openai_models = self.openai.list_models()
            models.extend(openai_models)
        
        # Gemini models
        if self.gemini_api.is_configured():
            models.append({
                "id": "gemini-2.0-flash-exp",
                "name": "Gemini 2.0 Flash",
                "description": "Fast and capable",
                "provider": "gemini_api"
            })
        
        return models

    # ═══════════════════════════════════════════════════════════════════════════
    # UNIFIED CONVERSATION API
    # Routes to whichever provider is configured (OpenAI or Gemini)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def has_conversation_support(self) -> bool:
        """Check if any provider with conversation support is configured."""
        return self.openai.is_configured() or self.gemini_api.is_configured()
    
    def start_conversation(self, system_prompt: str = None) -> str:
        """
        Start a conversation using the best available provider.
        
        Automatically routes to OpenAI or Gemini based on what's configured.
        For Gemini, system_prompt is sent as the first message since Gemini
        doesn't support system prompts natively.
        
        Args:
            system_prompt: Optional system context for the conversation
            
        Returns:
            conversation_id: Unique identifier for this conversation
        """
        if self.openai.is_configured():
            conversation_id = self.openai.start_conversation(system_prompt)
            self._conversation_providers[conversation_id] = "openai"
            provider_name = f"OpenAI (model: {self.openai.model})"
        elif self.gemini_api.is_configured():
            conversation_id = self.gemini_api.start_conversation()
            self._conversation_providers[conversation_id] = "gemini_api"
            # Send system_prompt as first message for Gemini
            if system_prompt:
                try:
                    self.gemini_api.send_message(conversation_id, system_prompt, temperature=0.3)
                except Exception as e:
                    logger.warning(f"[HybridAI] Failed to send system prompt to Gemini: {e}")
            provider_name = "Gemini API"
        else:
            raise AllProvidersFailedError(["openai", "gemini_api"])
        
        logger.info(f"[HybridAI] Started conversation {conversation_id[:8]}... via {provider_name}")
        return conversation_id
    
    def send_message(self, conversation_id: str, message: str, temperature: float = 0.7) -> str:
        """
        Send a message in an existing conversation, routing to the correct provider.
        
        Args:
            conversation_id: ID from start_conversation()
            message: The message to send
            temperature: Response temperature
            
        Returns:
            AI response text
        """
        provider = self._conversation_providers.get(conversation_id)
        if provider == "openai":
            return self.openai.send_message(conversation_id, message, temperature)
        elif provider == "gemini_api":
            return self.gemini_api.send_message(conversation_id, message, temperature)
        else:
            raise Exception(f"Conversation {conversation_id} not found in any provider")
    
    def end_conversation(self, conversation_id: str) -> None:
        """
        End a conversation and cleanup resources.
        
        Args:
            conversation_id: ID from start_conversation()
        """
        provider = self._conversation_providers.pop(conversation_id, None)
        if provider == "openai":
            self.openai.end_conversation(conversation_id)
        elif provider == "gemini_api":
            self.gemini_api.end_conversation(conversation_id)
        else:
            # Try both as fallback
            self.openai.end_conversation(conversation_id)
            self.gemini_api.end_conversation(conversation_id)

    def smart_task(
        self,
        prompt: str,
        task_type=None,  # TaskType enum from script_generator
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """
        Execute a task using the best available provider.
        
        This is a convenience wrapper around generate() that:
        - Uses AUTO provider selection
        - Enables smart fallback
        - Logs task execution
        
        Args:
            prompt: The prompt to send
            task_type: Optional task type for logging (from script_generator.TaskType)
            temperature: Response temperature
            model: Specific model to use
            
        Returns:
            AI response text
        """
        task_name = task_type.value if task_type else "unknown"
        logger.info(f"Executing smart_task: {task_name}")
        
        try:
            return self.generate(
                prompt=prompt,
                provider=AIProvider.AUTO,
                use_smart_model=True,
                temperature=temperature,
                model=model
            )
        except Exception as e:
            logger.error(f"smart_task failed for {task_name}: {e}")
            raise

