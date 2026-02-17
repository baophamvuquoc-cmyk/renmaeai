# Auto Media Architecture

![Auto Media Architecture](https://via.placeholder.com/1200x400/667eea/ffffff?text=Auto+Media+Architecture)

**AI-Powered Video Production & File Management Desktop Tool**

Một ứng dụng desktop toàn diện cho tự động hóa quản lý file và sản xuất video AI, từ kịch bản đến video hoàn chỉnh.

## ✨ Tính Năng Chính

### 🗂️ Quản Lý File Thông Minh
- Đổi tên hàng loạt với regex pattern
- Preview an toàn trước khi thực thi
- Hỗ trợ đa nền tảng (Windows, macOS, Linux)
- Metadata extraction và file organization

### 📝 AI Screenwriter
- Chuyển đổi kịch bản thành cấu trúc JSON scenes
- Tích hợp Gemini Pro AI
- Hỗ trợ tiếng Việt với underthesea
- Keyword extraction tự động (YAKE)

### 🎬 Asset Management
- Tìm kiếm stock footage từ Pexels & Pixabay
- Download và cache thông minh
- Tích hợp YouTube downloader (yt-dlp)
- AI video generation (HunyuanVideo, CogVideoX)

### 🎥 Video Production
- Timeline editor với drag & drop
- MoviePy integration cho video editing
- FFmpeg cho rendering chất lượng cao
- Render queue với progress tracking

## 🚀 Cài Đặt

### Yêu Cầu Hệ Thống
- **Node.js** 18+ (cho frontend)
- **Python** 3.10+ (cho backend)
- **FFmpeg** (cho video processing)

### Frontend Setup

\`\`\`bash
# Cài đặt dependencies
npm install

# Chạy development mode
npm run dev

# Build production
npm run build
\`\`\`

### Backend Setup

\`\`\`bash
# Tạo virtual environment (khuyến nghị)
cd backend
python -m venv venv

# Kích hoạt virtual environment
# Windows:
venv\\Scripts\\activate
# macOS/Linux:
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt

# Chạy backend server
python main.py
# hoặc
uvicorn main:app --reload
\`\`\`

### Cấu Hình API Keys

1. Copy file `.env.example` thành `.env`
2. Điền các API keys của bạn:

\`\`\`env
GEMINI_API_KEY=your_key_here
PEXELS_API_KEY=your_key_here
PIXABAY_API_KEY=your_key_here
\`\`\`

#### Lấy API Keys Miễn Phí:
- **Gemini**: https://makersuite.google.com/app/apikey
- **Pexels**: https://www.pexels.com/api/
- **Pixabay**: https://pixabay.com/api/docs/

## 📖 Sử Dụng

### 1. Quản Lý File
1. Mở tab "Quản Lý File"
2. Chọn thư mục cần xử lý
3. Cấu hình pattern đổi tên (prefix, suffix, regex, index)
4. Xem preview kết quả
5. Xác nhận để thực thi

### 2. Tạo Video từ Kịch Bản
1. Mở tab "Kịch Bản"
2. Nhập nội dung kịch bản
3. Click "Tạo Scenes với AI"
4. AI sẽ phân tích và tạo JSON scenes
5. Download hoặc copy JSON để sử dụng

### 3. Tìm Kiếm Asset
1. Mở tab "Tài Nguyên"
2. Nhập từ khóa tìm kiếm
3. Chọn loại (Video/Image)
4. Browse kết quả từ Pexels & Pixabay
5. Download asset về cache

### 4. Render Video
1. Mở tab "Render"
2. Theo dõi tiến trình các job
3. Xem output khi hoàn thành

## 🏗️ Kiến Trúc

\`\`\`
auto-media-architecture/
├── electron/              # Electron main process
│   ├── main.js           # Window management
│   └── preload.js        # IPC bridge
├── src/                   # React frontend
│   ├── components/       # UI components
│   ├── stores/           # Zustand state management
│   ├── lib/              # API client
│   └── styles/           # CSS design system
└── backend/              # Python FastAPI backend
    ├── modules/          # Core logic
    │   ├── file_manager.py
    │   ├── nlp_processor.py
    │   └── asset_manager.py
    └── routes/           # API endpoints
\`\`\`

## 🛠️ Tech Stack

### Frontend
- **Framework**: Electron + React + TypeScript
- **Build Tool**: Vite
- **State Management**: Zustand
- **Data Fetching**: TanStack React Query
- **UI**: Custom design system with glassmorphism

### Backend
- **Framework**: FastAPI (Python)
- **File Management**: pathlib
- **NLP**: underthesea, YAKE, KeyBERT
- **AI**: Gemini Pro API
- **Video**: MoviePy, FFmpeg
- **Download**: yt-dlp, requests

## 📝 Scripts NPM

\`\`\`bash
npm run dev              # Chạy frontend + electron
npm run build            # Build production
npm run electron:build   # Tạo installer
npm run backend:dev      # Chạy backend server
npm run backend:install  # Cài Python dependencies
\`\`\`

## 🤝 Đóng Góp

Mọi đóng góp đều được chào đón! Hãy tạo issue hoặc pull request.

## 📄 License

MIT License - Xem file LICENSE để biết thêm chi tiết

## 🙏 Credits

- Design inspired by modern AI tools
- Built with love for the Vietnamese content creator community
- Special thanks to all open-source contributors

---

**Made with ❤️ for Vietnamese Creators**
