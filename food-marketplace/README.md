# BerezEda — Food Marketplace (Hệ thống 1)

Nền tảng thương mại thực phẩm tích hợp locker tự động, hỗ trợ đa vai trò: admin, khách hàng, chủ cửa hàng, chủ locker.

## Cấu trúc

```
food-marketplace/
├── BE/   FastAPI, port 8000
└── FE/   Next.js, port 3000
```

## Yêu cầu

- Python 3.10+
- Node.js 18+
- PostgreSQL chạy local, database `berezh_eda` đã được tạo
- Firebase project (service account JSON)

## Cài đặt & chạy Backend (port 8000)

```bash
cd food-marketplace/BE

# Tạo và kích hoạt virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Cài dependencies
pip install -r requirements.txt

# Cấu hình môi trường
cp .env.example .env
# Sửa .env: DATABASE_URL, SECRET_KEY, Firebase credentials, Fincode keys

# Khởi động server (tạo bảng tự động lần đầu)
python run.py
```

Swagger UI: http://localhost:8000/docs

## Cài đặt & chạy Frontend (port 3000)

```bash
cd food-marketplace/FE

# Cài dependencies
npm install

# Cấu hình môi trường
# Tạo file .env.local với các biến Firebase và API URL

# Chạy development server
npm run dev
```

Truy cập: http://localhost:3000

## Biến môi trường

### BE (`BE/.env`) — copy từ `.env.example` rồi điền

| Biến | Mô tả |
|------|-------|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT secret key |
| `GOOGLE_APPLICATION_CREDENTIALS` | Đường dẫn đến file Firebase service account JSON |
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `FIREBASE_WEB_API_KEY` | Firebase Web API key |
| `FINCODE_PUBLIC_KEY` | Fincode payment public key |
| `FINCODE_SECRET_KEY` | Fincode payment secret key |
| `LOCKER_SIM_URL` | URL của Hệ thống 2 (mặc định: `http://localhost:8001/api`) |

### FE (`FE/.env.local`) — tạo thủ công

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

## Tích hợp với Hệ thống 2

Hệ thống 2 (locker-simulation) phải chạy ở port 8001 để các tính năng locker hoạt động.
Cấu hình `LOCKER_SIM_URL=http://localhost:8001/api` trong `BE/.env`.
