# Backend API

Backend API with:

- **Core**: FastAPI, config, database (local PostgreSQL), middleware, exception handler
- **Auth**: JWT (access + refresh), role-based permissions
- **Users**: User model, registration, login by user type (admin, customer, owner_shop, owner_locker)

## Requirements

- Python 3.10+
- Local PostgreSQL: **localhost**, user **postgres**, password **12345678**, database **locker**

## Installation

```bash
cd <project directory>
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
```

## Running

1. Create the **locker** database in PostgreSQL (if it does not exist):
   ```sql
   CREATE DATABASE locker;
   ```

2. Install and run:
   ```bash
   pip install -r requirements.txt
   copy .env.example .env   # Windows
   # cp .env.example .env   # Linux/Mac

   # Start the server (tables are created on first run)
   python run.py
   # or: uvicorn apps.core.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Swagger

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Login (user types)

| Role        | Email                   | Password    |
|------------|-------------------------|-------------|
| admin      | admin@example.com       | Admin@123   |
| customer   | customer@example.com    | Customer@123|
| owner_shop | owner_shop@example.com  | Shop@123    |
| owner_locker | owner_locker@example.com | Locker@123  |

1. **POST** `/api/auth/token` with body:
   ```json
   { "username": "admin@example.com", "password": "Admin@123" }
   ```
2. Receive `access` and `refresh` tokens.
3. Call protected APIs with header: `Authorization: Bearer <access>`.
4. **GET** `/api/users/me` – any logged-in user.
5. **GET** `/api/users/me/admin` – admin only.
6. **GET** `/api/users/me/customer` – customer only.
7. **GET** `/api/users/me/shop-owner` – owner_shop or admin.
8. **GET** `/api/users/me/locker-owner` – owner_locker or admin.

## Project structure

```
<project directory>/
  apps/
    core/         # config, database, middleware, error_middleware, schemas, main
    auth/         # JWT, RevokedToken, login, refresh, logout, permissions
    users/        # User model, CRUD, register, /me by role
  requirements.txt
  .env.example
  README.md
```

## Push to GitHub

1. Create a new repository on GitHub (do not add README, .gitignore, or license).
2. From the project root (e.g. `Locker-api`), run:

```bash
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub username and repository name.
