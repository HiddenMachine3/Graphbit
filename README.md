# Graphbit Setup Instructions

This guide will walk you through setting up the Graphbit development environment on your local machine.

## Prerequisites

### 1. Docker

Graphbit ships with a backend docker-compose stack that brings up the API and database together.

---

### 2. Node.js & npm
- If npm is not installed, first install Node.js which includes npm
- Verify installation:
  ```powershell
  npm --version
  node --version
  ```

## Installation Steps

### 1. Build the backend containers (Docker)

```powershell
cd "Backend"
docker-compose up --build
```

This starts the backend API and Postgres/pgvector for local development. The backend reads its settings from `Backend/.env`.

### 2. Install Frontend Dependencies

Navigate to the frontend directory and install Next.js and npm dependencies:

```powershell
cd "frontend"
npm install
```

### 3. (Optional) Seed the Database with Example Data

If you want to populate the database with example knowledge graphs and questions:

```powershell
cd "Backend"
python seed_data.py
```

This creates sample nodes, edges, questions, and users for testing. Skip this step if you prefer to start with an empty database.

Use `python seed_data.py --reset` to flush the current db, and start fresh with the default db content.

### 4. (Optional) Running the tests

```powershell
python -m pytest tests/ -v --tb=short 2>&1 | Select-Object -Last 50
```


## Running the Application

The application runs on two separate servers: Backend API and Frontend. You'll need **two terminal windows** to run them simultaneously.

### Terminal 1: Start the Backend (Docker)

```powershell
cd "Backend"
docker-compose up
```

The backend will be available at: `http://localhost:8000`

**Swagger API Documentation:** `http://localhost:8000/docs`

### Terminal 2: Start the Frontend
```powershell
cd "frontend"
cmd /c npm run dev
```

The frontend will typically be available at: `http://localhost:3000`

## Troubleshooting

### Backend won't start
- If using Docker setup: ensure Docker Desktop is running and the `pgvector` container is up (`docker ps`)
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

---

### Optional: Local backend setup (no Docker, Python 3.12)

<details>
<summary>Show optional local setup steps</summary>

This is the optional **local Windows** setup path (no Docker, no Visual Studio build tools). It uses Conda packages for PostgreSQL + pgvector.

## 1️⃣ Install Miniconda (if not already installed)

- Download and install Miniconda for Windows.
- Open a new PowerShell and verify:

```powershell
conda --version
```

## 2️⃣ Create the local PostgreSQL + pgvector Conda environment

From the repository root:

```powershell
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

In `Backend/.env`, replace the existing `DATABASE_URL` with your local Postgres URL:

```dotenv
DATABASE_URL=postgresql+psycopg://postgres:admin@localhost:5434/postgres
```

## 5️⃣ Install Python dependencies

Install both the root and backend requirements files:

```powershell
pip install -r requirements.txt
cd "Backend"
pip install -r requirements.txt
```

## 6️⃣ Start the backend API locally

```powershell
cd "Backend"
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at: `http://localhost:8000`

**Swagger API Documentation:** `http://localhost:8000/docs`

## 7️⃣ Stop local Postgres when needed

```powershell
powershell -ExecutionPolicy Bypass -File "Backend\scripts\stop_local_pgvector_db.ps1"
```

## 8️⃣ Notes from the working setup

- Native Windows PostgreSQL + pgvector compilation requires MSVC build tools; Conda avoids this.
- Graphbit local development does not require manual DB migration scripts; schema is initialized on backend startup, and data can be reset via `seed_data.py --reset`.
</details>

