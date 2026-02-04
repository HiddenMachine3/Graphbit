# Quick Start Guide - Custom JWT Authentication

## 🎯 What's New?

This project now uses **custom JWT authentication** instead of fastapi-users. The system is simpler, lighter, and easier to understand!

## 📚 Documentation

**New to authentication?** Start here: [`AUTH_INDEX.md`](AUTH_INDEX.md) - Central documentation hub

**Quick reference:** [`QUICK_REFERENCE_AUTH.md`](QUICK_REFERENCE_AUTH.md)

**Full setup guide:** [`INSTALLATION_CHECKLIST.md`](INSTALLATION_CHECKLIST.md)

---

## 🚀 Getting Started in 3 Steps

### Step 1: Setup Environment
```powershell
cd c:\V2_NoCodeML\Backend

# Install dependencies
pip install -r requirements.txt

# Create .env file
# Add: SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_urlsafe(32))">
```

### Step 2: Start the Services
```powershell
# Start database and redis
docker-compose up -d postgres redis

# Start the backend
uvicorn app.main:app --reload --port 8000
```

Wait for startup message: "Database tables created/verified ✓"

### Step 3: Test Authentication
Open your browser to `http://localhost:8000/docs` to see the Swagger UI.

---

## 🧪 Quick Test

### Option 1: Using Swagger UI (Browser) - Recommended
1. Go to `http://localhost:8000/docs`
2. Click on `POST /api/v1/auth/register`
3. Click "Try it out"
4. Enter:
   ```json
   {
     "email": "test@example.com",
     "password": "password123"
   }
   ```
5. Click "Execute"
6. You should get a 201 response with user data

7. Now try login: `POST /api/v1/auth/login` (Note: endpoint changed!)
8. Click "Try it out"
9. Enter form data:
   - username: `test@example.com`
   - password: `password123`
10. Copy the `access_token` from response

11. Click the "Authorize" button at the top
12. Enter: `Bearer YOUR_TOKEN_HERE`
13. Click "Authorize"

14. Now try `GET /api/v1/users/me` - it should return your user data!

### Option 2: Using PowerShell
```powershell
# Register
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/register" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"email":"test@example.com","password":"password123"}'

$response.Content

# Login
$loginResponse = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/auth/jwt/login" `
  -Method POST `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=test@example.com&password=password123"

$token = ($loginResponse.Content | ConvertFrom-Json).access_token

# Get current user
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/users/me" `
  -Headers @{"Authorization"="Bearer $token"}
```

---

## 📋 Checklist

- [ ] Docker and Docker Compose installed
- [ ] `.env` file exists in Backend directory
- [ ] Services started: `docker-compose up -d`
- [ ] Database initialized: `docker-compose exec fastapi_app python -m app.db.init_db`
- [ ] Can access Swagger UI at http://localhost:8000/docs
- [ ] Successfully registered a user
- [ ] Successfully logged in and got JWT token
- [ ] Successfully accessed protected `/users/me` endpoint

---

## 🔗 Connect Your Frontend

Your frontend should make requests to:
- **Register:** `POST http://localhost:8000/api/v1/auth/register`
- **Login:** `POST http://localhost:8000/api/v1/auth/jwt/login`
- **Get User:** `GET http://localhost:8000/api/v1/users/me`

Update your frontend API base URL to `http://localhost:8000/api/v1`

---

## 🐛 Common Issues

### "Connection refused" error
**Fix:** Make sure services are running: `docker-compose ps`

### "Table doesn't exist" error  
**Fix:** Run init script: `docker-compose exec fastapi_app python -m app.db.init_db`

### CORS errors in browser
**Fix:** Check that your frontend port (probably 5173 or 3000) is in the CORS origins list in `app/main.py`

### Can't connect to database
**Fix:** Check PostgreSQL is healthy: `docker-compose logs postgres`

---

## 📚 Next Steps

1. Read the full documentation: `AUTH_IMPLEMENTATION.md`
2. Test with your frontend application
3. Add more protected routes using the `current_active_user` dependency
4. Consider adding email verification or password reset if needed

---

## 🎯 Success Criteria

You're all set when:
- ✓ You can register a new user
- ✓ You can login and receive a JWT token
- ✓ You can access `/users/me` with the token
- ✓ Your frontend can connect and authenticate users

**Happy coding! 🚀**
