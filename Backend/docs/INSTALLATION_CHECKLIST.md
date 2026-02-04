# Installation & Testing Checklist

## 📋 Pre-Installation Checklist

- [ ] **Python 3.9+** installed
- [ ] **PostgreSQL** installed or Docker available
- [ ] **Redis** installed or Docker available  
- [ ] **Node.js & npm/bun** installed (for frontend)
- [ ] **Git** repository cloned
- [ ] **Code editor** (VS Code recommended) ready

---

## 🔧 Backend Installation

### Step 1: Environment Setup
- [ ] Navigate to Backend directory: `cd Backend`
- [ ] Create virtual environment: `python -m venv venv`
- [ ] Activate virtual environment:
  - Windows: `.\venv\Scripts\activate`
  - Linux/Mac: `source venv/bin/activate`
- [ ] Verify Python version: `python --version` (should be 3.9+)

### Step 2: Install Dependencies
- [ ] Install requirements: `pip install -r requirements.txt`
- [ ] Verify installation: `pip list | grep fastapi`
- [ ] Check for errors in installation
- [ ] Confirm these packages installed:
  - [ ] `fastapi==0.115.0`
  - [ ] `sqlalchemy[asyncio]==2.0.34`
  - [ ] `python-jose[cryptography]==3.3.0`
  - [ ] `passlib[bcrypt]==1.7.4`
  - [ ] `python-multipart==0.0.9`

### Step 3: Environment Variables
- [ ] Create `.env` file in Backend directory
- [ ] Generate SECRET_KEY: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- [ ] Add to `.env`:
  ```bash
  SECRET_KEY=<generated-key-here>
  ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=60
  DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/nocodeml
  CELERY_BROKER_URL=redis://localhost:6379/0
  CELERY_RESULT_BACKEND=redis://localhost:6379/0
  ```
- [ ] Verify `.env` file is in `.gitignore`
- [ ] Check all required variables are set

### Step 4: Database Setup
- [ ] Start PostgreSQL:
  - Docker: `docker-compose up -d postgres`
  - Local: Ensure PostgreSQL service is running
- [ ] Verify PostgreSQL is running: `docker ps` or check service status
- [ ] Test connection: `psql -U postgres -h localhost` (if installed locally)
- [ ] Database will be created automatically on first run

### Step 5: Redis Setup (for Celery)
- [ ] Start Redis:
  - Docker: `docker-compose up -d redis`
  - Local: Ensure Redis service is running
- [ ] Verify Redis is running: `docker ps` or `redis-cli ping`

### Step 6: Start Backend
- [ ] Run: `uvicorn app.main:app --reload --port 8000`
- [ ] Check for startup messages:
  - [ ] "Database tables created/verified" ✓
  - [ ] "Application startup complete" ✓
- [ ] Verify no errors in console
- [ ] Check server is running: `http://localhost:8000`
- [ ] Check health endpoint: `http://localhost:8000/health`
- [ ] Check API docs: `http://localhost:8000/docs`

---

## 🎨 Frontend Installation

### Step 1: Navigate to Frontend
- [ ] Open new terminal
- [ ] Navigate: `cd Frontend`
- [ ] Verify `package.json` exists

### Step 2: Install Dependencies
- [ ] Run: `npm install` or `bun install`
- [ ] Wait for installation to complete
- [ ] Check for any errors or warnings
- [ ] Verify `node_modules` directory created

### Step 3: Environment Variables
- [ ] Check if `.env` exists in Frontend directory
- [ ] Add if needed:
  ```bash
  VITE_API_URL=http://localhost:8000
  ```

### Step 4: Start Frontend
- [ ] Run: `npm run dev` or `bun run dev`
- [ ] Check for compilation success
- [ ] Note the port (usually 8080 or 5173)
- [ ] Verify no errors in console

### Step 5: Access Frontend
- [ ] Open browser: `http://localhost:8080` (or the port shown)
- [ ] Verify page loads without errors
- [ ] Check browser console for errors (F12)
- [ ] Verify no CORS errors

---

## ✅ Authentication Testing

### Test 1: API Endpoints (Swagger UI)
- [ ] Visit `http://localhost:8000/docs`
- [ ] Verify Swagger UI loads
- [ ] Check these endpoints are visible:
  - [ ] `POST /api/v1/auth/register`
  - [ ] `POST /api/v1/auth/login`
  - [ ] `GET /api/v1/auth/me`
  - [ ] `POST /api/v1/auth/logout`

### Test 2: User Registration (API)
- [ ] Click `POST /api/v1/auth/register` in Swagger UI
- [ ] Click "Try it out"
- [ ] Enter test data:
  ```json
  {
    "email": "test@example.com",
    "password": "password123"
  }
  ```
- [ ] Click "Execute"
- [ ] Verify Response:
  - [ ] Status: 201 Created
  - [ ] Response includes: `id`, `email`, `is_active`, `created_at`
  - [ ] No `hashed_password` in response
