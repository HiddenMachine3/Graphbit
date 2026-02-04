# Custom JWT Authentication System

## Overview

This application uses a **custom, lightweight JWT-based authentication system** built from scratch with FastAPI. It replaces the previous `fastapi-users` dependency with a minimal, maintainable solution.

## Architecture

### Core Components

```
Backend/app/
├── core/
│   ├── config.py      # Settings (SECRET_KEY, ALGORITHM, token expiration)
│   ├── security.py    # Password hashing & JWT token functions
│   └── deps.py        # Authentication dependencies
├── api/
│   └── auth.py        # Authentication endpoints
├── models/
│   └── __init__.py    # User model (SQLAlchemy)
└── schemas/
    └── __init__.py    # Pydantic schemas (validation)
```

## Authentication Flow

### 1. Registration
```
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}

Response (201):
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-10-03T10:00:00Z",
  "updated_at": null
}
```

**Process:**
1. Validates email format and password length (min 8 chars)
2. Checks if email already exists (returns 409 if duplicate)
3. Hashes password using bcrypt
4. Creates user in database
5. Returns user data (without password)

### 2. Login
```
POST /api/v1/auth/login
Content-Type: multipart/form-data

username=user@example.com
password=securepassword123

Response (200):
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Process:**
1. Validates credentials against database
2. Verifies password using bcrypt
3. Checks user is active
4. Creates JWT token with user_id and email
5. Returns token (expires in 60 minutes by default)

### 3. Protected Routes
```
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response (200):
{
  "id": 1,
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2025-10-03T10:00:00Z",
  "updated_at": null
}
```

**Process:**
1. Extracts token from Authorization header
2. Decodes and validates JWT signature
3. Fetches user from database using token's user_id
4. Returns user data

### 4. Logout
```
POST /api/v1/auth/logout
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

Response (200):
{
  "message": "Successfully logged out"
}
```

**Note:** JWT tokens are stateless. Actual logout is handled client-side by deleting the token from localStorage.

## Security Features

### Password Security
- **Hashing:** bcrypt algorithm with automatic salt generation
- **Validation:** Minimum 8 characters required
- **Storage:** Only hashed passwords stored in database
- **Comparison:** Constant-time comparison to prevent timing attacks

### JWT Token Security
- **Signing:** HS256 algorithm with SECRET_KEY
- **Expiration:** 60-minute default (configurable)
- **Payload:** Contains user_id and email (no sensitive data)
- **Validation:** Signature and expiration checked on every request

### HTTP Security
- **401 Unauthorized:** Invalid/missing/expired tokens
- **409 Conflict:** Email already registered
- **400 Bad Request:** Inactive user accounts
- **422 Unprocessable Entity:** Validation errors

## Database Schema

### User Model
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    is_superuser BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_email ON users(email);
```

## Configuration

### Environment Variables (.env)
```bash
# Required
SECRET_KEY=your-secret-key-here-min-32-chars
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Optional (with defaults)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### Generating a SECRET_KEY
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

## Usage Examples

### Protecting a Route (Backend)
```python
from fastapi import APIRouter, Depends
from app.core.deps import get_current_active_user
from app.models import User

router = APIRouter()

@router.get("/protected-endpoint")
async def protected_route(
    current_user: User = Depends(get_current_active_user)
):
    """This endpoint requires authentication."""
    return {
        "message": f"Hello {current_user.email}",
        "user_id": current_user.id
    }
```

### Frontend Integration (React/TypeScript)
```typescript
// Login
const response = await authAPI.login(email, password);
localStorage.setItem('auth_token', response.access_token);

// Make authenticated request
const user = await authAPI.getCurrentUser();

