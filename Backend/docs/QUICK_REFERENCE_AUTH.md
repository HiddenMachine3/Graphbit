# JWT Authentication Quick Reference

## 🚀 Quick Start

```powershell
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set SECRET_KEY in .env
SECRET_KEY=your-secret-key-here

# 3. Start services
docker-compose up -d postgres redis
uvicorn app.main:app --reload
```

## 📡 API Endpoints

| Method | Endpoint | Auth? | Description |
|--------|----------|-------|-------------|
| POST | `/api/v1/auth/register` | No | Create new user |
| POST | `/api/v1/auth/login` | No | Login (get JWT) |
| GET | `/api/v1/auth/me` | Yes | Get current user |
| POST | `/api/v1/auth/logout` | Yes | Logout (optional) |

## 🔐 Authentication Flow

```
1. Register → POST /auth/register → {id, email, ...}
2. Login → POST /auth/login → {access_token, token_type}
3. Store token → localStorage.setItem('auth_token', token)
4. Use token → Authorization: Bearer <token>
5. Access protected routes → GET /auth/me
```

## 💻 Code Examples

### Register User
```python
from app.schemas import UserCreate

user_data = UserCreate(
    email="user@example.com",
    password="securepass123"  # Min 8 chars
)
```

### Protect a Route
```python
from fastapi import APIRouter, Depends
from app.core.deps import get_current_active_user
from app.models import User

router = APIRouter()

@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_active_user)
):
    return {"user_id": current_user.id}
```

### Create JWT Token
```python
from app.core.security import create_access_token

token = create_access_token(
    data={"sub": user.email, "user_id": user.id}
)
```

### Verify Password
```python
from app.core.security import verify_password

is_valid = verify_password(plain_password, hashed_password)
```

## 🧪 Testing with cURL

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=test@example.com" \
  -F "password=password123"
```

### Get Current User
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

## 🎯 Frontend Integration

### Login Function
```typescript
const login = async (email: string, password: string) => {
  const formData = new FormData();
  formData.append('username', email);
  formData.append('password', password);
  
  const response = await api.post('/api/v1/auth/login', formData);
  localStorage.setItem('auth_token', response.access_token);
};
```

### Axios Interceptor
```javascript
api.interceptors.request.use(config => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
```

### Generate SECRET_KEY
```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 📊 Database Schema

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);
```

## 🔧 Common Tasks

### Make User Superuser
```sql
UPDATE users SET is_superuser = true WHERE email = 'admin@example.com';
```

### Deactivate User
```sql
UPDATE users SET is_active = false WHERE email = 'user@example.com';
```

### Check Active Users
```sql
SELECT id, email, created_at FROM users WHERE is_active = true;
```

## ❌ Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 401 | Unauthorized | Check token is valid and not expired |
| 409 | Conflict | Email already registered |
| 422 | Validation Error | Check password length (min 8 chars) |
| 400 | Bad Request | Account may be inactive |

## 🐛 Troubleshooting

### Token Not Working
```python
# Decode token to inspect
from app.core.security import decode_access_token
payload = decode_access_token(token)
print(payload)  # Check exp, user_id, etc.
```

### Check Token Expiration
```python
from datetime import datetime
exp = payload.get('exp')
is_expired = datetime.fromtimestamp(exp) < datetime.now()
```

### Verify Password Hash
```python
from app.core.security import verify_password
is_match = verify_password("password123", user.hashed_password)
```

## 📁 File Structure

```
app/
├── core/
│   ├── security.py      # Password & JWT functions
│   ├── deps.py          # Auth dependencies
│   └── config.py        # Settings
├── api/
│   └── auth.py          # Auth endpoints
├── models/
│   └── __init__.py      # User model
└── schemas/
    └── __init__.py      # Pydantic schemas
```

## 🔒 Security Best Practices

- ✅ Never commit SECRET_KEY to git
- ✅ Use HTTPS in production
- ✅ Set strong SECRET_KEY (32+ random chars)
- ✅ Implement rate limiting on auth endpoints
- ✅ Log authentication attempts
- ✅ Use secure password requirements
- ✅ Set reasonable token expiration
- ✅ Validate all user input

## 📚 Key Functions

### security.py
```python
hash_password(password: str) -> str
verify_password(plain: str, hashed: str) -> bool
create_access_token(data: dict) -> str
decode_access_token(token: str) -> dict | None
```

### deps.py
```python
async def get_current_user(token, db) -> User
async def get_current_active_user(current_user) -> User
```

## 🎨 Response Schemas

### Token Response
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### User Response
```json
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-10-03T10:00:00Z",
  "updated_at": null
}
```

## 🚨 Quick Fixes

### "Could not validate credentials"
→ Token expired or invalid. Login again.

### "Email already registered"
→ Use different email or login with existing account.

### "Password must be at least 8 characters"
→ Use longer password.

### CORS errors
→ Check `allow_origins` in `main.py`.

### Database connection error
→ Verify `DATABASE_URL` in `.env`.

## 🔗 Resources

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **Full Docs:** `AUTH_SYSTEM.md`
- **Implementation:** `AUTH_IMPLEMENTATION.md`
- **Migration:** `MIGRATION_GUIDE.md`

---

**Quick Reference v2.0.0** | NoCodeML Team | October 2025
