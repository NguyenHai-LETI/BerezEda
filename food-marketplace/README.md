# БережЕда — Маркетплейс еды (Система 1)

Платформа торговли едой с интеграцией автоматических локеров, поддерживает несколько ролей: администратор, покупатель, владелец магазина, владелец локера.

## Структура

```
food-marketplace/
├── BE/   FastAPI, порт 8000
└── FE/   Next.js, порт 3000
```

## Требования

- Python 3.10+
- Node.js 18+
- PostgreSQL запущен локально, база данных `berezh_eda` создана
- Firebase project (service account JSON)

## Установка и запуск Backend (порт 8000)

```bash
cd food-marketplace/BE

# Создать и активировать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Установить зависимости
pip install -r requirements.txt

# Настроить переменные окружения
cp .env.example .env
# Заполнить .env: DATABASE_URL, SECRET_KEY, Firebase credentials, Fincode keys

# Запустить сервер (таблицы создаются автоматически при первом запуске)
python run.py
```

Swagger UI: http://localhost:8000/docs

## Установка и запуск Frontend (порт 3000)

```bash
cd food-marketplace/FE

# Установить зависимости
npm install

# Настроить переменные окружения
# Создать файл .env.local с переменными Firebase и API URL

# Запустить сервер разработки
npm run dev
```

Открыть: http://localhost:3000

## Переменные окружения

### BE (`BE/.env`) — скопировать из `.env.example` и заполнить

| Переменная | Описание |
|-----------|---------|
| `DATABASE_URL` | Строка подключения PostgreSQL |
| `SECRET_KEY` | JWT секретный ключ |
| `GOOGLE_APPLICATION_CREDENTIALS` | Путь к файлу Firebase service account JSON |
| `FIREBASE_PROJECT_ID` | Firebase project ID |
| `FIREBASE_WEB_API_KEY` | Firebase Web API key |
| `FINCODE_PUBLIC_KEY` | Публичный ключ Fincode |
| `FINCODE_SECRET_KEY` | Секретный ключ Fincode |
| `LOCKER_SIM_URL` | URL Системы 2 (по умолчанию: `http://localhost:8001/api`) |

### FE (`FE/.env.local`) — создать вручную

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

## Интеграция с Системой 2

Система 2 (locker-simulation) должна быть запущена на порту 8001 для работы функций локера.
Указать `LOCKER_SIM_URL=http://localhost:8001/api` в `BE/.env`.
