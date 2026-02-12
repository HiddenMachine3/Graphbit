# Graphbit Setup Instructions

This guide will walk you through setting up the Graphbit development environment on your local machine.

## Prerequisites

### Python
- **Required version:** Python 3.12 or higher
- Verify your installation:
  ```powershell
  python --version
  ```

### PostgreSQL (pgvector) via Docker (Windows)

Graphbit now uses a **containerized PostgreSQL** with **pgvector** for local development.

# 🐘 pgvector Setup on Windows Using Docker

This guide documents the complete setup process for running PostgreSQL with pgvector using Docker on Windows.

---

# 1️⃣ Install Docker Desktop

- Download and install **Docker Desktop for Windows**
- Start Docker Desktop
- Ensure Docker is running before proceeding

You can verify Docker is working by running:

```bash
docker --version
```

---

# 2️⃣ Run pgvector PostgreSQL Container

In PowerShell, run:

```powershell
docker run -d `
  --name pgvector `
  -e POSTGRES_PASSWORD=admin `
  -p 5433:5432 `
  ankane/pgvector
```

Explanation:

* `--name pgvector` → Name of the container
* `POSTGRES_PASSWORD=admin` → Sets the PostgreSQL password
* `-p 5433:5432` → Maps local port 5433 to container port 5432
* `ankane/pgvector` → Prebuilt PostgreSQL image with pgvector installed

---

# 3️⃣ Verify Container Is Running

```bash
docker ps
```

Expected output should include something like:

```
0.0.0.0:5433->5432/tcp
```

This confirms:

* Container is running
* Port 5433 is mapped correctly

---

# 4️⃣ Connect Using pgAdmin

In pgAdmin:

1. Right click **Servers**
2. Click **Create → Server**
3. Fill in:

General:

* Name: `pgvector-docker`

Connection:

* Host: `localhost`
* Port: `5433`
* Username: `postgres`
* Password: `admin`
* Maintenance DB: `postgres`

Click **Save**

---

# 5️⃣ Confirm You’re Connected To Docker PostgreSQL

Open Query Tool and run:

```sql
SELECT version();
```

You should see something like:

```
PostgreSQL 15.x on x86_64-pc-linux-gnu
```

If it says `linux-gnu`, you are connected to the Docker container (correct).

If it says `windows`, you are connected to your native Windows PostgreSQL (wrong).

---

# 6️⃣ Enable pgvector Extension

Run:

```sql
CREATE EXTENSION vector;
```

Verify installation:

```sql
SELECT * FROM pg_extension;
```

You should see:

```
vector
```

---

# 7️⃣ Test pgvector Is Working

Create a test table:

```sql
CREATE TABLE test_vectors (
    id SERIAL PRIMARY KEY,
    embedding vector(3)
);
```

Insert a test vector:

```sql
INSERT INTO test_vectors (embedding)
VALUES ('[1,2,3]');
```

If it returns:

```
INSERT 0 1
```

pgvector is successfully installed and operational.

---

# 🎉 Setup Complete

You now have:

* PostgreSQL running inside Docker
* pgvector extension enabled
* Isolated from your Windows PostgreSQL installation
* Ready for embedding storage and similarity search

---

Note: The backend reads its database settings from `Backend/.env`. The default `DATABASE_URL` is already configured for Docker on port `5433`.

---

# 🪟 pgvector Setup on Windows (Local, No Docker)

This is the **local Windows** setup path (no Docker, no Visual Studio build tools). It uses Conda packages for PostgreSQL + pgvector.

## 1️⃣ Install Miniconda (if not already installed)

- Download and install Miniconda for Windows.
- Open a new PowerShell and verify:

```powershell
conda --version
```

## 2️⃣ Create the local PostgreSQL + pgvector Conda environment

From the repository root:

```powershell
Set-Location 'S:\files\files\Projects\Projects\Graphbit'
conda create -n graphbit-pgvector-db -c conda-forge postgresql=16.10 pgvector=0.8.1 -y
```

## 3️⃣ Start local Postgres and enable pgvector

Use the automation script in this repo:

