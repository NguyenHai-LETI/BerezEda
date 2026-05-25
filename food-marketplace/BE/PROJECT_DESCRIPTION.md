# Food Marketplace — Mô tả dự án

---

## I. Tổng quan dự án

### 1.1. Mục đích dự án

Trong ngành thực phẩm, một lượng lớn sản phẩm bị lãng phí mỗi ngày do không được tiêu thụ trước hạn sử dụng — đặc biệt tại các cửa hàng nhỏ, tiệm bánh, nhà hàng nơi việc dự báo nhu cầu khách hàng rất khó chính xác. Đồng thời, nhiều người tiêu dùng có nhu cầu mua thực phẩm chất lượng với giá ưu đãi nhưng thiếu kênh tiếp cận. Dự án Food Marketplace giải quyết bài toán này bằng cách xây dựng một nền tảng kết nối cửa hàng thực phẩm với khách hàng thông qua hệ thống locker (tủ khóa thông minh). Các cửa hàng đóng gói sản phẩm sắp hết hạn thành combo giảm giá, đặt vào locker tại các vị trí thuận tiện; khách hàng đặt hàng và thanh toán online, sau đó đến locker nhận hàng bằng mã QR. Mô hình này giúp giảm lãng phí thực phẩm, tạo nguồn doanh thu bổ sung cho cửa hàng, đồng thời mang lại lợi ích kinh tế cho người tiêu dùng — tất cả thông qua một quy trình tự động, không cần nhân viên phục vụ trực tiếp.

### 1.2. Các đối tượng trong hệ thống

| Đối tượng | Mô tả |
|-----------|-------|
| **Owner** | Người sở hữu hệ thống (chủ đầu tư nền tảng). Có thể đồng thời sở hữu locker vật lý hoặc ký kết hợp đồng thuê locker với bên thứ 3. |
| **Shop (owner_shop)** | Chủ cửa hàng thực phẩm, đăng bán combo giảm giá trên nền tảng. |
| **Owner Locker (owner_locker)** | Người sở hữu và quản lý các điểm locker vật lý. |
| **Customer** | Khách hàng, người mua combo và nhận hàng tại locker. |
| **Admin** | Quản trị viên hệ thống, quản lý tài khoản và vận hành nền tảng. |

### 1.3. Sơ đồ tương tác giữa các đối tượng

```
┌─────────────────────────────────────────────────────────────────────┐
│                          OWNER (Chủ hệ thống)                      │
│          Sở hữu nền tảng + có thể sở hữu locker vật lý            │
│              hoặc thuê locker từ bên thứ 3                          │
└────────────┬──────────────────────────────────┬─────────────────────┘
             │ Ký hợp đồng                      │ Ký hợp đồng
             │ với Shop                          │ với Locker Owner
             ▼                                   ▼
┌────────────────────────┐           ┌────────────────────────────┐
│   SHOP OWNER           │           │   LOCKER OWNER             │
│   (Chủ cửa hàng)      │           │   (Chủ locker)             │
│                        │           │                            │
│ - Tạo sản phẩm        │           │ - Quản lý locker location  │
│ - Tạo combo giảm giá  │◄─────────►│ - Gán shop vào locker      │
│ - Đặt combo vào unit  │  Thỏa     │ - Quản lý locker unit      │
│ - Xem doanh thu       │  thuận    │ - Giám sát trạng thái      │
└────────────┬───────────┘  3 bên    └────────────────────────────┘
             │
             │ Đăng bán combo
             ▼
┌────────────────────────────────────────────────────────────────────┐
│                        LOCKER (Tủ khóa thông minh)                 │
│                                                                    │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│  │ Unit 1  │ │ Unit 2  │ │ Unit 3  │ │ Unit 4  │ │ Unit 5  │    │
│  │ Combo A │ │ Combo B │ │ (trống) │ │ Combo C │ │ (trống) │    │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
└────────────────────────────┬───────────────────────────────────────┘
                             │ Đặt hàng + Thanh toán
                             │ Nhận hàng bằng QR
                             ▼
┌────────────────────────────────────────────────────────────────────┐
│                         CUSTOMER (Khách hàng)                      │
│                                                                    │
│  1. Duyệt combo trên app  →  2. Đặt hàng & thanh toán (Fincode)  │
│  3. Nhận mã QR             →  4. Đến locker quét QR lấy hàng     │
│  5. Đánh giá combo                                                 │
└────────────────────────────────────────────────────────────────────┘

                             ┌──────────────────────┐
                             │   ADMIN              │
                             │                      │
                             │ - Tạo tài khoản      │
                             │   shop/locker owner   │
                             │   sau khi ký HĐ      │
                             │ - Gửi thông tin       │
                             │   qua email           │
                             │ - Quản lý toàn bộ    │
                             │   hệ thống           │
                             └──────────────────────┘
```

