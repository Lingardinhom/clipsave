# ClipSave — Phím tắt iPhone & Backend API Tải Video Đa Nền Tảng Không Watermark

**ClipSave** là hệ thống phím tắt iOS (tham khảo trải nghiệm **Snap Video**) kết hợp **Backend API tự chủ (self-hosted)** giúp tải video, album ảnh (carousel) và âm thanh từ hầu hết nền tảng mạng xã hội về iPhone mà **không dính watermark**, không quảng cáo, và luôn tương thích 100% với ứng dụng **Ảnh (Photos)** trên iPhone.

---

## Tính năng nổi bật

- **Đa nền tảng (Global + Châu Á)**: TikTok (không watermark + Photo Mode), Douyin, Xiaohongshu (Tiểu Hồng Thư), Instagram (Reels/Post/Carousel), Facebook, Threads, YouTube / Shorts, X (Twitter), Pinterest, Bilibili, Reddit, SoundCloud...
- **Chuẩn hóa Video cho iPhone Photos**: Tự động ghép audio+video và chuyển đổi stream VP9/AV1/WebM sang **MP4 (H.264 + AAC + faststart)** qua `ffmpeg` để lệnh *Save to Photo Album* trên iOS không bao giờ báo lỗi.
- **Xử lý link chia sẻ thông minh**: Tự lọc URL sạch từ đoạn text chia sẻ tiếng Trung/Anh/Việt và giải mã link rút gọn (`vt.tiktok.com`, `v.douyin.com`, `xhslink.com`, `fb.watch`, `pin.it`...).
- **2 Phiên bản Phím tắt iPhone**:
  - `ClipSave.unsigned.shortcut`: Có Menu chọn **Video chất lượng cao / Video 720p / Tách âm thanh M4A**.
  - `ClipSave-1Tap.unsigned.shortcut`: Chế độ 1-chạm lưu ngay (giống Snap Video).
- **Kèm Web UI dự phòng**: Truy cập `/` trên Safari hoặc trình duyệt máy tính để dán link và tải trực tiếp.
- **Bảo mật & Dọn dẹp tự động**: Hỗ trợ `X-API-Key`, chống SSRF, giới hạn tốc độ (rate-limit) và tự xóa file tạm sau 10 phút (`FILE_TTL_SECONDS`).

---

## Khởi chạy Backend nhanh

### 1. Chạy bằng Docker Compose (Khuyên dùng cho VPS / Local)
```bash
cd backend
cp .env.example .env
# Sửa API_KEY trong .env thành chuỗi bí mật của bạn
docker compose up -d --build
```

### 2. Chạy trực tiếp bằng Python (`uv`)
Yêu cầu: Python 3.11+ và `ffmpeg`.
```bash
cd backend
uv venv
uv pip install -e ".[dev]"
cp .env.example .env
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Deploy lên Cloud (Render / Railway / Fly.io)
- **Render**: Dùng file cấu hình sẵn tại [deploy/render.yaml](deploy/render.yaml).
- **Railway**: Dùng [deploy/railway.toml](deploy/railway.toml).
- **Fly.io**: Dùng [deploy/fly.toml](deploy/fly.toml).

---

## Cài đặt Phím tắt lên iPhone

Xem hướng dẫn chi tiết tại [shortcut/GUIDE_IOS.md](shortcut/GUIDE_IOS.md) (bao gồm cách ký file `.shortcut` trên Mac bằng `./shortcut/sign_on_mac.sh` hoặc tự lắp ráp 10 bước trên iPhone nếu không có máy Mac).

---

## Kiểm thử (Tests)

```bash
cd backend
uv run pytest -v
```
