# CAPPYAUTOPOS - TỰ ĐỘNG HÓA ĐĂNG BÀI FACEBOOK THẾ HỆ MỚI
*(An toàn 100% • Zero Backdoor • Anti-Ban • PyWebView Modern Dark UI • CSDL SQLite)*

---

## 1. Giới thiệu
**CappyAutoPost v2.0** là hệ thống tự động hóa đăng bài viết, hình ảnh lên các Nhóm Facebook (Facebook Groups) đa tài khoản, đa luồng, được thiết kế lại hoàn toàn dựa trên các nghiên cứu kỹ thuật từ phiên bản tiền nhiệm (`ToolAutoPost`), loại bỏ triệt để mã độc đánh cắp tài khoản, đồng thời nâng cấp toàn diện về giao diện, tính năng và khả năng chống checkpoint (anti-ban).

---

## 2. Tính năng nổi bật

1. **An toàn & Minh bạch 100% (Zero Backdoor):**
   - Không chứa bất kỳ dòng mã độc hay kết nối gửi cookie về máy chủ gián điệp.
   - Toàn bộ dữ liệu Cookie, bài viết, nhật ký lưu trữ cục bộ trong file cơ sở dữ liệu `cappy_autopost.db` (SQLite WAL mode).
2. **Giao diện Người dùng Hiện đại (Modern Dark UI):**
   - Xây dựng bằng kiến trúc **PyWebView + HTML/CSS/Tailwind UI-UX Pro Max** tối ưu theo chuẩn thiết kế quốc tế.
   - 6 Tab chức năng: **Dashboard**, **Tài khoản (Cookie)**, **Danh sách Nhóm**, **Kho Bài Viết & Spintax**, **Chạy Chiến Dịch**, **Lịch sử Đăng**.
   - Hỗ trợ xem console log thời gian thực với màu sắc phân biệt trực quan.
3. **Bộ kiểm tra Cookie Siêu tốc (Fast Headless HTTP Validator):**
   - Kiểm tra Live / Die / Checkpoint chỉ mất **0.5 giây / tài khoản** qua giao thức HTTP mbasic (không cần bật trình duyệt Chrome Selenium nặng nề).
   - Tự động lấy tên Facebook và UID tài khoản.
4. **Lõi tự động hóa Chống phát hiện Bot (Anti-Detection Automation):**
   - Sử dụng **`undetected-chromedriver`** vượt qua các cơ chế kiểm tra bot của Cloudflare / Facebook.
   - Mỗi phiên chạy tạo một profile tạm thời độc lập và tự động xóa sạch khi kết thúc để chống rò rỉ RAM / bộ nhớ đĩa.
5. **Mô phỏng hành vi Người thật (Natural Human Behavior):**
   - Thuật toán trễ gõ phím ngẫu nhiên (25ms - 85ms/ký tự) kèm khoảng dừng suy nghĩ tự nhiên.
   - Tiêm nội dung mượt mà vào trình soạn thảo Lexical React Editor của Facebook bằng `insertText` + `Shift+Enter` (không lỗi mất dấu tiếng Việt hay emoji).
   - Nghỉ an toàn theo đồ thị hình chuông (Gaussian curve) giữa các nhóm đăng.
