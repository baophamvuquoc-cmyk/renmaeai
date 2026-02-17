# ANTIGRAVITY MASTER SPECIFICATION (V3.0)
**Project:** Automated Script & Video Pipeline
**Architecture:** Hybrid (Gemini API + GPM Automation)
**Deployment Target:** Windows Desktop App (Silent Mode - No Console)
**Version:** 3.0 (Production Ready)

---

## PART 1: SYSTEM ARCHITECTURE (KIẾN TRÚC HỆ THỐNG)

Hệ thống hoạt động theo mô hình **"Hybrid AI Router"**. Kết hợp giữa API tốc độ cao (Gemini Free) và Automation trình duyệt (GPM Login) để tối ưu chi phí và chất lượng.

### 1.1. Routing Strategy (Chiến lược định tuyến)
*   **Fast Lane (Gemini API Free):** Xử lý các task cấu trúc dữ liệu, JSON, cắt cảnh, trích xuất từ khóa (Latency < 2s).
*   **Deep Lane (GPM Automation):** Xử lý các task cần tư duy sâu: "Học giọng văn" (Style Cloning) và "Viết kịch bản đệ quy" (Recursive Writing).

### 1.2. The Core Backend (Python Code)
*File: `backend/modules/ai_automation.py`*

```python
from enum import Enum
from typing import Optional
import random
import time

class AIProvider(Enum):
    CHATGPT = "chatgpt"      # GPM Automation (Deep Lane)
    GEMINI = "gemini"        # GPM Automation (Deep Lane)
    AUTO = "auto"            # Load Balancing

class AIAutomationClient:
    def __init__(self, gpm_api_token: str):
        self.gpm_token = gpm_api_token
        self.profiles = {
            AIProvider.CHATGPT: "GPM_PROFILE_ID_CHATGPT_PLUS", 
            AIProvider.GEMINI: "GPM_PROFILE_ID_GEMINI_ULTRA",
        }
        
    def send_prompt(self, prompt: str, provider: AIProvider = AIProvider.AUTO, max_retries: int = 2) -> str:
        """Gửi prompt với cơ chế Auto-Fallback & Load Balancing"""
        if provider == AIProvider.AUTO:
            provider = random.choice([AIProvider.CHATGPT, AIProvider.GEMINI])
        
        for attempt in range(max_retries):
            try:
                # [TODO] Dev implement Playwright connection to GPM here
                return self._execute_gpm_playwright(prompt, provider)
            except Exception as e:
                print(f"[Warn] {provider.value} failed: {e}")
                # Failover: Nếu ChatGPT lỗi -> chuyển sang Gemini (và ngược lại)
                if attempt < max_retries - 1:
                    provider = self._get_fallback_provider(provider)
                    print(f"Switching to fallback: {provider.value}")
                    time.sleep(3)
        
        raise Exception("CRITICAL: All AI providers failed.")

    def _get_fallback_provider(self, current: AIProvider) -> AIProvider:
        return AIProvider.GEMINI if current == AIProvider.CHATGPT else AIProvider.CHATGPT