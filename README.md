# Backend SLA

Backend ini adalah API untuk aplikasi SLA/ticketing yang dibangun dengan FastAPI. Layanan ini menangani autentikasi internal, pembuatan tiket dari portal publik, pelacakan status tiket, serta seeding role dan user awal saat aplikasi dijalankan.

## Fitur Utama

- API `FastAPI` untuk kebutuhan publik dan internal.
- Login internal berbasis JWT.
- Endpoint publik untuk membuat tiket dan melacak status tiket.
- Integrasi database PostgreSQL dengan SQLAlchemy dan Alembic.
- Seeder default untuk role `admin`, `head`, dan `technician`.
- Pengujian dasar menggunakan `pytest`.

## Stack

- Python
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- PyJWT
- `pwdlib[argon2]`
- Pytest

## Struktur Singkat

```text
backend/
|-- alembic/           # konfigurasi dan versi migrasi database
|-- app/
|   |-- api/           # router dan endpoint API
|   |-- core/          # konfigurasi, konstanta, security
|   |-- db/            # session database dan seeding awal
|   |-- models/        # model SQLAlchemy
|   |-- schemas/       # schema request/response
|   |-- services/      # business logic
|   `-- utils/         # helper tambahan
|-- tests/             # automated tests
|-- .env.example
|-- alembic.ini
`-- requirements.txt
```

## Persiapan Lokal

### 1. Install dependency

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Siapkan environment variable

```powershell
Copy-Item .env.example .env
```

Variabel yang digunakan:

| Variable | Keterangan |
| --- | --- |
| `PROJECT_NAME` | Nama aplikasi FastAPI |
| `API_V1_STR` | Prefix endpoint API, default `/api/v1` |
| `SECRET_KEY` | Kunci JWT, minimal 32 karakter |
| `ALGORITHM` | Algoritma JWT, default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Masa berlaku token login |
| `POSTGRES_SERVER` | Host PostgreSQL |
| `POSTGRES_USER` | Username PostgreSQL |
| `POSTGRES_PASSWORD` | Password PostgreSQL |
| `POSTGRES_PORT` | Port PostgreSQL |
| `POSTGRES_DB` | Nama database |
| `CORS_ORIGINS` | Origin frontend yang diizinkan |
| `FIRST_SUPERUSER_EMAIL` | Email admin awal |
| `FIRST_SUPERUSER_PASSWORD` | Password admin awal |

### 3. Jalankan PostgreSQL

Dari root project:

```powershell
docker compose up -d postgres
```

### 4. Jalankan migrasi database

```powershell
cd backend
alembic upgrade head
```

### 5. Jalankan server

```powershell
uvicorn app.main:app --reload
```

API akan tersedia di `http://127.0.0.1:8000`.

## Seed Data Default

Saat aplikasi startup, fungsi `init_db()` akan memastikan role dan user default tersedia. Setelah migrasi dijalankan dan server aktif, akun berikut siap dipakai:

| Role | Email | Password |
| --- | --- | --- |
| `admin` | `admin@example.com` | `admin123` |
| `head` | `head@example.com` | `head123` |
| `technician` | `technician@example.com` | `technician123` |

Nilai untuk akun admin bisa diubah melalui `FIRST_SUPERUSER_EMAIL` dan `FIRST_SUPERUSER_PASSWORD` pada file `.env`.

## Endpoint Penting

| Method | Endpoint | Keterangan |
| --- | --- | --- |
| `GET` | `/` | Pesan sambutan API |
| `GET` | `/health` | Health check sederhana |
| `POST` | `/api/v1/auth/login` | Login internal |
| `GET` | `/api/v1/auth/me` | Profil user login |
| `POST` | `/api/v1/public/tickets` | Buat tiket dari portal publik |
| `GET` | `/api/v1/public/tracking` | Tracking tiket via `ticket_code` dan `phone_number` |

Dokumentasi interaktif FastAPI tersedia di:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/redoc`

## Testing

Jalankan test backend dengan:

```powershell
cd backend
pytest
```

## Catatan Integrasi

- Default `CORS_ORIGINS` sudah mengizinkan frontend lokal di `http://localhost:5173` dan `http://127.0.0.1:5173`.
- Frontend mengakses backend melalui base URL `http://127.0.0.1:8000/api/v1`.
- Migrasi perlu dijalankan terlebih dahulu karena seeding user tidak membuat tabel secara otomatis.
