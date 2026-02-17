from enum import Enum
from typing import Optional
import random
import time

# Giả định import các thư viện cần thiết
# import requests (cho GPM API)
# from playwright.sync_api import sync_playwright

class AIProvider(Enum):
    CHATGPT = "chatgpt"      # Web Automation
    GEMINI = "gemini"        # Web Automation
    GEMINI_API = "gemini_api" # Official Free API
    AUTO = "auto"            # Tự động cân bằng tải

class AIAutomationClient:
    def __init__(self, gpm_api_token: str):
        self.gpm_token = gpm_api_token
        # Map Provider với ID Profile GPM tương ứng
        self.profiles = {
            AIProvider.CHATGPT: "GPM_PROFILE_ID_CHATGPT_PLUS", 
            AIProvider.GEMINI: "GPM_PROFILE_ID_GEMINI_ULTRA",
        }
        
    def send_prompt(self, prompt: str, provider: AIProvider = AIProvider.AUTO, max_retries: int = 2) -> str:
        """
        Gửi prompt tới AI provider với cơ chế auto-fallback & load balancing
        """
        # 1. Load Balancing: Random chọn provider để tránh pattern giống bot
        if provider == AIProvider.AUTO:
            provider = random.choice([AIProvider.CHATGPT, AIProvider.GEMINI])
        
        for attempt in range(max_retries):
            try:
                print(f"[*] Sending prompt via GPM Profile: {provider.value} (Attempt {attempt+1})...")
                return self._execute_gpm_playwright(prompt, provider)
            except Exception as e:
                print(f"[!] {provider.value} Failed: {e}")
                
                # 2. Failover: Nếu ChatGPT lỗi, tự động chuyển sang Gemini (và ngược lại)
                if attempt < max_retries - 1:
                    provider = self._get_fallback_provider(provider)
                    print(f"⚠️ Switching to fallback provider: {provider.value}")
                    time.sleep(3) # Nghỉ nhẹ để tránh spam
        
        raise Exception("CRITICAL: All AI Automation providers failed.")
    
    def _execute_gpm_playwright(self, prompt: str, provider: AIProvider) -> str:
        """Kết nối Playwright vào GPM Profile đang mở"""
        profile_id = self.profiles[provider]
        
        # [DEV TODO]: Implement Playwright Logic
        # 1. Call GPM Local API -> Start Profile -> Get Debug Port (e.g., 127.0.0.1:xxx)
        # 2. Connect Playwright to Debug Port.
        # 3. Locate Textarea -> Fill Prompt -> Click Send.
        # 4. Wait for Streaming to finish -> Scrape Response Text.
        return "Simulated AI Response for now"

    def _get_fallback_provider(self, current: AIProvider) -> AIProvider:
        return AIProvider.GEMINI if current == AIProvider.CHATGPT else AIProvider.CHATGPT

# CLASS CHÍNH ĐỂ GỌI TRONG APP
class HybridAIClient:
    def __init__(self):
        # self.gemini_api = GeminiOfficialClient() # Free Tier Client
        self.automation = AIAutomationClient(gpm_api_token="YOUR_GPM_TOKEN")
    
    def generate(self, prompt: str, use_smart_model: bool = True) -> str:
        # Chiến lược Hybrid
        if not use_smart_model:
            try:
                # Ưu tiên API Free cho task nhẹ
                # return self.gemini_api.generate(prompt)
                pass 
            except Exception:
                print("API Quota exceeded, switching to automation...")
        
        # Dùng Automation cho task nặng
        return self.automation.send_prompt(prompt)