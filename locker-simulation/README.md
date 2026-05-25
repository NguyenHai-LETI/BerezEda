# Locker Simulation — Hệ thống 2

Mô phỏng màn hình locker thực tế, tích hợp với hệ thống food-marketplace (Hệ thống 1).

## Cấu trúc

```
locker-simulation/
├── BE/   FastAPI, port 8001
└── FE/   Next.js, port 3001
```

## Khởi động

### Backend (port 8001)

```bash
cd locker-simulation/BE
pip install -r requirements.txt   # lần đầu
python run.py
```

### Frontend (port 3001)

```bash
cd locker-simulation/FE
npm install      # lần đầu
npm run dev
```

## Yêu cầu

- PostgreSQL chạy local, database `locker_simulation` đã được tạo
- Hệ thống 1 chạy ở port 8000 (để callback hoạt động)

## Kiểm tra

```bash
# BE health check
curl http://localhost:8001/health

# FE
open http://localhost:3001
```

## API Endpoints (BE)

| Method | Path | Mô tả |
|--------|------|--------|
| POST | `/api/locker-codes/register-deposit` | Hệ thống 1 gọi sau khi shop assign locker → tạo mã AA |
| POST | `/api/locker-codes/register-pickup` | Hệ thống 1 gọi sau khi user thanh toán → tạo mã BB |
| POST | `/api/qr/validate` | Validate mã QR, trả về code_type + IDs |
| POST | `/api/simulate/deposit-confirmed` | Xác nhận đặt hàng vào locker (mã AA) |
| POST | `/api/simulate/pickup-confirmed` | Xác nhận lấy hàng ra khỏi locker (mã BB) |
| GET  | `/health` | Health check |

## Luồng hoạt động

### Seller đặt hàng vào locker (mã AA)
1. Hệ thống 1 gọi `register-deposit` → Hệ thống 2 tạo mã `AA123456`
2. Hệ thống 1 hiển thị QR mã AA cho seller
3. Seller quét QR trên Locker Simulator
4. Hệ thống 2 validate → hiển thị nút "Mô phỏng cho đồ vào"
5. Seller bấm nút → Hệ thống 2 callback vào Hệ thống 1 `/internal/locker-sim/deposit`
6. Hệ thống 1 cập nhật: combo status → `available`, unit status → `occupied`, sync Firebase

### Buyer lấy hàng ra (mã BB)
1. Hệ thống 1 gọi `register-pickup` sau khi thanh toán → tạo mã `BB654321`
2. Hệ thống 1 hiển thị QR mã BB cho buyer (trang chi tiết đơn hàng)
3. Buyer quét QR trên Locker Simulator
4. Hệ thống 2 validate → hiển thị nút "Mô phỏng lấy đồ ra"
5. Buyer bấm nút → Hệ thống 2 callback vào Hệ thống 1 `/internal/locker-sim/pickup`
6. Hệ thống 1 cập nhật: order status → `completed`, unit status → `available`, xóa combo khỏi Firebase

## Mã QR

- **AA**: mã deposit, dành cho seller, format `AA{6 chữ số}`, hết hạn khi bị ghi đè bởi order mới
- **BB**: mã pickup, dành cho buyer, format `BB{6 chữ số}`, hết hạn theo `pickup_deadline` của order
- 6 chữ số là duy nhất trên toàn bộ các mã đang active

## Biến môi trường

### BE (`BE/.env`)
```
DATABASE_URL=postgresql://postgres:12345678@localhost:5432/locker_simulation
SYSTEM1_URL=http://localhost:8000/api
```

### FE (`FE/.env.local`)
```
NEXT_PUBLIC_LOCKER_SIM_API=http://localhost:8001/api
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
```