**Mô tả luồng hoạt động:**

1. **Owner** sở hữu nền tảng. Owner có thể trực tiếp sở hữu locker vật lý hoặc ký hợp đồng thuê locker với bên thứ 3 (locker owner).
2. **Shop owner** ký hợp đồng với Owner để tham gia nền tảng. Có 2 hình thức:
   - Ký trực tiếp với Owner → Owner gán shop vào các locker theo thỏa thuận 3 bên (Owner — Shop Owner — Locker Owner).
   - Ký hợp đồng với Locker Owner → được phép bán tại các locker location mà Locker Owner đó sở hữu.
3. **Admin** tạo tài khoản cho shop owner và locker owner sau khi hoàn tất đăng ký hợp đồng. Thông tin tài khoản được gửi qua email đăng ký.
4. **Locker Owner** gán shop vào locker location, quản lý các unit.
5. **Shop Owner** tạo sản phẩm, đóng gói thành combo giảm giá, chọn locker unit để bán.
6. **Customer** duyệt combo, đặt hàng, thanh toán qua Fincode, nhận mã QR, đến locker lấy hàng.

---

## II. Mô tả chức năng theo Role

### 1. Customer (Khách hàng)

#### Duyệt & Tìm kiếm
- Xem danh sách combo đang bán trên trang chủ
- Xem chi tiết combo (sản phẩm bên trong, giá gốc, giá giảm)
- Xem thông tin cửa hàng
- Xem danh sách locker trên bản đồ, tìm locker gần nhất

#### Đặt hàng & Thanh toán
- Đặt hàng combo
- Đăng ký thẻ thanh toán với cổng thanh toán Fincode (cổng thanh toán của Nhật, có môi trường test — sử dụng thẻ với số `4111 1111 1111 1111` để đăng ký). Hệ thống chuyển hướng tới trang đăng ký thẻ của Fincode, không lưu dữ liệu thẻ của người dùng.
- Thanh toán online
- Xem lịch sử đơn hàng và chi tiết từng đơn

#### Nhận hàng
- Nhận mã truy cập và mã QR mở locker sau khi thanh toán
- Mở locker để lấy hàng

#### Tương tác
- Thêm/xóa cửa hàng yêu thích
- Thêm/xóa locker yêu thích
- Viết đánh giá (review) cho combo đã mua
- Push notification *(chưa implement)*:
  - Khi cửa hàng đã yêu thích (favorited shop) publish bán combo mới
  - Khi thanh toán thành công mà chưa nhận hàng → push notification trước 10 phút trước khi hết hạn nhận hàng

#### Tài khoản
- Đăng ký tài khoản
- Đăng nhập / Đăng xuất
- Xem và chỉnh sửa thông tin cá nhân

---

### 2. Shop (Chủ cửa hàng — owner_shop)

#### Quản lý cửa hàng
- Xem và chỉnh sửa thông tin cửa hàng (tên, mô tả, địa chỉ)
- Upload ảnh cửa hàng

#### Quản lý sản phẩm
- Tạo sản phẩm mới (ProductMaster)
- Chỉnh sửa thông tin sản phẩm
- Upload ảnh sản phẩm

