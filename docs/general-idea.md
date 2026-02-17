# IMPLEMENTATION PLAN: HỆ THỐNG TỰ ĐỘNG HÓA FILE & SẢN XUẤT VIDEO AI (AUTO-MEDIA ARCHITECTURE)

## 1. Tổng Quan Dự Án
Xây dựng một hệ thống "Ingredients-to-Video" tích hợp, bao gồm khả năng quản trị dữ liệu thô (đổi tên, sắp xếp) và pipeline sản xuất video tự động từ kịch bản (Script-to-Video) sử dụng kết hợp Stock Footage, YouTube Data và Generative AI.

**Mục tiêu:** Tự động hóa quy trình từ quản lý tài nguyên đầu vào đến render video thành phẩm chất lượng cao.

---

## 2. Kiến Trúc Công Nghệ (Tech Stack)
* **Ngôn ngữ chính:** Python 3.10+
* **Quản lý tập tin:** `pathlib`, `PureWindowsPath/PurePosixPath`, `Re` (Regex).
* **NLP & Logic:** `underthesea` (xử lý tiếng Việt), `YAKE/KeyBERT` (Keyword extraction), LLM API (Gemini Pro/GPT-4).
* **Asset Acquisition:** `requests` (Pexels/Pixabay API), `yt-dlp` (YouTube), `scrapetube`.
* **Video Generation (AI):** HunyuanVideo (13B), CogVideoX-5B, hoặc Wan2.1.
* **Video Editing:** `MoviePy v2.0`, `FFmpeg` (CLI filter complex).
* **Hạ tầng:** `bitsandbytes` (Quantization), Cloud GPU (Thunder Compute/RunPod), Docker.

---

## 3. Lộ Trình Triển Khai Chi Tiết

### Giai Đoạn 1: Xây Dựng Core Quản Lý Tập Tin (File System Automation)
*Mục tiêu: Đảm bảo dữ liệu đầu vào được chuẩn hóa, tránh lỗi ghi đè và quản lý đường dẫn đa nền tảng.*

#### 1.1. Module Đối Tượng Đường Dẫn
- [ ] Implement `pathlib` thay thế hoàn toàn `os.path`.
- [ ] Xây dựng class xử lý đường dẫn tương thích chéo (Cross-platform) sử dụng `PureWindowsPath` và `PurePosixPath`.
- [ ] Viết hàm tiện ích trích xuất metadata: `.stem` (tên gốc), `.suffix` (đuôi file), `.stat().st_size` (kích thước).

#### 1.2. Module Đổi Tên Hàng Loạt (Batch Renamer)
- [ ] **Logic cốt lõi:**
    - [ ] Sử dụng `iterdir()` hoặc `glob()` để quét thư mục.
    - [ ] Áp dụng `enumerate()` để đánh số thứ tự (Index).
    - [ ] Tích hợp `Regex` để lọc/thay thế chuỗi (ví dụ: xóa ngày tháng cũ, chuẩn hóa snake_case).
- [ ] **Cơ chế an toàn (Safety Net):**
    - [ ] Tạo `Rename Map` (Danh sách thay đổi dự kiến) trước khi ghi đĩa.
    - [ ] Implement tính năng **Dry-Run/Preview** (Xem trước kết quả).
    - [ ] Xử lý ngoại lệ: `try-except` cho `PermissionError`, `FileExistsError`.

---

### Giai Đoạn 2: Bộ Não Xử Lý Nội Dung (NLP & Scripting Engine)
*Mục tiêu: Chuyển đổi ý tưởng thô thành cấu trúc dữ liệu JSON có thể lập trình.*

#### 2.1. Phân Tích & Làm Sạch Văn Bản
- [ ] Tích hợp `underthesea` để tokenization kịch bản tiếng Việt.
- [ ] Implement thuật toán trích xuất từ khóa:
    - [ ] **Option nhẹ:** YAKE (dựa trên thống kê).
    - [ ] **Option sâu:** KeyBERT (dựa trên Embeddings & Cosine Similarity) để tìm visual concepts.

#### 2.2. AI Screenwriter (LLM Integration)
- [ ] Kết nối API (Gemini/GPT-4) với prompt kỹ thuật (System Prompt).
- [ ] **Output định dạng JSON bắt buộc:**
    ```json
    [
      {
        "scene_id": 1,
        "duration": 5,
        "voiceover": "Lời bình cho phân cảnh...",
        "visual_query": "từ khóa tìm stock",
        "ai_prompt": "mô tả chi tiết cho model sinh video",
        "mood": "cinematic, slow motion"
      }
    ]
    ```

---

### Giai Đoạn 3: Hệ Thống Thu Thập Tài Nguyên (Hybrid Asset Engine)
*Mục tiêu: Tìm kiếm footage phù hợp nhất từ 3 nguồn: Stock miễn phí, YouTube, hoặc AI sinh mới.*

