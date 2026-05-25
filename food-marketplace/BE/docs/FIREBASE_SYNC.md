# Firebase Sync Flow

> **Lưu ý quan trọng**: Mỗi khi thay đổi logic sync Firebase (thêm/xóa/sửa bất kỳ lệnh `firebase_service.*`), phải cập nhật tài liệu này.

## Tổng quan kiến trúc

Hệ thống dùng Firestore làm **read layer cho client** (FE/mobile đọc realtime). PostgreSQL là **nguồn sự thật** (source of truth). Backend đồng bộ một chiều: PostgreSQL → Firestore.

```
PostgreSQL (source of truth)
        │
        │ firebase_service.*  (apps/integrations/firebase_client.py)
        ▼
    Firestore
        │
        ▼
  Frontend / Mobile (realtime reads)
```

## Cấu trúc Firestore

### Collection: `locker_locations`

Document ID = `locker_location.id` (UUID từ PostgreSQL)

```
locker_locations/{location_id}          ← thông tin location
locker_locations/{location_id}/units/{unit_id}   ← subcollection units
```

**Document fields:**
```json
{
  "id": "uuid",
  "name": "Москва Постамат",
  "address": "Красная пл. ...",
  "latitude": 55.75,
  "longitude": 37.62,
  "is_active": true
}
```

**Subcollection `units` document fields:**
```json
{
  "id": "uuid",
  "unit_number": 3,
  "status": "available | occupied | reserved",
  "size": "M",
  "temperature": 4,
  "is_active": true,
  "location_id": "uuid"
}
```

**Unit status values:**
| Status | Ý nghĩa |
|---|---|
| `available` | Trống, có thể assign combo |
| `reserved` | Đã assign combo, chờ seller đặt hàng vào |
| `occupied` | Hàng đã trong tủ, đang bán / chờ pickup |

### Collection: `combos`

Document ID = `combo.id` (UUID từ PostgreSQL)

```json
{
  "id": "uuid",
  "shop_id": "uuid",
  "locker_unit_id": "uuid",
  "locker_location_id": "uuid",
  "title": "vegetable",
  "sale_price": 84,
  "status": "available",
  "sale_end_time": "2026-03-22T10:03:49"
}
```

> Firestore `combos` chỉ chứa combo **đang bán** (`status = available`). Khi combo bị mua/hủy/hết hạn, document bị **xóa khỏi Firestore**.

---

## Luồng sync theo từng sự kiện

### 1. Seller assign locker cho combo

**Trigger:** `POST /combos/{id}/assign-locker`
**File:** [apps/combos/services.py](../apps/combos/services.py) — `assign_locker()`

```
DB: combo.status → "ready"
Firestore: units/{unit_id}.status → "reserved"
```

### 2. Seller đặt hàng vào tủ (confirm placed)

**Trigger:** `PUT /combos/{id}/confirm-placed`
**File:** [apps/combos/services.py](../apps/combos/services.py) — `confirm_placed()`

```
DB: combo.status → "available", unit.status → "occupied"
Firestore: units/{unit_id}.status → "occupied"
Firestore: combos/{combo_id} → CREATE/UPDATE (status: "available")
```

### 3. Khách hàng thanh toán

**Trigger:** Payment callback
**File:** [apps/orders/services.py](../apps/orders/services.py) — `mark_order_paid()`

```
DB: combo.status → "sold"
Firestore: combos/{combo_id} → DELETE  ← combo không còn hiển thị
(unit vẫn "occupied" — hàng còn trong tủ chờ pickup)
```

### 4. Khách hàng pickup

**Trigger:** `POST /orders/{id}/pickup` hoặc locker simulator
**File:** [apps/orders/services.py](../apps/orders/services.py) — `pickup_order()` / `pickup_by_code()`

```
DB: order.status → "completed", unit.status → "available"
Firestore: units/{unit_id}.status → "available"
Firestore: combos/{combo_id} → DELETE  (safety — đã xóa ở bước 3)
```

### 5. Seller hủy combo

**Trigger:** `PUT /combos/{id}/cancel`
**File:** [apps/combos/services.py](../apps/combos/services.py) — `cancel_combo()`

```
DB: combo.status → "cancelled", unit.status → "available"
Firestore: units/{unit_id}.status → "available"
Firestore: combos/{combo_id} → DELETE
```

### 6. Combo hết hạn (scheduler)

**Trigger:** APScheduler job — `expire_combo()`
**File:** [apps/scheduler/scheduler.py](../apps/scheduler/scheduler.py)

```
DB: combo.status → "EXPIRED"
DB: unit.status → "available"  (qua complete_reservation_and_release_locker hoặc fallback)
Firestore: units/{unit_id}.status → "available"
Firestore: combos/{combo_id} → DELETE
```

---

## Sơ đồ trạng thái unit

```
available ──[assign_locker]──► reserved
                                   │
                            [confirm_placed]
                                   │
                                   ▼
              ◄──[cancel]──── occupied
              ◄──[expired]───     │
              ◄──[pickup]────     │
```

## Sơ đồ trạng thái combo trong Firestore

```
(không tồn tại)
      │
  [confirm_placed] → CREATE (status: "available")
      │
  [mark_order_paid] → DELETE
  [cancel_combo]    → DELETE
  [expire_combo]    → DELETE
```

---

## Files liên quan

| File | Vai trò |
|---|---|
| `apps/integrations/firebase_client.py` | Client duy nhất giao tiếp Firestore |
| `apps/combos/services.py` | Sync combo + unit khi publish/cancel |
| `apps/orders/services.py` | Sync combo/unit khi thanh toán + pickup |
| `apps/lockers/services.py` | Helper `mark_unit_occupied/available` với Firebase sync |
| `apps/scheduler/scheduler.py` | Sync khi combo expire |

## Bugs đã fix

| Bug | File | Mô tả |
|---|---|---|
| `mark_order_paid` thiếu `delete_combo` | `orders/services.py:67` | Combo vẫn hiện trên Firestore sau khi bán |
| `expire_combo` fallback skip Firebase | `scheduler/scheduler.py:57` | Unit Firestore không được sync nếu DB đã `available` |
| `pickup_order/pickup_by_code` thiếu `delete_combo` | `orders/services.py:93,106` | Safety net — đảm bảo combo bị xóa dù bước 3 lỗi |
