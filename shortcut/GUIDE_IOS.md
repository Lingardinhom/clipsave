# Hướng dẫn cài đặt Phím tắt **ClipSave** trên iPhone

Do Apple yêu cầu mọi file `.shortcut` từ iOS 15 trở lên phải được ký số trước khi mở trực tiếp trên iPhone, bạn có **2 cách cài đặt** rất nhanh dưới đây:

---

## Cách 1: Bạn có máy Mac (Nhanh nhất — 30 giây)

1. Mở Terminal trên Mac tại thư mục `shortcut/` và chạy:
   ```bash
   chmod +x sign_on_mac.sh
   ./sign_on_mac.sh
   ```
   *(Hoặc chạy trực tiếp: `shortcuts sign --mode anyone -i dist/ClipSave.unsigned.shortcut -o dist/ClipSave.shortcut`)*
   - `ClipSave.shortcut`: Có menu chọn **Video HD / 720p / Tách âm thanh M4A**.
   - `ClipSave-1Tap.shortcut`: Bấm 1 chạm tải thẳng chất lượng cao nhất (giống Snap Video).
2. Gửi file `.shortcut` đã ký qua **AirDrop** sang iPhone (hoặc mở trên Mac rồi bấm **Share → Copy iCloud Link**).
3. Khi iPhone hỏi cấu hình ban đầu (*Import Questions*):
   - Dán **Server URL** (ví dụ `https://clipsave-xxx.onrender.com`, không có `/` ở cuối).
   - Dán **API Key** trùng với biến `API_KEY` bạn đặt trên server.

---

## Cách 2: Bạn KHÔNG có máy Mac (Tự lắp ráp 12 bước trên iPhone trong 3 phút)

Vì toàn bộ logic tải & ghép video nằm trên Backend API, phím tắt trên iPhone cực kỳ gọn. Bạn mở app **Phím tắt (Shortcuts)** → bấm **+** → thêm đúng thứ tự các hành động dưới đây:

1. **Văn bản (Text)**: Nhập URL server của bạn (ví dụ `https://clipsave.yourdomain.com`) → **Đặt biến (Set Variable)** tên `ServerURL`.
2. **Văn bản (Text)**: Nhập `API_KEY` của bạn → **Đặt biến (Set Variable)** tên `APIKey`.
3. **Nếu (If)** `Đầu vào phím tắt (Shortcut Input)` *có bất kỳ giá trị nào*:
   - **Văn bản (Text)**: chèn `Shortcut Input`
   - **Không thì (Otherwise)**: **Lấy bảng nhớ tạm (Get Clipboard)**
   - **Kết thúc Nếu (End If)**
4. **Lấy URL từ đầu vào (Get URLs from Input)** từ `Kết quả Nếu (If Result)`.
5. **Lấy mục từ danh sách (Get Item from List)**: `Mục đầu tiên (First Item)` → **Đặt biến** tên `TargetURL`.
6. **Lấy nội dung của URL (Get Contents of URL)**:
   - **URL**: `[ServerURL]/api/v1/resolve`
   - **Phương thức (Method)**: `POST`
   - **Tiêu đề (Headers)**: `X-API-Key` = `[APIKey]`
   - **Phần thân yêu cầu (Request Body)**: `JSON`
     - `url` (Text): `[TargetURL]`
     - `mode` (Text): `auto` *(hoặc `audio` nếu muốn tải nhạc)*
     - `quality` (Text): `best`
     - `ios_compatible` (Boolean): `True`
7. **Lấy giá trị từ từ điển (Get Dictionary Value)**: Khóa `items` từ `Nội dung của URL (Contents of URL)`.
8. **Lặp lại với mỗi mục (Repeat with Each)** trong `Giá trị từ điển`:
   - **Lấy giá trị từ từ điển**: Khóa `download_url` từ `Mục lặp lại (Repeat Item)`.
   - **Lấy nội dung của URL**: URL = `Giá trị từ điển` *(Phương thức GET)*.
   - **Lưu vào Album Ảnh (Save to Photo Album)**: Lưu `Nội dung của URL` vào album `Gần đây (Recents)` hoặc tạo album `ClipSave`.
9. **Kết thúc Lặp lại (End Repeat)**.
10. **Hiển thị thông báo (Show Notification)**: `"ClipSave: Đã lưu xong không watermark!"`.

---

## Kích hoạt từ nút Chia sẻ (Share Sheet) & Cấp quyền

1. Mở chỉnh sửa phím tắt **ClipSave** → bấm biểu tượng **(i)** ở dưới cùng → bật **Hiển thị trong Bảng chia sẻ (Show in Share Sheet)** → chọn **URL**, **Trang web Safari**, **Văn bản**.
2. Vào **Cài đặt iPhone → Phím tắt → Nâng cao** → bật **Cho phép chia sẻ lượng lớn dữ liệu** (để tải video dung lượng lớn không bị cảnh báo).
3. Lần đầu chạy trên một app (TikTok, Douyin, Instagram...), iOS sẽ hỏi **"Cho phép ClipSave kết nối tới..."** và **"Lưu vào Ảnh"** → chọn **Luôn cho phép (Always Allow)**.
