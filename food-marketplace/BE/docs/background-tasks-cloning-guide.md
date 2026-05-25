# Hướng dẫn clone các task chạy nền từ Standard BE

## Nguyên tắc chung

> **Ưu tiên sử dụng eta (lên lịch 1 lần) thay vì task chạy định kì (beat) khi có thể.**

Dự án hiện tại dùng **APScheduler với MemoryJobStore** thay vì Celery/Redis. Các hàm lên lịch 1 lần tương đương `apply_async(eta=...)` của Celery:
- `scheduler.add_job(func, 'date', run_date=..., id=...)`
- Khi server restart: `reschedule_all_on_startup()` khôi phục lại các job bị mất.

---

## Phân loại task trong Standard BE

### 1. Task định kì (Celery Beat) — 4 task

| Task | Chu kỳ | Có thể thay bằng eta? | Ghi chú |
|------|--------|----------------------|---------|
| `cleanup_revoked_tokens` | Hàng ngày | **Không** | Quét toàn bộ token hết hạn, không có event trigger cụ thể |
| `clean_expired_combos` | 200s | **Có thể bỏ** nếu dùng eta đầy đủ | Safety net — chỉ cần nếu eta bị miss. Hiện tại `reschedule_all_on_startup()` đã xử lý |
| `clean_pickup_deadline_passed` | 200s | **Có thể bỏ** nếu dùng eta | Tương tự — lên lịch eta khi tạo order, startup sweep xử lý miss |
| `reset_monthly_shop_stats` | Đầu tháng | **Không** | Chạy theo lịch cố định, không có event trigger |

**Khi clone:**
- `cleanup_revoked_tokens` → Dùng APScheduler interval hoặc cron job
- `clean_expired_combos` → **Không cần** nếu đã có `schedule_combo_expiry()` + `reschedule_all_on_startup()`
- `clean_pickup_deadline_passed` → **Không cần** nếu đã có `schedule_order_expiry()` + startup sweep
- `reset_monthly_shop_stats` → Dùng APScheduler cron trigger: `scheduler.add_job(func, 'cron', day=1, hour=0)`

### 2. Task lên lịch 1 lần (eta/countdown) — 5 task

| Task | Trigger | Cách clone |
|------|---------|------------|
| `send_pickup_deadline` | Khi order được tạo, eta = pickup_deadline | `scheduler.add_job(func, 'date', run_date=pickup_deadline)` |
| `check_preparation_timeout` | Khi combo chuyển PREPARATION, countdown = timeout | `scheduler.add_job(func, 'date', run_date=now+timeout)` |
| `send_deadline_put_to_locker` | Khi combo cần đặt vào locker, eta = deadline | `scheduler.add_job(func, 'date', run_date=deadline)` |
| `schedule_product_expiry_notifications` | Khi combo bắt đầu bán, eta = thời điểm cảnh báo | `scheduler.add_job(func, 'date', run_date=warning_time)` |
| `send_product_expiry_reached` | Khi combo hết hạn, eta = expiry_time | Đã có: `schedule_combo_expiry()` |

**Đây là loại task phù hợp nhất với APScheduler.** Clone trực tiếp, thay `apply_async(eta=X)` bằng `scheduler.add_job(..., run_date=X)`.

### 3. Task fire-and-forget (immediate) — ~20 task

| Nhóm | Ví dụ | Cách clone |
|------|-------|------------|
| Firebase sync | `sync_unit_to_firebase`, `delete_combo_from_firebase` | Gọi trực tiếp (không cần queue) |
| Push notification | `send_push_to_buyer`, `send_push_to_shop` | Gọi trực tiếp hoặc dùng `threading.Thread` |
| Email | `send_order_confirmation_email` | Gọi trực tiếp hoặc `threading.Thread` |

**Khi clone:** Thay `.delay()` bằng gọi hàm trực tiếp. Nếu cần non-blocking, dùng:
```python
import threading
threading.Thread(target=sync_func, args=(...,), daemon=True).start()
```

---

## Đã clone trong dự án hiện tại

| Chức năng | File | Cách hoạt động |
|-----------|------|----------------|
| Combo hết hạn bán | `apps/scheduler/scheduler.py` → `expire_combo()` | eta: lên lịch khi combo confirm, startup sweep khôi phục |
| Order hết hạn | `apps/scheduler/scheduler.py` → `expire_order()` | eta: lên lịch khi tạo order |
| Startup recovery | `apps/scheduler/scheduler.py` → `reschedule_all_on_startup()` | Quét combo/order chưa hết hạn, lên lịch lại hoặc expire ngay |

---

## Checklist khi clone task mới

1. **Xác định loại task**: định kì, eta, hay fire-and-forget?
2. **Nếu có thể dùng eta** → Dùng `scheduler.add_job('date', run_date=...)` thay vì beat
3. **Thêm startup recovery** vào `reschedule_all_on_startup()` để xử lý job bị miss khi restart
4. **Fire-and-forget** → Gọi trực tiếp, không cần queue
5. **Chỉ dùng interval/cron** cho task thực sự không có event trigger (cleanup token, reset stats)

---

## Khi nào cần Celery/Redis?

Hiện tại **chưa cần**. APScheduler đủ cho quy mô nhỏ. Cân nhắc chuyển sang Celery khi:
- Cần chạy nhiều worker song song
- Cần retry tự động cho task thất bại
- Cần task queue phân tán (multiple server instances)
- MemoryJobStore gây mất job quá thường xuyên
