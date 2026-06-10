# Fresh Demo Database Setup

Use this when you want a clean client demo database without touching `bodyshopdb`.

## 1. Create Demo Database

If PostgreSQL is installed in `C:\Program Files\PostgreSQL\18`, run:

```powershell
$env:PGPASSWORD="Admin@123"
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -h localhost -p 5432 -U postgres bodyshop_demo
```

If database already exists and you want to recreate it:

```powershell
$env:PGPASSWORD="Admin@123"
& "C:\Program Files\PostgreSQL\18\bin\dropdb.exe" -h localhost -p 5432 -U postgres bodyshop_demo
& "C:\Program Files\PostgreSQL\18\bin\createdb.exe" -h localhost -p 5432 -U postgres bodyshop_demo
```

Only run `dropdb` for the demo database, never for `bodyshopdb`.

## 2. Switch Environment

Copy `.env.demo.example` to `.env.demo`, then use it as `.env` while running the demo.

Simplest manual method:

```powershell
Copy-Item .env .env.local.backup -Force
Copy-Item .env.demo.example .env -Force
```

To switch back:

```powershell
Copy-Item .env.local.backup .env -Force
```

## 3. Apply Migrations

```powershell
.\.venv\Scripts\python.exe manage.py migrate
```

## 4. Seed Demo Data

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo_data
```

Default demo password for all demo users:

```text
Demo@123
```

Demo users:

```text
demo_admin
demo_manager
demo_advisor
demo_denter
demo_painter
demo_technician
demo_reception
```

## 5. Run Server

```powershell
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

For Flutter demo, update `apiBaseUrl` to local/ngrok URL ending with `/api/mobile`.
