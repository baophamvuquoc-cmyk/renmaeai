import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


class NLPProcessor:
    """NLP and script processing module"""
    
    def __init__(self):
        # Configure Gemini API — try DB settings first, fallback to env var
        api_key = None
        try:
            from modules.ai_settings_db import get_settings_db
            db = get_settings_db()
            all_settings = db.get_all_settings()
            api_key = all_settings.get('gemini_api', {}).get('api_key')
        except Exception:
            pass
        
        if not api_key:
            api_key = os.getenv("GEMINI_API_KEY")
        
        if api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel('gemini-pro')
            except Exception as e:
                self.model = None
                print(f"Warning: Failed to initialize Gemini: {e}")
        else:
            self.model = None
            print("Warning: GEMINI_API_KEY not found in settings or environment")
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords from Vietnamese text using YAKE"""
        try:
            import yake
            
            kw_extractor = yake.KeywordExtractor(
                lan="vi",
                n=3,  # max ngram size
                dedupLim=0.9,
                top=max_keywords
            )
            
            keywords = kw_extractor.extract_keywords(text)
            return [kw[0] for kw in keywords]
        
        except ImportError:
            print("YAKE not installed, using simple extraction")
            # Fallback: simple word frequency
            words = text.lower().split()
            from collections import Counter
            common = Counter(words).most_common(max_keywords)
            return [word for word, _ in common]
    
    def tokenize_vietnamese(self, text: str) -> List[str]:
        """Tokenize Vietnamese text using underthesea"""
        try:
            from underthesea import word_tokenize
            return word_tokenize(text)
        except ImportError:
            print("underthesea not installed, using simple split")
            return text.split()
    
    def generate_scenes_from_script(
        self,
        script: str,
        language: str = "vi"
    ) -> List[Dict]:
        """Use LLM to convert script into structured scenes"""
        
        if not self.model:
            # Fallback: simple scene splitting
            return self._fallback_scene_generation(script)
        
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
{script}

JSON output:
"""
        
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()
            
            # Extract JSON from response
            import json
            import re
            
            # Try to find JSON array in response
            json_match = re.search(r'\[.*\]', text, re.DOTALL)
            if json_match:
                scenes = json.loads(json_match.group())
                return scenes
            else:
                print("Could not extract JSON from response")
                return self._fallback_scene_generation(script)
        
        except Exception as e:
            print(f"Error generating scenes with AI: {e}")
            return self._fallback_scene_generation(script)
    
    def _fallback_scene_generation(self, script: str) -> List[Dict]:
        """Simple fallback scene generation without AI"""
        # Split by paragraphs or sentences
        paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
        
        if not paragraphs:
            paragraphs = [script]
        
        scenes = []
        for idx, paragraph in enumerate(paragraphs, 1):
            # Extract simple keywords
            keywords = self.extract_keywords(paragraph, max_keywords=3)
            visual_query = ", ".join(keywords[:2]) if keywords else "generic scene"
            
            scenes.append({
                "scene_id": idx,
                "duration": 5,
                "voiceover": paragraph,
                "visual_query": visual_query,
                "ai_prompt": f"A cinematic shot related to {visual_query}",
                "mood": "professional"
            })
        
        return scenes