#### 3.1. Module Stock API (Pexels/Pixabay)
- [ ] Đăng ký API Key.
- [ ] Viết hàm `search_stock(query, orientation, size)` sử dụng `requests`.
- [ ] Parse JSON phản hồi -> Lấy URL video chất lượng cao nhất -> Tải xuống thư mục tạm.

#### 3.2. Module YouTube Scraper
- [ ] Tích hợp `yt-dlp` (Embedded Python version).
- [ ] Cấu hình `cookie.txt` và cơ chế xoay vòng User-Agent/Proxy để tránh chặn IP.
- [ ] Chức năng: Download phân đoạn (Range download) để tiết kiệm băng thông.
- [ ] Trích xuất Metadata (Subtitle/Description) để đối chiếu ngữ cảnh.

#### 3.3. Module Generative Video (AI Local/Cloud)
- [ ] **Lựa chọn Model:** HunyuanVideo (Chất lượng cao) hoặc CogVideoX (Nhẹ hơn).
- [ ] **Tối ưu hóa phần cứng:**
    - [ ] Implement `bitsandbytes` để chạy Quantization (8-bit/4-bit) giảm VRAM.
    - [ ] Kích hoạt `VAE Tiling` để tránh OOM (Out of Memory) khi render độ phân giải cao.
    - [ ] Offload CPU/GPU thông qua `accelerate`.

---

### Giai Đoạn 4: Trình Biên Tập Tự Động (Programmatic Editor)
*Mục tiêu: Lắp ráp các tài nguyên thành video hoàn chỉnh.*

#### 4.1. Audio Pipeline
- [ ] Tạo file âm thanh từ văn bản (TTS) hoặc load file voiceover có sẵn.
- [ ] Tự động tính toán thời lượng (`audio.duration`) để cắt footage hình ảnh khớp timeline.

#### 4.2. Video Composition (MoviePy v2.0)
- [ ] Load clips: `VideoFileClip` (Stock/AI) hoặc `ImageSequenceClip`.
- [ ] Xử lý cắt ghép: `.subclipped()`, `.with_duration()`.
- [ ] Resize/Crop: Đảm bảo đồng bộ tỷ lệ khung hình (ví dụ: 9:16 cho Shorts, 16:9 cho YouTube).
- [ ] Composite: Sử dụng `CompositeVideoClip` để chồng lớp (Video nền + Overlay Text + Logo).

#### 4.3. Rendering & Optimization (FFmpeg)
- [ ] Sử dụng MoviePy để xuất bản nháp (Preview).
- [ ] **Production Render:** Gọi trực tiếp `FFmpeg` qua `subprocess` cho các tác vụ nặng:
    - [ ] Stream copy (nối file không encode lại).
    - [ ] Filter complex (chỉnh màu, add noise).
    - [ ] Preset: `slow` hoặc `veryslow` cho chất lượng final.

---

### Giai Đoạn 5: Hạ Tầng & Vận Hành (Infrastructure & Ops)

#### 5.1. Quản Lý Tài Nguyên
- [ ] Cấu trúc thư mục dự án chuẩn:
    ```text
    /project_root
    ├── /raw_assets (Input từ người dùng)
    ├── /processed_assets (Sau khi đổi tên/chuẩn hóa)
    ├── /temp_downloads (Cache từ Stock/YouTube)
    ├── /output (Video thành phẩm)
    └── /scripts (Mã nguồn)
    ```

#### 5.2. Triển khai GPU (Cost Strategy)
- [ ] Dev môi trường: Colab Pro hoặc Local GPU (nếu có RTX 3090/4090).
- [ ] Production môi trường: Thuê GPU theo giờ trên Thunder Compute (A100/H100) để chạy model HunyuanVideo.
- [ ] So sánh chi phí: Nếu nhu cầu thấp -> Dùng API thương mại (Runway/Sora); Nhu cầu cao -> Self-host model.

---

## 4. Tài Nguyên Tham Khảo (GitHub Study List)
Để đẩy nhanh tiến độ, cần nghiên cứu mã nguồn của các repo sau:

1.  **Pipeline:** `gemini-youtube-automation` (ChaituRajSagar), `VideoGraphAI` (mikeoller82).
2.  **Editing:** `MoviePy` (Zulko) - Chú ý docs v2.0, `FFMPerative` (remyxai).
3.  **Data Mining:** `yt-dlp` (Core library), `scrapetube`.
4.  **AI Models:** `HunyuanVideo` (Tencent), `CogVideo` (THUDM).

## 5. Rủi Ro & Giải Pháp
| Rủi ro | Giải pháp |
| :--- | :--- |
| **API Limit** (Pexels/YouTube) | Cache dữ liệu đã tải, xoay vòng API Key, sử dụng Proxy. |
| **VRAM Model AI quá lớn** | Dùng bản Quantization (4-bit), giảm độ phân giải sinh, thuê Cloud GPU. |
| **Lỗi Encoding Video** | Luôn chuẩn hóa input về cùng FPS và Codec (H.264/AAC) trước khi ghép. |
| **Logic đổi tên sai** | Luôn bắt buộc bước Preview/Dry-run trước khi thực thi. |