```powershell
powershell -ExecutionPolicy Bypass -File "Backend\scripts\setup_local_pgvector_db.ps1" -CondaEnvName "graphbit-pgvector-db" -Port 5434 -DbUser postgres -DbPassword admin -DbName postgres
```

What this script does:

- Initializes a local data directory at `Backend/.local_pgvector_db/data` (first run only)
- Starts PostgreSQL on `127.0.0.1:5434`
- Runs `CREATE EXTENSION IF NOT EXISTS vector;`
- Runs a smoke test insert/select on a `vector(3)` column

## 4️⃣ Configure backend connection string

In `Backend/.env`, set:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:admin@localhost:5434/postgres
```

## 5️⃣ Stop local Postgres when needed

```powershell
powershell -ExecutionPolicy Bypass -File "Backend\scripts\stop_local_pgvector_db.ps1"
```

## 6️⃣ Notes from the working setup

- Native Windows PostgreSQL + pgvector compilation requires MSVC build tools; Conda avoids this.
- If backend startup fails with `No module named uvicorn`, use the interpreter that has dependencies installed (example below).

---

### Node.js & npm
- If npm is not installed, first install Node.js which includes npm
- Verify installation:
  ```powershell
  npm --version
  node --version
  ```

## Installation Steps

### 1. Install Python Dependencies

Install both the root and backend requirements files:

```powershell
Set-Location 'S:\files\files\Projects\Projects\Graphbit'
pip install -r requirements.txt
Set-Location 'S:\files\files\Projects\Projects\Graphbit\Backend'
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

Navigate to the frontend directory and install Next.js and npm dependencies:

```powershell
cd "S:\files\files\Projects\Projects\Graphbit\frontend"
npm install
```

### 3. (Optional) Seed the Database with Example Data

If you want to populate the database with example knowledge graphs and questions:

```powershell
Set-Location 'S:\files\files\Projects\Projects\Graphbit\Backend'
python seed_data.py
```

This creates sample nodes, edges, questions, and users for testing. Skip this step if you prefer to start with an empty database.

Use `python seed_data.py --reset` to flush the current db, and start fresh with the default db content.

### 4. Running the tests

```powershell
Set-Location 'S:\files\files\Projects\Projects\Graphbit'; python -m pytest tests/ -v --tb=short 2>&1 | Select-Object -Last 50  
```


## Running the Application

The application runs on two separate servers: Backend API and Frontend. You'll need **two terminal windows** to run them simultaneously.

### Terminal 1: Start the Backend API

```powershell
Set-Location 'S:\files\files\Projects\Projects\Graphbit\Backend'
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If `python -m uvicorn` fails due to interpreter mismatch, run with the explicit Python path:

```powershell
Set-Location 'S:\files\files\Projects\Projects\Graphbit\Backend'
& "C:\Users\cosmo\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at: `http://localhost:8000`

**Swagger API Documentation:** `http://localhost:8000/docs`

### Terminal 2: Start the Frontend
```powershell
cd "S:\files\files\Projects\Projects\Graphbit\frontend"
cmd /c npm run dev
```

The frontend will typically be available at: `http://localhost:3000`

## Troubleshooting

### Backend won't start
- If using Docker setup: ensure Docker Desktop is running and the `pgvector` container is up (`docker ps`)
- If using local Windows setup: run `Backend\scripts\setup_local_pgvector_db.ps1` and verify DB is on port `5434`
- Verify `DATABASE_URL` in `Backend/.env` matches your setup (Docker `5433`, local Conda `5434`)
- Check that port 8000 is not already in use
- Verify Python dependencies installed correctly: `pip list`

### Frontend won't start
- Ensure npm dependencies are installed: `npm list`
- Check that port 3000 is not already in use
- Clear node_modules and reinstall if issues persist:
  ```powershell
  rm -r node_modules
  npm install
  ```

### Port conflicts
- If ports 3000 or 8000 are in use, modify the commands:
  - Backend: Add `--port 8001` flag
  - Frontend: Add `-- -p 3001` flag

## Next Steps

Once both servers are running, visit `http://localhost:3000` to access the Graphbit application. The frontend will communicate with the backend API at `http://localhost:8000`.

