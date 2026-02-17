# HƯỚNG DẪN CHUYỂN ĐỔI KỊCH BẢN VĂN HỌC SANG KỊCH BẢN VIDEO AI (GOOGLE VEO 3 SCENE BUILDER)

[cite_start]Tài liệu này hướng dẫn quy trình xây dựng hệ thống trung gian "Scene Builder" để chuyển đổi ngôn ngữ văn học trừu tượng thành chỉ lệnh kỹ thuật chính xác cho mô hình Google Veo 3 và Veo 3.1[cite: 7, 8].

---

## 1. TƯ DUY CỐT LÕI: "NGUYÊN TỬ HÓA" KỊCH BẢN
AI hoạt động tốt nhất khi xử lý các đơn vị thông tin nhỏ gọn. [cite_start]Đừng cố gắng tạo một cảnh phim phức tạp trong một lần tạo (one-shot generation)[cite: 42].

### Quy tắc phân rã (Decomposition Rules):
* [cite_start]**Đơn vị thời gian (Micro-beats):** Chia kịch bản thành các nhịp nhỏ có thời lượng từ **4 đến 8 giây**[cite: 45]. [cite_start]Đây là khoảng thời gian lý tưởng để AI duy trì sự ổn định vật lý[cite: 46].
* [cite_start]**Đơn vị hành động:** Mỗi prompt chỉ chứa **một hành động chủ đạo** hoặc **một chuyển động camera** duy nhất[cite: 47].
    * *Sai:* "Nhân vật bước vào, nhặt thư và khóc."
    * [cite_start]*Đúng:* Tách thành 3 shot: (1) Toàn cảnh bước vào -> (2) Cận cảnh tay nhặt thư -> (3) Đặc tả mặt khóc[cite: 48, 49, 50].

---

## 2. QUY TRÌNH TRÍCH XUẤT DỮ LIỆU (6 TRỤ CỘT)
[cite_start]Mọi dòng kịch bản phải được "bóc tách" thành 6 yếu tố kỹ thuật sau để nạp vào Scene Builder[cite: 53, 54]:

| Yếu Tố (Element) | Câu Hỏi Định Hướng | Ví Dụ Kỹ Thuật (Keyword) |
| :--- | :--- | :--- |
| **1. Chủ Thể (Subject)** | Ai là trung tâm? Đặc điểm nhận dạng? | [cite_start]*Old man, 70s, gray beard, worn brown jacket.* [cite: 56] |
| **2. Hành Động (Action)** | Làm gì cụ thể? (Tránh động từ trừu tượng) | [cite_start]*Walking slowly, limping, looking down.* [cite: 56] |
| **3. Bối Cảnh (Environment)** | Ở đâu? Thời gian? Khí hậu? | [cite_start]*Abandoned warehouse, dusty, god rays, sunset.* [cite: 56] |
| **4. Camera** | Góc máy và chuyển động? | [cite_start]*Low angle, slow push-in (dolly), shallow depth of field.* [cite: 57] |
| **5. Ánh Sáng (Lighting)** | Nguồn sáng và tính chất? | [cite_start]*Volumetric lighting, rim light, high contrast.* [cite: 57] |
| **6. Âm Thanh (Audio)** | Âm thanh đi kèm? | [cite_start]*Echoing footsteps, distant wind, melancholic cello.* [cite: 57] |

### Chiến lược chuyển đổi cảm xúc (Emotion Mapping)
AI không hiểu "nỗi buồn", nó cần tín hiệu thị giác. [cite_start]Hãy dịch cảm xúc sang thông số kỹ thuật[cite: 59, 60]:

* [cite_start]**Tích cực (Lãng mạn/Vui):** Ánh sáng vàng mềm mại (Golden Hour), tông màu ấm, bố cục đối xứng[cite: 73, 92, 84].
* [cite_start]**Tiêu cực (Buồn/Cô đơn):** Ánh sáng xanh (Blue hour), tông lạnh, quay từ xa (Distance), zoom chậm[cite: 88, 102, 98, 124].
* [cite_start]**Kịch tính (Bí ẩn/Căng thẳng):** Tương phản cao (High contrast), bóng đổ sâu (Film Noir), ánh sáng gắt từ bên (Side lighting)[cite: 106, 109, 120].

---

## 3. CẤU TRÚC HÓA JSON (SCENE BUILDER SCHEMA)
[cite_start]Sử dụng cấu trúc JSON thay vì văn bản tự do để ngăn chặn hiện tượng "rò rỉ thuộc tính" (ví dụ: áo đỏ của người A bị nhầm sang người B) và dễ dàng tự động hóa[cite: 135, 138].

### Mẫu JSON tiêu chuẩn cho Veo 3:
```json
{
  "scene_id": "Mã_Cảnh (VD: SC_01_A)",
  "meta": {
    "duration": "5s",
    "aspect_ratio": "16:9 (Youtube) hoặc 9:16 (Tiktok)", 
    "resolution": "4k (Upscaled)"
  },
  "content": {
    "subject": {
      "description": "Mô tả ngoại hình chi tiết",
      "reference_image_id": "Tên file ảnh tham chiếu (Ingredients)", 
      "action": "Hành động cụ thể"
    },
    "environment": {
      "location": "Địa điểm",
      "lighting": "Thiết lập ánh sáng (VD: Neon, Soft)",
      "weather": "Thời tiết"
    }
  },
  "camera": {
    "shot_size": "Cỡ cảnh (Wide/Medium/Close-up)",
    "movement": "Chuyển động (Pan/Tilt/Dolly)",
    "lens": "Loại ống kính (35mm/85mm)"
  },
  "audio": {
    "dialogue": "Lời thoại (ngắn)",
    "sfx": "Tiếng động hiện trường (Diegetic)",
    "bgm_mood": "Nhạc nền (Non-diegetic)"
  },
  "control": {
    "negative_prompt": "blurry, text, watermark, distortion"
  }
}