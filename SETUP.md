# Graphbit Setup Instructions

This guide will walk you through setting up the Graphbit development environment on your local machine.

## Prerequisites

### Python
- **Required version:** Python 3.12 or higher
- Verify your installation:
  ```powershell
  python --version
  ```

### PostgreSQL
- **Required version:** PostgreSQL 18
- Download and install from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
- Make sure PostgreSQL is running on your system before starting the backend

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
- Ensure PostgreSQL 18 is installed and running
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
