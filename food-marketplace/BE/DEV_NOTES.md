# Dev Notes — Known Issues & Workarounds

## Ports

| Service | Port | Command |
|---------|------|---------|
| Backend API | **8001** | `.venv\Scripts\uvicorn apps.core.main:app --host 0.0.0.0 --port 8000` |
| Frontend | **3001** | `npm run dev` (trong `/graduation_project`) |

> **Tại sao không dùng port mặc định (8000 / 3000)?**
> Xem mục "Zombie Processes" bên dưới.

---

## Bug đã fix: `dependencies.py` — db/token as query params

**Vấn đề:** `get_current_user(db, token: str)` trong `services.py` được dùng như FastAPI `Depends()`.
FastAPI hiểu `db` và `token` là **query parameters bắt buộc**, không phải dependency injection.

**Triệu chứng:** Mọi protected endpoint trả về:
```json
{"status": 400, "message": "Field required", "errors": [{"loc": ["query", "db"]}, {"loc": ["query", "token"]}]}
```

**Fix:** `apps/auth/dependencies.py` — `get_authenticated_user` đọc user từ `request.state.user`
(đã được middleware `AuthMiddleware` set sẵn):
```python
def get_authenticated_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user
```

**Lưu ý:** `get_current_user` trong `services.py` KHÔNG được dùng làm `Depends()`.

---

## Zombie Processes — Windows

**Vấn đề:** Khi uvicorn chạy với `--reload` (watchfiles), nó tạo reloader process + server child process.
Khi kill bằng `taskkill` hoặc `wmic`, watchfiles reloader tự restart child → process cũ vẫn giữ port.

**Triệu chứng:** Nhiều `python.exe` cùng LISTEN trên port 8000:
```
TCP  0.0.0.0:8000  LISTENING  9100
TCP  0.0.0.0:8000  LISTENING  10452
TCP  0.0.0.0:8000  LISTENING  5580
...
```
Server mới không bind được port 8000, start thất bại silently.

**Workaround:**
- Dùng port khác: `--port 8001`
- KHÔNG dùng `--reload` khi dev (dùng `uvicorn` thẳng, không qua `run.py`)
- Kill đúng cách: `cmd /c "taskkill /F /PID <pid> /T"` (cần `/T` để kill cả tree)

**Cách start đúng:**
```bash
# Backend (không reload)
.venv\Scripts\uvicorn apps.core.main:app --host 0.0.0.0 --port 8001

# Hoặc dùng reload nhưng nhớ kill /T khi dừng
.venv\Scripts\uvicorn apps.core.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Bcrypt / Passlib compatibility

**Vấn đề:** `passlib[bcrypt]` không tương thích với `bcrypt >= 5.0`.

**Fix:** Cố định `bcrypt==4.0.1` trong requirements.txt và re-hash passwords sau khi install.

**Passwords mặc định (sau seed):**

| Email | Password | Role |
|-------|----------|------|
| admin@berezh-eda.ru | Admin@123 | admin |
| customer@berezh-eda.ru | Customer@123 | customer |
| shop@berezh-eda.ru | Shop@123 | owner_shop |
| locker@berezh-eda.ru | Locker@123 | owner_locker |

---

## Data seeded (dev)

- **Locker:** `BerezhEda Postamat #1` — Москва, Охотный Ряд (5 units, status=available)
- **Shop:** `Tokyo Restaurant` (owner: shop@berezh-eda.ru)
- Shop đã được associate với Locker → seller có thể chọn unit khi đăng bán.

