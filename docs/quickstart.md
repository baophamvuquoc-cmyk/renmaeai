# 🚀 Quick Start Guide

## Cài Đặt Nhanh

### Bước 1: Cài Dependencies

```bash
# Frontend
npm install

# Backend
cd backend
pip install -r requirements.txt
cd ..
```

### Bước 2: Cấu Hình API Keys (Tùy chọn)

Copy `.env.example` thành `.env` và điền API keys:

```env
GEMINI_API_KEY=your_key_here
PEXELS_API_KEY=your_key_here
PIXABAY_API_KEY=your_key_here
```

**Lấy API keys miễn phí:**
- Gemini: https://makersuite.google.com/app/apikey
- Pexels: https://www.pexels.com/api/
- Pixabay: https://pixabay.com/api/docs/

> ⚠️ **Lưu ý:** Ứng dụng vẫn chạy được mà không cần API keys, nhưng các tính năng AI và stock search sẽ bị giới hạn.

### Bước 3: Chạy Ứng Dụng

**Mở 2 terminal:**

Terminal 1 - Backend:
```bash
cd backend
python main.py
```

Terminal 2 - Frontend:
```bash
npm run dev
```

✅ Ứng dụng sẽ tự động mở!

---

## 📖 Hướng Dẫn Sử Dụng

### File Management (Đổi Tên Hàng Loạt)

1. Click tab **"Quản Lý File"**
2. Chọn **"Chọn Thư Mục"**
3. Cấu hình pattern:
   - Prefix: `video_`
   - Số thứ tự: bắt đầu từ 1, padding 3 (001, 002, ...)
   - Regex (tùy chọn): `\d{4}-\d{2}-\d{2}` → thay bằng `""`
4. Click **"Xem Trước"**
5. Kiểm tra kết quả và click **"Xác Nhận Đổi Tên"**

### Script Editor (Tạo Scenes AI)

1. Click tab **"Kịch Bản"**
2. Nhập kịch bản tiếng Việt
3. Click **"Tạo Scenes với AI"**
4. AI sẽ phân tích và tạo JSON scenes
5. Download hoặc copy JSON

**Ví dụ kịch bản:**
```
Xin chào! Hôm nay chúng ta sẽ học về AI.

AI có thể giúp tự động hóa công việc.

Hãy cùng khám phá các tính năng tuyệt vời!
```

### Asset Browser (Tìm Stock Footage)

1. Click tab **"Tài Nguyên"**
2. Nhập từ khóa (tiếng Anh): `sunset city`
3. Chọn loại: Video hoặc Image
4. Click **"Tìm Kiếm"**
5. Hover vào video và click **"Tải Xuống"**

---

## 🛠️ Troubleshooting

### Backend không chạy được

```bash
# Kiểm tra Python version (cần 3.10+)
python --version

# Cài lại dependencies
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

### Frontend không build được

```bash
# Xóa node_modules và cài lại
rm -rf node_modules
npm install

# Clear cache
npm cache clean --force
```

### Lỗi CORS khi gọi API

Đảm bảo backend đang chạy ở `http://localhost:8000`

---

## 📦 Build Production

```bash
# Build frontend
npm run build

# Tạo installer Windows
npm run electron:build
```

File installer sẽ ở trong thư mục `dist/`

---

## 💡 Tips

- Giữ cả 2 terminal (backend + frontend) mở khi development
- Sử dụng **Ctrl+Shift+I** để mở DevTools trong Electron
- Backend API docs: http://localhost:8000/docs
- Tất cả file tải xuống sẽ ở `backend/temp_downloads/`

---

**Chúc bạn sử dụng vui vẻ! 🎉**

Xem thêm chi tiết trong [README.md](README.md)
