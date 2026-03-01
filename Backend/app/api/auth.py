"""Authentication routes for user registration and login.

Provides endpoints:
- POST /auth/register - Create new user account
- POST /auth/login - Authenticate and receive JWT token  
- GET /auth/me - Get current user information (protected)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import hash_password, verify_password, create_access_token
from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse, Token, LoginRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> User:
    """Register a new user account.
    
    Creates a new user with:
    - Unique email address
    - Securely hashed password
    - Default active status
    
    Args:
        user_data: User registration data (email, password)
        db: Database session
        
    Returns:
        The created user object (without password)
        
    Raises:
        HTTPException 409: If email already exists
        HTTPException 422: If validation fails (e.g., password too short)
    """
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        logger.warning("Registration failed: email already exists email=%s", user_data.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create new user with hashed password
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        is_active=True,
        is_superuser=False,
        is_verified=False  # User starts unverified, can be verified later
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    logger.info("User registered: email=%s", user_data.email)
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Authenticate user and return JWT access token.
    
    Accepts form data with:
    - username: Actually the email address (OAuth2 spec requires "username" field)
    - password: User's password
    
    Args:
        form_data: OAuth2 form data (username=email, password)
        db: Database session
        
    Returns:
        Dictionary with access_token and token_type
        
    Raises:
        HTTPException 401: If credentials are invalid
        
    Note:
        The frontend sends form data (not JSON) to this endpoint.
        This is compatible with OAuth2 password flow.
    """
    # Find user by email (form_data.username contains the email)
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()
    
    # Verify user exists and password is correct
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Login failed: invalid credentials email=%s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Create JWT token with user information
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id}
    )
    
    logger.info("Login success: email=%s user_id=%s", user.email, user.id)
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """Get current authenticated user's information.
    
    This is a protected endpoint that requires a valid JWT token
    in the Authorization header: "Bearer <token>"
    
    Args:
        current_user: Injected by get_current_active_user dependency
        
    Returns:
        The current user's information (without password)
        
    Raises:
        HTTPException 401: If token is invalid or missing
    """
    return current_user


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Logout endpoint (optional).
    
    Since JWT tokens are stateless, logout is handled client-side
    by deleting the token from localStorage.
    
    This endpoint exists for:
    - API consistency
    - Future token blacklisting if needed
    - Audit logging
    
    Args:
        current_user: Verified the token is valid
        
    Returns:
        Success message
    """
    return {"message": "Successfully logged out"}