6. **Bộ giải mã Spintax & Biến động đa tầng:**
   - Cú pháp lồng nhau: `{Chào bạn|Hello|{Hi anh/chị|Xin chào}}`.
   - Biến động: `{time}` (giờ phút), `{date}` (ngày), `{datetime}`, `{rand_id}` (#ABC12), `{rand_num}`.
7. **Hỗ trợ Đăng Ẩn danh & Proxy:**
   - Tự động bật chế độ "Đăng ẩn danh" (Anonymous Post) nếu nhóm Facebook hỗ trợ.
   - Gán Proxy riêng cho từng tài khoản (định dạng `host:port` hoặc `host:port:user:pass`).

---

## 3. Cấu trúc thư mục dự án

```text
CappyAutoPost/
├── cappy_app.py               # File chính khởi chạy ứng dụng Desktop
├── build_exe.py               # Script đóng gói thành file .exe độc lập
├── requirements.txt           # Danh sách thư viện Python
├── PLAN.md                    # Bản kế hoạch kiến trúc chi tiết
├── config/
│   └── settings.py            # Cấu hình đường dẫn và thông số trễ mặc định
├── database/
│   ├── connection.py          # Quản lý kết nối SQLite WAL & Transaction
│   └── models.py              # CRUD cho Accounts, Groups, Posts, History
├── core/
│   ├── browser.py             # Quản lý Undetected ChromeDriver + Stealth
│   ├── cookie_helper.py       # Bộ phân tích Cookie chuỗi/JSON & Proxy
│   ├── fb_actions.py          # Thao tác giao diện Facebook (Login, Post, Anon, Upload)
│   ├── human_behavior.py      # Mô phỏng gõ phím & delay Gaussian tự nhiên
│   └── spintax.py             # Bộ xử lý Spintax lồng nhau & biến động
├── services/
│   ├── account_service.py     # Fast HTTP Validator & nhập tài khoản
│   ├── group_service.py       # Quản lý & chuẩn hóa URL nhóm
│   └── campaign_worker.py     # Worker điều phối chiến dịch chạy ngầm đa luồng
├── ui/
│   ├── api.py                 # JS-Python Bridge API (PyWebView)
│   └── web/                   # Giao diện Webview hiện đại
│       ├── index.html         # Bố cục 6 Tabs & Modals
│       ├── css/style.css      # Hệ thống màu Dark Slate & Lucide icons
│       └── js/app.js          # Controller điều khiển sự kiện giao diện
└── tests/
    └── test_cappy.py          # Bộ kiểm thử Unit test tự động
```

---

## 4. Hướng dẫn cài đặt & Khởi chạy

### Cách 1: Khởi chạy trực tiếp từ mã nguồn

1. Kích hoạt môi trường ảo Python 3.12:
   ```powershell
   .venv\Scripts\activate
   ```
2. Khởi chạy ứng dụng:
   ```powershell
   python cappy_app.py
   ```
   *(Hoặc chạy trực tiếp: `.venv\Scripts\python.exe cappy_app.py`)*

---

### Cách 2: Đóng gói thành file chạy `.exe`

Chạy script đóng gói:
```powershell
.venv\Scripts\python.exe build_exe.py
```
Sau khi hoàn tất, file thực thi sẽ nằm tại:
`dist/CappyAutoPost/CappyAutoPost.exe`

---

## 5. Hướng dẫn sử dụng nhanh

### Bước 1: Nạp tài khoản (Tab Tài khoản)
- Nhấn **"Thêm Cookie / Proxy"**.
- Dán danh sách cookie Facebook (chuỗi `c_user=...; xs=...;` hoặc mảng JSON J2Team/EditThisCookie).
- Có thể kèm proxy theo định dạng: `cookie|host:port` hoặc `cookie|host:port:user:pass`.
- Nhấn **"Nhập tài khoản"**, hệ thống sẽ tự động check Live siêu tốc trong 0.5s.

### Bước 2: Nạp nhóm Facebook (Tab Danh sách Nhóm)
- Nhấn **"Nhập Nhóm Hàng Loạt"**.
- Điền danh mục (ví dụ: `Bất động sản`, `Tuyển dụng`).
- Dán danh sách liên kết nhóm (mỗi dòng một link hoặc ID nhóm).

### Bước 3: Soạn bài viết (Tab Kho Bài Viết)
- Nhấn **"Tạo Bài Viết Mới"**.
- Nhập tiêu đề và nội dung có gắn Spintax `{Chào bạn|Hello|Hi}` và biến `{time}`, `{date}`, `{rand_id}`.
- Nhấn **"Xem trước Spintax ngẫu nhiên"** để kiểm tra nội dung trước khi lưu.
- Chọn hình ảnh đính kèm từ máy tính (nếu có).
- Tích chọn "Ưu tiên đăng ẩn danh" nếu muốn.

### Bước 4: Chạy chiến dịch (Tab Chạy Chiến Dịch)
- Chọn bài viết cần đăng.
- Cấu hình số bài tối đa / tài khoản (mặc định 3 bài trước khi tự động đổi sang nick khác).
- Cấu hình khoảng trễ nghỉ an toàn (ví dụ: 120s - 240s).
- Nhấn **"BẮT ĐẦU CHIẾN DỊCH"** và theo dõi diễn biến từng giây trên khung Console Nhật Ký Trực Tiếp.
