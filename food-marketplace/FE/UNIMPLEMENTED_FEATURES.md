# Danh sách chức năng chưa được implement

> Cập nhật: 2026-05-19  
> Phạm vi scan: `food-marketplace/FE/app/**`

---

## 🔴 CUSTOMER — Người dùng (Shell)

### 1. MyPage — Menu items dẫn đến `href: "#"` (dead links)

File: `app/(shell)/mypage/page.tsx` dòng 9–14

| Menu Item | Route dự kiến | Trạng thái |
|---|---|---|
| Мои отзывы (Đánh giá của tôi) | `/mypage/reviews` | ❌ Trang chưa tồn tại |
| Способы оплаты (Phương thức thanh toán) | `/mypage/payment` | ❌ Trang chưa tồn tại |
| Политика конфиденциальности (Chính sách bảo mật) | `/mypage/privacy` | ❌ Trang chưa tồn tại |
| Условия использования (Điều khoản sử dụng) | `/mypage/terms` | ❌ Trang chưa tồn tại |
| Связаться с нами (Liên hệ) | `/mypage/contact` | ❌ Trang chưa tồn tại |

---

### 2. Account Page — Nút đổi avatar không hoạt động

File: `app/(shell)/mypage/account/page.tsx` dòng 104

```tsx
<button className="absolute bottom-0 right-0 ..." aria-label="Сменить фото">
  <Camera className="h-3.5 w-3.5 text-white" />
</button>
```

- Nút Camera icon **không có `onClick` handler**
- Bấm vào không làm gì cả
- Chức năng upload/thay đổi avatar chưa được implement

---

### 3. Map Page — Nút "Маршрут" (Chỉ đường) không hoạt động

File: `app/(shell)/map/page.tsx` dòng 279

```tsx
<button className="w-9 h-9 ..." aria-label="Маршрут">
  <Navigation className="h-4 w-4 text-ink-60" />
</button>
```

- Nút Navigation icon trên mỗi locker **không có `onClick`**
- Không mở Google Maps hay chỉ đường đến locker
- Cần implement: mở `https://www.google.com/maps/dir/?api=1&destination={lat},{lng}`

---

### 4. Route `/items/[id]` — Dùng MOCK DATA, không kết nối API thật

File: `app/(shell)/items/[id]/page.tsx` dòng 11

```tsx
import { getItemById, getShopById, getLockerById } from '@/lib/mock'
```

- **Toàn bộ trang dùng dữ liệu giả** từ `lib/mock.ts`
- Không gọi API thật để lấy thông tin item/shop/locker
- Bộ đếm số lượng (qty stepper +/−) chỉ là local state, không ảnh hưởng đến checkout
- Nút Favorite (`setFav`) chỉ toggle local state, **không gọi API** addFavoriteShop

---

### 5. Route `/lockers/[id]` — Tab "Магазины" link đến route không tồn tại

File: `app/(shell)/lockers/[id]/page.tsx` dòng 121

```tsx
<Link href={`/shops/${shop.id}`}>
```

- Tab "Магазины" link đến `/shops/${shop.id}`
- **Route `/shops/[id]` không tồn tại** trong app — 404

---

### 6. Route `/combos/[id]` — Link tên shop dẫn đến route không tồn tại

File: `app/(shell)/combos/[id]/page.tsx` dòng 193

```tsx
<Link href={combo.shop_id ? `/shops/${combo.shop_id}` : '#'}>
  {combo.shop_name}
</Link>
```

- Bấm vào tên shop trên trang chi tiết combo sẽ bị 404
- **Route `/shops/[id]` không tồn tại**

---

## 🟠 SELLER — Người bán

### 7. Dashboard — Nút "⋯" (More menu) trên mỗi combo không hoạt động

File: `app/seller/page.tsx` dòng 529–534

```tsx
<button
  className="grid place-items-center ..."
  onMouseEnter={...}
  onMouseLeave={...}
>
  <MoreHorizontal size={18} />
</button>
```

- **Không có `onClick` handler**
- Không có dropdown/menu xuất hiện khi bấm
- Không thể edit hay xóa combo trực tiếp từ dashboard

---

### 8. Revenue Page — Nút "Скачать отчёт" không hoạt động

File: `app/seller/revenue/page.tsx` dòng 121–131

```tsx
<button ...>
  <Download size={13} strokeWidth={1.8} />
  Скачать отчёт
</button>
```

- **Không có `onClick` handler** — bấm không làm gì
- Chức năng export/download báo cáo chưa implement

---

### 9. Revenue Page — Bộ chọn kỳ không filter dữ liệu thật

File: `app/seller/revenue/page.tsx` dòng 58–60

```tsx
const [period, setPeriod] = useState<string>('month')
// ...
getSalesSummary().catch(() => null)  // Không truyền period
```

- UI cho phép chọn 7 ngày / Tháng / Quý / Năm
- **`getSalesSummary()` không nhận tham số period** — luôn trả về cùng một dữ liệu
- Badge `+18%` trên card "Выручка за период" là **giá trị hardcode giả**

---

### 10. Sales History Page — Nút "Экспорт" không hoạt động

File: `app/seller/sales-history/page.tsx` dòng 115–127

```tsx
<button ... onMouseEnter={...} onMouseLeave={...}>
  <Download size={13} strokeWidth={1.8} />
  Экспорт
</button>
```

- **Không có `onClick` handler** — bấm không làm gì
- Chức năng export lịch sử bán hàng chưa implement

---

## 🟡 ADMIN

### 11. Admin Panel — Chỉ có quản lý user, thiếu nhiều chức năng

File: `app/admin/page.tsx`

Admin panel chỉ có **1 trang duy nhất**: tạo và xem danh sách user (owner_shop / owner_locker).

Các chức năng admin điển hình **chưa có trang**:

| Chức năng | Trạng thái |
|---|---|
| Quản lý đơn hàng toàn hệ thống | ❌ Chưa có |
| Quản lý combo/sản phẩm | ❌ Chưa có |
| Quản lý locker locations & units | ❌ Chưa có |
| Báo cáo doanh thu tổng hợp | ❌ Chưa có |
| Quản lý khách hàng | ❌ Chưa có |

---

## 📋 Bảng tổng hợp theo mức độ ưu tiên

| Mức độ | # | Chức năng | File |
|---|---|---|---|
| 🔴 Cao | 1 | 5 trang trong MyPage menu (href="#") | `app/(shell)/mypage/page.tsx` |
| 🔴 Cao | 2 | Route `/shops/[id]` thiếu — 404 từ combos & lockers | `app/(shell)/combos/[id]/page.tsx`, `app/(shell)/lockers/[id]/page.tsx` |
| 🔴 Cao | 3 | Trang `/items/[id]` dùng mock data, không kết nối API | `app/(shell)/items/[id]/page.tsx` |
| 🟠 Trung | 4 | Avatar upload không hoạt động | `app/(shell)/mypage/account/page.tsx` |
| 🟠 Trung | 5 | Nút chỉ đường trên Map không hoạt động | `app/(shell)/map/page.tsx` |
| 🟠 Trung | 6 | More menu trên combo card (seller dashboard) | `app/seller/page.tsx` |
| 🟡 Thấp | 7 | Nút Download báo cáo (Revenue) | `app/seller/revenue/page.tsx` |
| 🟡 Thấp | 8 | Period filter Revenue không filter thật | `app/seller/revenue/page.tsx` |
| 🟡 Thấp | 9 | Nút Export (Sales History) | `app/seller/sales-history/page.tsx` |
| 🟡 Thấp | 10 | Admin panel thiếu các module quản trị | `app/admin/page.tsx` |
