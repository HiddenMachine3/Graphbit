# Graphbit Setup Instructions

This guide will walk you through setting up the Graphbit development environment on your local machine (Windows).

## Prerequisites

### Python
- **Required version:** Python 3.11+
- Verify your installation:
  ```powershell
  python --version
  ```

### PostgreSQL
- **Required version:** PostgreSQL 18
- Download and install from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
- Make sure the PostgreSQL service is running before starting the backend
- Default credentials used by this project (see `backend/.env`):
  - **User:** `postgres`
  - **Password:** `admin`
  - **Database:** `postgres`
  - **Port:** `5432`

> **⚠ Important (PostgreSQL 18 on Windows):** PostgreSQL 18 sets a system-wide `CURL_CA_BUNDLE` environment variable pointing to a certificate file that may not exist. This causes SSL errors in Python. You **must** clear it in every terminal before running the backend:
> ```powershell
> $env:CURL_CA_BUNDLE = ""
> ```

### Node.js & npm
- **Required version:** Node.js 18+ (includes npm)
- Verify installation:
  ```powershell
  node --version
  npm --version
  ```

---

## Installation Steps

### 1. Clone the Repository

```powershell
git clone https://github.com/HiddenMachine3/Graphbit.git
cd Graphbit
```

### 2. Install Python Dependencies

Install both the root-level and backend requirements:

```powershell
pip install -r requirements.txt
cd backend
pip install -r requirements.txt
cd ..
```

> **Note:** The backend requires PyTorch for local LLM topic extraction. If `torch` fails to install, install the CPU-only build manually:
> ```powershell
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> ```

### 3. Install Frontend Dependencies

```powershell
cd frontend
npm install
cd ..
```

### 4. (Optional) Seed the Database

Populate the database with sample knowledge graphs, nodes, edges, and questions for testing:

```powershell
cd backend
python seed_data.py
cd ..
```

Skip this if you prefer to start with an empty database — tables are auto-created on first backend startup.

### 5. Running the Tests

```powershell
python -m pytest tests/ -v --tb=short
```

---

## Running the Application

You need **two terminal windows** — one for the backend, one for the frontend.

### Terminal 1: Start the Backend API

```powershell
cd backend
$env:CURL_CA_BUNDLE = ""
python -m uvicorn app.main:app --reload --port 8000
```

- API available at: **http://localhost:8000**
- Swagger docs at: **http://localhost:8000/docs**

### Terminal 2: Start the Frontend

```powershell
cd frontend
npm run dev
```

- Frontend available at: **http://localhost:3000**

---

## Chrome Extension (Optional)

The `extension/` folder contains a Chrome Manifest V3 extension that lets you ingest YouTube video transcripts directly from YouTube.

### Load the Extension

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (toggle in the top-right)
3. Click **Load unpacked** and select the `extension/` folder
4. Navigate to any YouTube video — click the extension icon to ingest the transcript into your knowledge graph

> The extension calls the backend at `http://localhost:8000`, so make sure the backend is running.

---

## Environment Configuration

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://postgres:admin@localhost:5432/postgres` | PostgreSQL connection string |
| `SECRET_KEY` | *(preset)* | JWT signing key — change for production |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis URL for Celery (optional) |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/0` | Redis URL for Celery results (optional) |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Backend API URL used by the frontend |

### Topic Extraction Model

The ingestion pipeline uses a local Hugging Face model for extracting topics from YouTube transcripts. By default it uses `Qwen/Qwen2.5-7B-Instruct`. You can override this with:

```powershell
$env:HF_TOPIC_MODEL = "Qwen/Qwen2.5-7B-Instruct"
```

> **Note:** The model runs on CPU by default (no CUDA required). First run will download the model (~14 GB). Requires sufficient RAM.

---

## Troubleshooting

### `UnicodeEncodeError` on backend startup
- This happens when the Windows terminal can't render certain characters. Set the console to UTF-8:
  ```powershell
  [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
  ```

### Backend won't start — `CURL_CA_BUNDLE` / SSL errors
- PostgreSQL 18 sets `CURL_CA_BUNDLE` to a path that may not exist. **Always** clear it before starting the backend:
  ```powershell
  $env:CURL_CA_BUNDLE = ""
  ```

### Backend won't start — port 8000 already in use
- Find and kill stale processes on port 8000:
  ```powershell
  netstat -ano | Select-String ":8000.*LISTENING"
  # Then kill the PID shown in the last column:
  taskkill /F /PID <PID>
  ```

### Frontend won't start
- Ensure npm dependencies are installed: `npm install`
- Clear cache and reinstall if issues persist:
  ```powershell
  Remove-Item -Recurse -Force node_modules
  npm install
  ```

### Database connection errors
- Ensure PostgreSQL is running:
  ```powershell
  Get-Service postgresql* | Select-Object Name, Status
  ```
- Verify credentials in `backend/.env` match your PostgreSQL setup

---

## Project Structure

```
Graphbit/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/          # API route handlers (graph, projects, auth)
│   │   ├── core/         # Config, settings
│   │   ├── db/           # Database session
│   │   ├── domain/       # Business logic
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Topic extraction, video transcripts
│   ├── seed_data.py      # Database seeder
│   ├── requirements.txt
│   └── .env              # Backend environment config
├── frontend/             # Next.js 14 frontend
│   ├── app/              # App router pages (graph, etc.)
│   ├── components/       # React components (KnowledgeGraphView, etc.)
│   ├── lib/              # API client, types
│   └── .env.local        # Frontend environment config
├── extension/            # Chrome extension (Manifest V3)
│   ├── manifest.json
│   ├── popup.html/js/css
│   ├── content.js
│   └── background.js
├── tests/                # Pytest tests
├── requirements.txt      # Root-level Python deps
└── SETUP.md              # This file
```

---

## Next Steps

Once both servers are running, visit **http://localhost:3000** to use Graphbit. The frontend communicates with the backend API at `http://localhost:8000/api/v1`.
