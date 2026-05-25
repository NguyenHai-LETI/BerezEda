# Симулятор локера — Система 2

Симулирует экран реального локера, интегрирован с маркетплейсом еды (Система 1).

## Структура

```
locker-simulation/
├── BE/   FastAPI, порт 8001
└── FE/   Next.js, порт 3001
```

## Запуск

### Backend (порт 8001)

```bash
cd locker-simulation/BE
pip install -r requirements.txt   # первый раз
python run.py
```

### Frontend (порт 3001)

```bash
cd locker-simulation/FE
npm install      # первый раз
npm run dev
```

## Требования

- PostgreSQL запущен локально, база данных `locker_simulation` создана
- Система 1 запущена на порту 8000 (для работы callback)

## Проверка

```bash
# Проверка работоспособности BE
curl http://localhost:8001/health

# FE
open http://localhost:3001
```

## API Endpoints (BE)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/locker-codes/register-deposit` | Система 1 вызывает после назначения локера магазином → создаёт код AA |
| POST | `/api/locker-codes/register-pickup` | Система 1 вызывает после оплаты покупателем → создаёт код BB |
| POST | `/api/qr/validate` | Валидация QR-кода, возвращает code_type + IDs |
| POST | `/api/simulate/deposit-confirmed` | Подтверждение помещения заказа в локер (код AA) |
| POST | `/api/simulate/pickup-confirmed` | Подтверждение извлечения заказа из локера (код BB) |
| GET  | `/health` | Проверка работоспособности |

## Сценарии работы

### Продавец кладёт заказ в локер (код AA)
1. Система 1 вызывает `register-deposit` → Система 2 создаёт код `AA123456`
2. Система 1 отображает QR с кодом AA для продавца
3. Продавец сканирует QR в симуляторе локера
4. Система 2 валидирует → отображает кнопку «Симулировать помещение товара»
5. Продавец нажимает кнопку → Система 2 делает callback в Систему 1 `/internal/locker-sim/deposit`
6. Система 1 обновляет: статус комбо → `available`, статус ячейки → `occupied`, синхронизация Firebase

### Покупатель забирает заказ (код BB)
1. Система 1 вызывает `register-pickup` после оплаты → создаётся код `BB654321`
2. Система 1 отображает QR с кодом BB для покупателя (страница деталей заказа)
3. Покупатель сканирует QR в симуляторе локера
4. Система 2 валидирует → отображает кнопку «Симулировать извлечение товара»
5. Покупатель нажимает кнопку → Система 2 делает callback в Систему 1 `/internal/locker-sim/pickup`
6. Система 1 обновляет: статус заказа → `completed`, статус ячейки → `available`, удаление комбо из Firebase

## QR-коды

- **AA**: код помещения, для продавца, формат `AA{6 цифр}`, истекает при перезаписи новым заказом
- **BB**: код получения, для покупателя, формат `BB{6 цифр}`, истекает по `pickup_deadline` заказа
- 6 цифр уникальны среди всех активных кодов

## Переменные окружения

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
