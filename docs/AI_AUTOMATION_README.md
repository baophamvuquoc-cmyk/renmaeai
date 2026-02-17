# AI Automation - User Guide

Tính năng AI Automation cho phép tự động hóa việc sử dụng ChatGPT Plus và Gemini Ultra thông qua GPM Browser.

---

## 🎯 Tổng Quan

Hệ thống sử dụng **Hybrid AI Router** kết hợp:
- **Gemini API (Free)** - Cho task nhanh, đơn giản
- **GPM Browser Automation** - Cho ChatGPT Plus và Gemini Ultra với session đã login

---

## 🚀 Cài Đặt

### Yêu cầu
1. **GPM Browser** - Tải từ [gpmlogin.com](https://gpmlogin.com)
2. **Python dependencies**:
   ```bash
   pip install playwright apscheduler
   python -m playwright install chromium
   ```

### Thiết lập GPM
1. Mở **GPM Browser** application
2. Tạo profile mới trong GPM (không cần through code)
3. Quay lại ứng dụng, vào **AI Settings → Account Manager**

---

## 🔧 Sử Dụng

### Thêm Tài Khoản AI

1. Vào **AI Settings** từ sidebar
2. Click **"Thêm Tài Khoản"** (ChatGPT hoặc Gemini)
3. Chọn GPM profile đã tạo
4. Browser sẽ mở lên → **Đăng nhập thủ công**
5. Sau khi login xong, hệ thống tự detect và lưu session

### Sử dụng AI Automation

1. Trong **Script Editor**, chọn "Generate with AI"
2. Chọn provider: Gemini API, ChatGPT, hoặc Auto
3. Nhập prompt → Submit
4. Hệ thống tự động:
   - Mở GPM browser (ẩn)
   - Gửi prompt
   - Lấy response
   - Đóng browser

---

## ❓ Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| "GPM not running" | Khởi động GPM Browser application |
| "Profile not found" | Tạo profile trong GPM trước |
| "Session expired" | Click "Test" để verify, re-login nếu cần |
| "Playwright not installed" | Chạy `pip install playwright` |

### Logs
- Console logs hiển thị với màu sắc
- File log: `backend/logs/ai_automation.log`

---

## ⚙️ Session Scheduler

Hệ thống tự động verify session định kỳ:
- Default: mỗi 6 giờ
- Có thể start/stop qua API:
  - `POST /api/ai/scheduler/start?interval_hours=6`
  - `POST /api/ai/scheduler/stop`
  - `GET /api/ai/scheduler/status`

---

## 📦 API Reference

### Accounts
- `GET /api/ai/accounts` - List accounts
- `POST /api/ai/accounts/setup` - Setup new account
- `POST /api/ai/accounts/{id}/verify` - Verify session
- `DELETE /api/ai/accounts/{id}` - Delete account

### AI Generation
- `POST /api/ai/generate` - Generate with AI
- `GET /api/ai/providers` - List available providers