- [ ] Try registering same email again
- [ ] Verify Response:
  - [ ] Status: 409 Conflict
  - [ ] Error message: "Email already registered"

### Test 3: User Login (API)
- [ ] Click `POST /api/v1/auth/login` in Swagger UI
- [ ] Click "Try it out"
- [ ] Enter credentials:
  - `username`: test@example.com (yes, it's called username)
  - `password`: password123
- [ ] Click "Execute"
- [ ] Verify Response:
  - [ ] Status: 200 OK
  - [ ] Response includes: `access_token`, `token_type: "bearer"`
- [ ] Copy the `access_token` value

### Test 4: Protected Route (API)
- [ ] Click the "Authorize" button at top of Swagger UI
- [ ] Paste token in this format: `Bearer <your-token>`
- [ ] Click "Authorize"
- [ ] Click "Close"
- [ ] Click `GET /api/v1/auth/me`
- [ ] Click "Try it out"
- [ ] Click "Execute"
- [ ] Verify Response:
  - [ ] Status: 200 OK
  - [ ] Response shows your user data
- [ ] Click "Authorize" button again
- [ ] Click "Logout"
- [ ] Try `/auth/me` again
- [ ] Verify Response:
  - [ ] Status: 401 Unauthorized

### Test 5: Password Validation (API)
- [ ] Try registering with short password:
  ```json
  {
    "email": "short@example.com",
    "password": "123"
  }
  ```
- [ ] Verify Response:
  - [ ] Status: 422 Unprocessable Entity
  - [ ] Error message mentions password length

### Test 6: Invalid Login (API)
- [ ] Try login with wrong password
- [ ] Verify Response:
  - [ ] Status: 401 Unauthorized
  - [ ] Error message: "Incorrect email or password"

### Test 7: Frontend Registration
- [ ] Open browser: `http://localhost:8080`
- [ ] Navigate to Register page
- [ ] Fill in form:
  - Email: `frontend@example.com`
  - Password: `password123`
- [ ] Submit form
- [ ] Verify:
  - [ ] Success toast/message appears
  - [ ] No errors in browser console

### Test 8: Frontend Login
- [ ] Navigate to Login page
- [ ] Enter credentials from Test 7
- [ ] Submit form
- [ ] Verify:
  - [ ] Success toast/message appears
  - [ ] Redirected to home/dashboard
  - [ ] Token stored in localStorage (check DevTools → Application → Local Storage)
  - [ ] No errors in browser console

### Test 9: Frontend Protected Route
- [ ] While logged in, navigate to a protected page
- [ ] Verify:
  - [ ] Page loads successfully
  - [ ] User data displayed (if applicable)
  - [ ] Authorization header sent (check DevTools → Network → Headers)

### Test 10: Frontend Logout
- [ ] Click logout button
- [ ] Verify:
  - [ ] Redirected to login page
  - [ ] Token removed from localStorage
  - [ ] Cannot access protected routes

### Test 11: Token Expiration
- [ ] Login and get a token
- [ ] Wait for token to expire (default: 60 minutes, or modify `ACCESS_TOKEN_EXPIRE_MINUTES` to 1 for testing)
- [ ] Try accessing protected route
- [ ] Verify:
  - [ ] 401 error
  - [ ] Redirected to login

### Test 12: CORS Verification
- [ ] Open browser DevTools (F12)
- [ ] Go to Console tab
- [ ] Login and watch for CORS errors
- [ ] Verify:
  - [ ] No CORS errors
  - [ ] Requests succeed

---

## 🔍 Database Verification

### Check Users Table
- [ ] Connect to database:
  ```bash
  psql -U postgres -h localhost -d nocodeml
  # Or using Docker:
  docker exec -it <postgres-container> psql -U postgres -d nocodeml
  ```
- [ ] List tables: `\dt`
- [ ] Verify `users` table exists
- [ ] Check schema: `\d users`
- [ ] Verify columns:
  - [ ] `id` (integer, primary key)
  - [ ] `email` (varchar, unique)
  - [ ] `hashed_password` (varchar)
  - [ ] `is_active` (boolean)
  - [ ] `is_superuser` (boolean)
  - [ ] `created_at` (timestamp)
  - [ ] `updated_at` (timestamp)
- [ ] Check users: `SELECT id, email, is_active FROM users;`
- [ ] Verify test users exist

### Verify Password Hashing
- [ ] Check a user's password: `SELECT email, hashed_password FROM users LIMIT 1;`
- [ ] Verify:
  - [ ] Password starts with `$2b$` (bcrypt)
  - [ ] Password is hashed, not plain text

---

## 🧪 Advanced Testing

### Test 13: Concurrent Requests
- [ ] Open multiple browser tabs
- [ ] Login in each tab with same user
- [ ] Verify all tabs work correctly
- [ ] Make requests from different tabs
- [ ] Verify no session conflicts

### Test 14: Invalid Token
- [ ] Get a valid token
- [ ] Modify the token slightly (change a character)
- [ ] Try accessing protected route with modified token
- [ ] Verify:
  - [ ] 401 Unauthorized
  - [ ] Error message: "Could not validate credentials"

### Test 15: Multiple Users
- [ ] Register 3 different users
- [ ] Login with each user in different browser tabs/profiles
- [ ] Verify each user gets their own data
- [ ] Verify tokens don't interfere with each other

### Test 16: Admin User (if applicable)
- [ ] Manually set a user as superuser:
  ```sql
  UPDATE users SET is_superuser = true WHERE email = 'admin@example.com';
  ```
- [ ] Login with that user
- [ ] Verify superuser status in response

### Test 17: Inactive User
- [ ] Manually deactivate a user:
  ```sql
  UPDATE users SET is_active = false WHERE email = 'test@example.com';
  ```
- [ ] Try logging in with that user
- [ ] Verify:
  - [ ] 400 Bad Request
  - [ ] Error message: "Inactive user account"

### Test 18: Rate Limiting (if implemented)
- [ ] Make multiple rapid login attempts
- [ ] Check if rate limiting is working (if configured)

---

## 📊 Performance Checks

### Response Times
- [ ] Measure `/auth/register` response time (should be < 500ms)
- [ ] Measure `/auth/login` response time (should be < 300ms)
- [ ] Measure `/auth/me` response time (should be < 100ms)
- [ ] Check database query times

### Load Testing (Optional)
- [ ] Use tool like `ab` or `wrk`:
  ```bash
  # Test login endpoint
  ab -n 100 -c 10 http://localhost:8000/api/v1/auth/login
  ```
- [ ] Check for errors or timeouts
- [ ] Monitor resource usage

---

## 🐛 Troubleshooting Checks

### If Backend Won't Start
- [ ] Check Python version: `python --version`
- [ ] Check virtual environment is activated
- [ ] Check all dependencies installed: `pip list`
- [ ] Check `.env` file exists and has SECRET_KEY
- [ ] Check PostgreSQL is running
- [ ] Check port 8000 is not in use: `netstat -ano | findstr :8000`
- [ ] Check for errors in console output

### If Database Connection Fails
- [ ] Check PostgreSQL is running: `docker ps` or service status
- [ ] Check DATABASE_URL in `.env`
- [ ] Check database credentials
- [ ] Try connecting manually: `psql -U postgres -h localhost`
- [ ] Check firewall/network settings

### If Frontend Won't Connect
- [ ] Check backend is running on port 8000
- [ ] Check VITE_API_URL in Frontend `.env`
- [ ] Check CORS settings in `app/main.py`
- [ ] Check browser console for errors
- [ ] Try opening `http://localhost:8000/docs` directly

### If Authentication Fails
- [ ] Check SECRET_KEY is set correctly
- [ ] Check token format in Authorization header
- [ ] Check token hasn't expired
- [ ] Check user exists in database
- [ ] Check user is active: `SELECT is_active FROM users WHERE email='...';`
- [ ] Check logs for detailed error messages

---

## 📝 Final Verification

### Code Quality
- [ ] No syntax errors in Python code
- [ ] No import errors
- [ ] All type hints are correct
- [ ] No linting errors (if using linter)
- [ ] All docstrings present

### Documentation
- [ ] README.md is up to date
- [ ] AUTH_SYSTEM.md reviewed
- [ ] AUTH_IMPLEMENTATION.md reviewed
- [ ] QUICK_REFERENCE_AUTH.md reviewed
- [ ] All inline comments make sense

### Security
- [ ] SECRET_KEY is not in version control
- [ ] `.env` file is in `.gitignore`
- [ ] Passwords are hashed, not plain text
- [ ] JWT tokens have expiration
- [ ] CORS is configured correctly
- [ ] No sensitive data in logs

### Production Readiness (if deploying)
- [ ] Use strong SECRET_KEY (32+ random characters)
- [ ] Enable HTTPS
- [ ] Set proper CORS origins (no wildcards)
- [ ] Configure environment variables on server
- [ ] Set up database backups
- [ ] Configure logging
- [ ] Set up monitoring
- [ ] Add rate limiting
- [ ] Add error tracking (e.g., Sentry)

---

## ✅ Sign-off

### Developer Sign-off
- [ ] All tests passed
- [ ] No errors in console
- [ ] Code reviewed
- [ ] Documentation complete
- [ ] Ready for code review

**Developer:** ________________  
**Date:** ________________

### QA Sign-off
- [ ] All test cases passed
- [ ] Edge cases tested
- [ ] Performance acceptable
- [ ] Security verified
- [ ] Ready for staging/production

**QA Engineer:** ________________  
**Date:** ________________

---

## 📞 Support Contacts

- **Technical Issues:** Check `AUTH_IMPLEMENTATION.md` → Troubleshooting
- **Setup Questions:** Review `AUTH_SYSTEM.md`
- **Quick Help:** Check `QUICK_REFERENCE_AUTH.md`

---

**Checklist Version:** 1.0.0  
**Last Updated:** October 3, 2025  
**Status:** Complete ✅