#### Quản lý combo
- Tạo combo (gộp nhiều sản phẩm, đặt giá giảm, chọn locker unit)
- Xem danh sách combo đã tạo
- Chỉnh sửa combo

#### Phân phối
- Chọn locker unit để đặt combo bán

#### Thống kê & Báo cáo
- Xem lịch sử bán hàng
- Xem doanh thu theo tháng
- Xem danh sách combo với các trạng thái khác nhau
- Phân tích dữ liệu người dùng *(chưa có phương án cụ thể, chưa apply)*

#### Tương tác
- Xem đánh giá từ khách hàng
- Nhận thông báo khi có đơn hàng được mua

---

### 3. Owner Locker (Chủ locker — owner_locker)

#### Quản lý locker location
- Tạo locker location mới (tên, địa chỉ, tọa độ)
- Chỉnh sửa thông tin locker location
- Upload ảnh locker location

#### Quản lý locker unit
- Thêm unit vào locker location
- Chỉnh sửa thông tin unit (kích thước, trạng thái)
- Xóa unit

#### Liên kết với cửa hàng
- Gán cửa hàng vào locker location (cho phép shop bán tại locker)
- Xem danh sách combo đang được đặt trong các unit

#### Đồng bộ & Giám sát
- Đồng bộ dữ liệu locker lên Firebase (real-time)
- Xem dashboard tổng quan
- Xem thống kê combo matching (combo nào được đặt vào unit nào)

---

### 4. Admin (Quản trị viên)

#### Quản lý người dùng
- Xem danh sách tất cả người dùng
- Lọc người dùng theo role
- Tạo tài khoản cho shop owner và locker owner (sau khi tạo, hệ thống gửi mail thông báo về cho shop owner / locker owner)
- Thay đổi role của người dùng

#### Quyền truy cập toàn hệ thống
- Truy cập tất cả dữ liệu: shops, products, combos, orders, lockers
- Thực hiện mọi thao tác mà shop owner và locker owner có thể làm
- Xem dashboard quản lý bán hàng toàn hệ thống

#### Dashboard thống kê & phân tích *(chưa apply)*

#### Vận hành hệ thống
- Đồng bộ toàn bộ locker lên Firebase
- Giám sát hoạt động tổng thể của marketplace

---

### 5. Các chức năng vận hành trong môi trường thực tế

#### Xử lý đồng thời (Concurrency Control)
- Sử dụng **Redis Lock** (distributed lock) để tránh trường hợp 2 customer cùng thanh toán và mua 1 combo. Lock được áp dụng theo combo ID với cơ chế atomic (SET NX + EX) và tự động hết hạn.

#### Ghi log hệ thống (Audit & System Logging)
- Ghi log tập trung cho các sự kiện: xác thực, lỗi hệ thống, thao tác thanh toán, thay đổi trạng thái đơn hàng.
- Phục vụ việc điều tra khi có claim (khiếu nại) từ khách hàng trong quá trình vận hành.

#### Xử lý nền (Background Jobs)
- Celery + Redis cho các tác vụ chạy nền và lập lịch:
  - Tự động dọn token đã thu hồi (mỗi 30 phút)
  - Tự động xử lý combo hết hạn
  - Tự động xử lý đơn hàng quá hạn nhận (pickup deadline)

#### Thanh toán & Webhook
- Tích hợp cổng thanh toán Fincode với cơ chế retry (tối đa 3 lần) khi gọi API.
- Webhook callback với xác thực chữ ký (signature verification) để đảm bảo tính toàn vẹn dữ liệu từ Fincode.
- Hỗ trợ xác thực 3D Secure.

#### Rate Limiting
- Giới hạn tần suất request dựa trên Redis (sliding window) để chống lạm dụng API.

#### Lưu trữ file
- Lưu trữ ảnh trên local storage (EBS volume khi deploy trên AWS EC2).
- Validate MIME type (JPEG, PNG, WebP, GIF) và giới hạn dung lượng file.

#### Gửi email
- Tích hợp AWS SES để gửi email (thông báo tạo tài khoản cho shop/locker owner).
- Template email dạng HTML.

