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
| `APP_NAME` | Nama aplikasi FastAPI |
| `API_V1_PREFIX` | Prefix endpoint API, default `/api/v1` |
| `ENVIRONMENT` | Environment aktif: `development`, `staging`, `production` |
| `DEBUG` | Mengaktifkan debug mode FastAPI |
| `JWT_SECRET_KEY` | Kunci JWT, minimal 32 karakter |
| `DATABASE_URL` | Connection string PostgreSQL penuh, opsional jika memakai `POSTGRES_*` |
| `ALGORITHM` | Algoritma JWT, default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Masa berlaku token login |
| `CORS_ORIGINS` | Origin frontend yang diizinkan |
| `ALLOWED_HOSTS` | Host header yang diizinkan |
| `LOG_LEVEL` | Level logging aplikasi |
| `LOG_DIR` | Folder output log |
| `PUBLIC_FORM_RATE_LIMIT` | Batas request public form per window |
| `PUBLIC_FORM_RATE_WINDOW_SECONDS` | Durasi window rate limit public form |
| `MAX_IMAGE_UPLOAD_MB` | Batas ukuran upload gambar |
| `MAX_VIDEO_UPLOAD_MB` | Batas ukuran upload video |
| `POSTGRES_SERVER` | Host PostgreSQL |
| `POSTGRES_USER` | Username PostgreSQL |
| `POSTGRES_PASSWORD` | Password PostgreSQL |
| `POSTGRES_PORT` | Port PostgreSQL |
| `POSTGRES_DB` | Nama database |
| `FIRST_SUPERUSER_EMAIL` | Email admin awal |
| `FIRST_SUPERUSER_PASSWORD` | Password admin awal |
| `CLOUDINARY_CLOUD_NAME` | Nama cloud Cloudinary |
| `CLOUDINARY_API_KEY` | API key Cloudinary |
| `CLOUDINARY_API_SECRET` | API secret Cloudinary |
| `CLOUDINARY_FOLDER` | Folder upload Cloudinary |
| `GEOAPIFY_REVERSE_GEOCODE_URL` | Endpoint reverse geocoding |
| `GEOAPIFY_API_KEY` | API key Geoapify |
| `GEOAPIFY_LANG` | Bahasa hasil reverse geocoding |

Backend masih menerima nama lama `PROJECT_NAME`, `API_V1_STR`, dan `SECRET_KEY` untuk kompatibilitas, tetapi nama baru di atas yang sebaiknya dipakai mulai sekarang.

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
| `admin` | sesuai `FIRST_SUPERUSER_EMAIL` | sesuai `FIRST_SUPERUSER_PASSWORD` |
| `head` | `head@example.com` | `head123` |
| `technician` | `technician@example.com` | `technician123` |

Nilai untuk akun admin dikontrol oleh `FIRST_SUPERUSER_EMAIL` dan `FIRST_SUPERUSER_PASSWORD` pada file `.env`. File `.env.example` sengaja memakai placeholder agar secret tidak ikut tersebar.

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

## Deploy Backend ke Vercel

Backend ini bisa dideploy sebagai project Vercel terpisah dari frontend, tetapi ada beberapa penyesuaian penting:

### 1. Siapkan database cloud

Vercel tidak menyediakan PostgreSQL lokal yang selalu aktif untuk project ini, jadi backend harus memakai database external yang bisa diakses publik, misalnya Supabase, Neon, atau Railway.

Saran paling praktis:

- gunakan 1 project Vercel khusus untuk `backend/`
- gunakan 1 database cloud khusus environment tersebut
- isi `DATABASE_URL` langsung dari provider database

Jika `DATABASE_URL` diisi, aplikasi akan memakainya. Jika kosong, aplikasi tetap fallback ke kombinasi `POSTGRES_*`.

Khusus jika memakai Supabase:

- untuk migrasi dari mesin lokal IPv4, `Session pooler` port `5432` biasanya paling aman
- untuk runtime serverless seperti Vercel, Supabase merekomendasikan `Transaction pooler` port `6543`

Repo ini sudah otomatis memakai `NullPool` dan menonaktifkan prepared statements saat mendeteksi URL Supabase transaction pooler.

### 2. Jalankan migrasi ke database cloud

Sebelum deploy, arahkan environment lokal ke database cloud lalu jalankan:

```powershell
cd backend
alembic upgrade head
```

Untuk saat ini lebih aman menjalankan migrasi secara manual atau lewat CI, bukan otomatis di setiap deploy preview.

### 3. Tambahkan environment variable di Vercel

Minimal variable yang perlu diisi:

| Variable | Wajib | Keterangan |
| --- | --- | --- |
| `JWT_SECRET_KEY` | Ya | Minimal 32 karakter |
| `DATABASE_URL` | Ya untuk deploy cloud | Connection string PostgreSQL penuh |
| `API_V1_PREFIX` | Opsional | Default `/api/v1` |
| `ENVIRONMENT` | Ya | Gunakan `production` saat live |
| `DEBUG` | Opsional | Default `false` |
| `ALGORITHM` | Opsional | Default `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Opsional | Default `30` |
| `CORS_ORIGINS` | Ya | Origin frontend yang diizinkan |
| `ALLOWED_HOSTS` | Ya | Domain backend yang valid |
| `FIRST_SUPERUSER_EMAIL` | Ya | Admin awal |
| `FIRST_SUPERUSER_PASSWORD` | Ya | Password admin awal |

Contoh `CORS_ORIGINS` setelah frontend online:

```text
https://frontend-anda.vercel.app,http://localhost:5173,http://127.0.0.1:5173
```

### 4. Deploy `backend/` sebagai Vercel project sendiri

Pilihan paling aman:

1. Import repo ke Vercel.
2. Buat project khusus backend.
3. Set Root Directory ke `backend`.
4. Tambahkan semua environment variable.
5. Deploy.

Repo ini sudah disiapkan dengan file `index.py` di root `backend/` agar Vercel punya entrypoint Python yang jelas.

### 5. Verifikasi endpoint hasil deploy

Setelah deploy berhasil, cek:

- `/`
- `/health`
- `/docs`
- `/api/v1/auth/login`

Jika deploy sukses tetapi request dari frontend ditolak browser, biasanya masalahnya ada di `CORS_ORIGINS`.

## Catatan Integrasi

- Default `CORS_ORIGINS` sudah mengizinkan frontend lokal di `http://localhost:5173` dan `http://127.0.0.1:5173`.
- Frontend mengakses backend melalui base URL `http://127.0.0.1:8000/api/v1`.
- Migrasi perlu dijalankan terlebih dahulu karena seeding user tidak membuat tabel secara otomatis.