// Logout
localStorage.removeItem('auth_token');
await authAPI.logout(); // Optional server-side call
```

## API Endpoints Summary

| Method | Endpoint | Auth Required | Description |
|--------|----------|---------------|-------------|
| POST | `/api/v1/auth/register` | No | Create new user account |
| POST | `/api/v1/auth/login` | No | Login and receive JWT token |
| GET | `/api/v1/auth/me` | Yes | Get current user info |
| POST | `/api/v1/auth/logout` | Yes | Logout (optional) |

## Dependencies

### Python Packages
```
fastapi==0.115.0
sqlalchemy[asyncio]==2.0.34
pydantic==2.9.2
pydantic-settings==2.3.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
```

### Why These Dependencies?
- **python-jose:** JWT encoding/decoding with cryptography support
- **passlib:** Password hashing with bcrypt
- **python-multipart:** Required for OAuth2PasswordRequestForm (form data login)
- **pydantic-settings:** Type-safe configuration management

## Error Handling

### Common Error Responses

**Invalid Credentials (401)**
```json
{
  "detail": "Incorrect email or password"
}
```

**Email Already Exists (409)**
```json
{
  "detail": "Email already registered"
}
```

**Password Too Short (422)**
```json
{
  "detail": [
    {
      "loc": ["body", "password"],
      "msg": "Password must be at least 8 characters long",
      "type": "value_error"
    }
  ]
}
```

**Invalid Token (401)**
```json
{
  "detail": "Could not validate credentials"
}
```

**Inactive Account (400)**
```json
{
  "detail": "Inactive user account"
}
```

## Migration from fastapi-users

### Changes Made
1. ✅ Removed `fastapi-users` and `fastapi-users-db-sqlalchemy` dependencies
2. ✅ Removed `is_verified` field from User model
3. ✅ Created custom `security.py` for password/JWT functions
4. ✅ Created custom `deps.py` for authentication dependencies
5. ✅ Created custom `auth.py` router with register/login/me endpoints
6. ✅ Updated Pydantic schemas with custom validation
7. ✅ Updated frontend API endpoints (`/auth/jwt/login` → `/auth/login`, `/users/me` → `/auth/me`)

### Frontend Compatibility
✅ **No changes required** - The frontend code works without modification because:
- Login still accepts form data with `username` (email) and `password`
- Token response format is identical: `{"access_token": "...", "token_type": "bearer"}`
- User response format is compatible (just removed `is_verified` field)
- Authorization header format unchanged: `Bearer <token>`

## Testing

### Manual Testing with cURL

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password123"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -F "username=test@example.com" \
  -F "password=password123"
```

**Get Current User:**
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### Testing with Frontend
1. Start backend: `cd Backend && uvicorn app.main:app --reload`
2. Start frontend: `cd Frontend && npm run dev`
3. Navigate to `http://localhost:8080/register`
4. Create account and login
5. Access protected routes

## Troubleshooting

### "Could not validate credentials" Error
- Check token hasn't expired (default: 60 minutes)
- Verify SECRET_KEY matches between token creation and validation
- Ensure Authorization header format: `Bearer <token>` (with space)

### "Email already registered" Error
- Email must be unique
- Check database for existing user: `SELECT * FROM users WHERE email='...'`

### Token Not Working After Server Restart
- If SECRET_KEY changed, old tokens are invalid
- Keep SECRET_KEY consistent in .env file
- Frontend should handle 401 errors by redirecting to login

### Database Connection Errors
- Verify DATABASE_URL format: `postgresql+asyncpg://user:pass@host:port/dbname`
- Check PostgreSQL is running
- Verify credentials are correct

## Best Practices

### Security
- ✅ Never commit SECRET_KEY to version control
- ✅ Use environment variables for sensitive config
- ✅ Use HTTPS in production
- ✅ Implement rate limiting on login endpoint
- ✅ Consider adding refresh tokens for long-lived sessions
- ✅ Log authentication attempts for security monitoring

### Code Quality
- ✅ Use type hints throughout
- ✅ Add comprehensive docstrings
- ✅ Validate all input with Pydantic
- ✅ Handle errors gracefully with proper status codes
- ✅ Use dependency injection for testability

## Future Enhancements

Potential features to add:
- [ ] Refresh token rotation
- [ ] Token blacklisting for logout
- [ ] Email verification
- [ ] Password reset flow
- [ ] Two-factor authentication (2FA)
- [ ] Rate limiting on auth endpoints
- [ ] Account lockout after failed attempts
- [ ] OAuth2 social login (Google, GitHub)
- [ ] API key authentication for service accounts

## Support

For issues or questions:
1. Check logs: `uvicorn app.main:app --log-level debug`
2. Verify configuration in `.env`
3. Test endpoints with cURL or Postman
4. Review this documentation

---

**Version:** 2.0.0  
**Last Updated:** October 3, 2025  
**Author:** NoCodeML Team
