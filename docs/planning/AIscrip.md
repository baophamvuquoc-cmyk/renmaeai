# IMPLEMENTATION PLAN: ANTIGRAVITY AI WORKFLOW (HYBRID EDITION)
**Project:** Automated Script & Video Pipeline
**Core Strategy:** Style Cloning + Recursive Writing + **GPM Browser Automation**
**Infrastructure:** Hybrid (Gemini Free API + GPM Automation Layer)
**Version:** 2.0 (Cost-Optimized & High Availability)

---

## 1. SYSTEM ARCHITECTURE (KIẾN TRÚC HỆ THỐNG)

Hệ thống hoạt động theo mô hình **"Hybrid AI Router"**. Thay vì phụ thuộc hoàn toàn vào API trả phí, hệ thống sẽ tự động định tuyến (route) yêu cầu tới nơi hiệu quả nhất.

### 1.1. High-Level Diagram
```mermaid
graph TD
    App[Antigravity Backend] --> HybridRouter[Hybrid AI Client]
    
    subgraph "Priority 1: Speed & Structure"
        HybridRouter -->|Task logic/JSON/Ngắn| GeminiAPI[Gemini Flash API (Free Tier)]
    end
    
    subgraph "Priority 2: Deep Writing & Nuance"
        HybridRouter -->|Task Sáng tạo/Dài| Automation[GPM Automation Layer]
        Automation -->|Load Balance| Profile1[GPM: ChatGPT Plus]
        Automation -->|Load Balance| Profile2[GPM: Gemini Ultra]
    end