#### Health Check
- Endpoint `/health` để kiểm tra trạng thái hoạt động của hệ thống, phục vụ monitoring và load balancer.

---

### Bảng tóm tắt chức năng

| Chức năng | Customer | Shop | Owner Locker | Admin |
|-----------|:--------:|:----:|:------------:|:-----:|
| Duyệt combo / shop / locker | ✅ | ✅ | ✅ | ✅ |
| Đặt hàng & thanh toán | ✅ | | | |
| Nhận hàng tại locker | ✅ | | | |
| Viết đánh giá | ✅ | | | |
| Yêu thích (shop & locker) | ✅ | | | |
| Quản lý sản phẩm | | ✅ | | ✅ |
| Tạo & quản lý combo | | ✅ | | ✅ |
| Xem doanh thu & thống kê bán hàng | | ✅ | | ✅ |
| Tạo & quản lý locker | | | ✅ | ✅ |
| Quản lý locker unit | | | ✅ | ✅ |
| Gán shop vào locker | | | ✅ | ✅ |
| Quản lý người dùng | | | | ✅ |
| Tạo tài khoản shop/locker owner | | | | ✅ |
| Truy cập toàn bộ dữ liệu | | | | ✅ |

---

## III. Sơ đồ cấu trúc database

```
┌──────────────┐       ┌──────────────────┐       ┌──────────────────┐
│    User      │       │      Shop        │       │ LockerLocation   │
│──────────────│       │──────────────────│       │──────────────────│
│ id (PK)      │──┐    │ id (PK)          │       │ id (PK)          │
│ email        │  │    │ owner_id (FK)────│───┐   │ owner_id (FK)────│───┐
│ username     │  │    │ name             │   │   │ name             │   │
│ role         │  │    │ code             │   │   │ code             │   │
│ phone        │  │    │ logo             │   │   │ address          │   │
│ is_active    │  │    │ avg_rating       │   │   │ position (geo)   │   │
│ shop_id (FK) │  │    │ is_active        │   │   │ is_active        │   │
└──────┬───────┘  │    └────────┬─────────┘   │   └────────┬─────────┘   │
       │          │             │             │            │             │
       │          └─────────────┼─────────────┼────────────┼─────────────┘
       │                        │             │            │
       │    ┌───────────────────┘             │            │
       │    │                                 │            │
       │    │  ┌──────────────────────────────┘            │
       │    │  │                                           │
       │    ▼  ▼                                           │
       │ ┌──────────────────────┐                          │
       │ │ ShopLockerAssociation│                          │
       │ │──────────────────────│                          │
       │ │ shop_id (PK, FK)     │                          │
       │ │ locker_location_id   │──────────────────────────┘
       │ │   (PK, FK)           │
       │ └──────────────────────┘
       │
       │    ┌──────────────────┐       ┌──────────────────┐
       │    │  ProductMaster   │       │   LockerUnit     │
       │    │──────────────────│       │──────────────────│
       │    │ id (PK)          │       │ id (PK)          │
       │    │ shop_id (FK)─────│──┐    │ location_id (FK) │
       │    │ name             │  │    │ unit_number      │
       │    │ selling_price    │  │    │ status           │
       │    │ images           │  │    │ size             │
       │    │ is_active        │  │    │ temperature      │
       │    └────────┬─────────┘  │    └────────┬─────────┘
       │             │            │             │
       │             ▼            │             │
       │    ┌──────────────────┐  │             │
       │    │  ComboProduct    │  │             │
       │    │──────────────────│  │             │
       │    │ id (PK)          │  │             │
       │    │ combo_id (FK)────│──┼──┐          │
       │    │ product_master_id│  │  │          │
       │    │   (FK)           │  │  │          │
       │    │ quantity         │  │  │          │
       │    └──────────────────┘  │  │          │
       │                          │  │          │
       │    ┌──────────────────┐  │  │          │
       │    │     Combo        │◄─┘  │          │
       │    │──────────────────│◄────┘          │
       │    │ id (PK)          │                │
       │    │ shop_id (FK)     │                │
       │    │ name             │                │
       │    │ original_price   │                │
       │    │ discount_%       │                │
       │    │ status           │                │
       │    │ pickup_deadline  │                │
       │    └────────┬─────────┘                │
       │             │                          │
       │             ▼                          │
       │    ┌──────────────────┐                │
       │    │     Order        │                │
       │    │──────────────────│                │
       │    │ id (PK)          │                │
       │    │ user_id (FK)─────│────────────────┼───── User
       │    │ combo_id (FK)    │                │
       │    │ shop_id (FK)     │                │
       │    │ locker_unit_id   │────────────────┘
       │    │   (FK)           │
       │    │ order_number     │
       │    │ status           │
       │    │ final_price      │
       │    │ pickup_code      │
       │    └────────┬─────────┘
       │             │
       │             ▼
       │    ┌──────────────────┐       ┌──────────────────┐
       │    │    Payment       │       │    Review         │
       │    │──────────────────│       │──────────────────│
       │    │ id (PK)          │       │ id (PK)          │
       │    │ order_id         │       │ user_id (FK)     │
       │    │ customer_id      │       │ shop_id (FK)     │
       │    │ amount           │       │ combo_id (FK)    │
       │    │ status           │       │ order_id (FK)    │
       │    └──────────────────┘       │ rating           │
       │                               │ comment          │
       │                               └──────────────────┘
       │
       │    ┌──────────────────┐       ┌──────────────────┐
       │    │ LockerReservation│       │    Favorite       │
       │    │──────────────────│       │──────────────────│
       │    │ id (PK)          │       │ id (PK)          │
       │    │ locker_unit_id   │       │ user_id (FK)─────│───── User
       │    │   (FK)           │       │ shop_id (FK)     │
       │    │ user_id (FK)     │       └──────────────────┘
       │    │ shop_id (FK)     │
       │    │ combo_id (FK)    │       ┌──────────────────┐
       │    │ access_code      │       │  FavoriteLocker  │
       │    │ qr_code_url      │       │──────────────────│
       │    │ status           │       │ id (PK)          │
       │    └──────────────────┘       │ user_id (FK)─────│───── User
       │                               │ locker_location_id│
       │    ┌──────────────────┐       │   (FK)           │
       │    │   Notification   │       └──────────────────┘
       │    │──────────────────│
       │    │ id (PK)          │       ┌──────────────────┐
       │    │ title            │       │NotificationUser  │
       │    │ body             │       │──────────────────│
       │    │ type             │       │ id (PK)          │
       │    │ created_by_id(FK)│       │ notification_id  │
       │    └──────────────────┘       │   (FK)           │
       │                               │ user_id (FK)     │
       │    ┌──────────────────┐       │ is_read          │
       │    │     Device       │       └──────────────────┘
       │    │──────────────────│
       │    │ id (PK)          │       ┌──────────────────┐
       │    │ user_id (FK)─────│──┐    │    QRCode        │
       │    │ device_token     │  │    │──────────────────│
       │    │ platform         │  │    │ id (PK)          │
       │    └──────────────────┘  │    │ user_id (FK)     │
       │                          │    │ qr_data          │
       └──────────────────────────┘    │ is_used          │
                                       └──────────────────┘
```

**Quan hệ chính:**

| Quan hệ | Loại |
|----------|------|
| User → Shop | One-to-One (owner) |
| User → LockerLocation | One-to-Many (owner) |
| Shop ↔ LockerLocation | Many-to-Many (qua ShopLockerAssociation) |
| Shop → ProductMaster | One-to-Many |
| Shop → Combo | One-to-Many |
| Combo ↔ ProductMaster | Many-to-Many (qua ComboProduct) |
| LockerLocation → LockerUnit | One-to-Many |
| User → Order | One-to-Many |
| Combo → Order | One-to-Many |
| Order → Review | One-to-One |
| User → Favorite | One-to-Many |
| User → FavoriteLocker | One-to-Many |
| Notification → NotificationUser | One-to-Many |
