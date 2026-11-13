# Hướng dẫn cài đặt Phím tắt **ClipSave** trên iPhone

Do Apple yêu cầu mọi file `.shortcut` từ iOS 15 trở lên phải được ký số trước khi mở trực tiếp trên iPhone, bạn có **3 cách cài đặt** tùy theo thiết bị đang có:

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

## Cách 2: Bạn chỉ dùng iPhone (Ký file `.unsigned.shortcut` ngay trên điện thoại)

> [!WARNING]
> **Không bấm mở trực tiếp file `.unsigned.shortcut` trong app Tệp/Safari** — iPhone sẽ báo lỗi *"Không thể cài do nguồn không hợp lệ / chưa được ký"*. Bạn cần ký nó qua phím tắt trung gian dưới đây:

1. Tải file về app **Tệp (Files)** trên iPhone (chọn lưu về Tệp, không mở ngay):
   - Bản có Menu chọn chất lượng: `https://github.com/Lingardinhom/clipsave/raw/main/shortcut/dist/ClipSave.unsigned.shortcut`
   - Bản 1-chạm (giống Snap Video): `https://github.com/Lingardinhom/clipsave/raw/main/shortcut/dist/ClipSave-1Tap.unsigned.shortcut`
2. Cài phím tắt ký file miễn phí trên RoutineHub: **Sign Shortcut File** (`https://routinehub.co/shortcut/26044/`).
3. Chạy **Sign Shortcut File** → chọn file `.unsigned.shortcut` trong Tệp → chờ vài giây để ký → bấm **Thêm phím tắt (Add Shortcut)**.
4. Nhập **Server URL** và **API Key** khi được hỏi lúc thêm phím tắt.

---

## Cách 3: Tự bấm tạo 7 bước ngay trên iPhone (Chắc chắn 100%, chỉ mất 90 giây)

Nếu tự tạo trực tiếp trong app **Phím tắt (Shortcuts)** trên iPhone, Apple tin cậy 100% và không bao giờ gặp lỗi nguồn không hợp lệ.

Mở app **Phím tắt** → bấm **+** → bấm **(i)** ở dưới cùng → bật **Hiển thị trong Bảng chia sẻ (Show in Share Sheet)** → chọn **URL**, **Trang web Safari**, **Văn bản**.
Sau đó chạm vào thẻ **Nhận đầu vào (Receive ... input)** trên cùng → ở mục *"Nếu không có đầu vào (If there's no input)"* chọn **Lấy bảng nhớ tạm (Get Clipboard)**.

Thêm đúng **7 hành động** sau:

1. **Lấy URL từ đầu vào** *(Get URLs from Input)* → chọn đầu vào là **Đầu vào phím tắt** *(Shortcut Input)*.
2. **Lấy nội dung của URL** *(Get Contents of URL)*:
   - **URL**: `https://<server-của-bạn>/api/v1/resolve` *(chỉnh lại thành URL server của bạn)*
   - Bấm mũi tên mở rộng **▶**:
     - **Phương thức (Method)**: `POST`
     - **Tiêu đề (Headers)**: Thêm khóa `X-API-Key` = `<API_KEY của bạn>`
     - **Phần thân yêu cầu (Request Body)**: `JSON` → thêm 4 trường:
       - `url` (Văn bản/Text): chọn biến **URL** (từ bước 1)
       - `mode` (Văn bản/Text): `auto`
       - `quality` (Văn bản/Text): `best`
       - `ios_compatible` (Boolean): `Đúng (True)`
3. **Lấy giá trị từ từ điển** *(Get Dictionary Value)*:
   - **Khóa (Key)**: `items`
   - **Từ điển (Dictionary)**: **Nội dung của URL** *(Contents of URL)* (từ bước 2).
4. **Lặp lại với mỗi mục** *(Repeat with Each)* trong **Giá trị từ điển** (từ bước 3).
5. *(Bên trong vòng lặp)* **Lấy giá trị từ từ điển** *(Get Dictionary Value)*:
   - **Khóa (Key)**: `download_url`
   - **Từ điển (Dictionary)**: **Mục lặp lại** *(Repeat Item)*.
6. *(Bên trong vòng lặp)* **Lấy nội dung của URL** *(Get Contents of URL)* → URL là **Giá trị từ từ điển** (từ bước 5), phương thức `GET`.
7. *(Bên trong vòng lặp)* **Lưu vào Album Ảnh** *(Save to Photo Album)* → lưu **Nội dung của URL** (từ bước 6) vào `Gần đây (Recents)` (hoặc album `ClipSave`).
8. **Kết thúc Lặp lại** *(End Repeat)* → thêm **Hiển thị thông báo** *(Show Notification)*: `"Đã lưu video không watermark!"`.

---

## Kích hoạt từ nút Chia sẻ (Share Sheet) & Cấp quyền

1. Mở chỉnh sửa phím tắt **ClipSave** → bấm biểu tượng **(i)** ở dưới cùng → bật **Hiển thị trong Bảng chia sẻ (Show in Share Sheet)** → chọn **URL**, **Trang web Safari**, **Văn bản**.
2. Vào **Cài đặt iPhone → Phím tắt → Nâng cao** → bật **Cho phép chia sẻ lượng lớn dữ liệu** (để tải video dung lượng lớn không bị cảnh báo).
3. Lần đầu chạy trên một app (TikTok, Douyin, Instagram...), iOS sẽ hỏi **"Cho phép ClipSave kết nối tới..."** và **"Lưu vào Ảnh"** → chọn **Luôn cho phép (Always Allow)**.
