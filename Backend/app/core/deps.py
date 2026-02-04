"""Authentication dependencies for protecting routes.

This module provides FastAPI dependencies that:
- Extract and validate JWT tokens from Authorization headers
- Fetch the current user from the database
- Ensure the user is active
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

# OAuth2PasswordBearer extracts the token from "Authorization: Bearer <token>" header
# tokenUrl is where clients get tokens (our login endpoint)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token.
    
    This dependency:
    1. Extracts the JWT token from the Authorization header
    2. Decodes and validates the token
    3. Fetches the user from the database
    4. Raises 401 if token is invalid or user not found
    
    Args:
        token: JWT token extracted from Authorization header
        db: Database session
        
    Returns:
        The authenticated User object
        
    Raises:
        HTTPException: 401 if credentials are invalid
        
    Example usage in a route:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_user)):
            return {"user_id": user.id}
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Decode the JWT token
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    
    # Extract user_id from token payload
    user_id: Optional[int] = payload.get("user_id")
    if user_id is None:
        raise credentials_exception
    
    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get the current user and verify they are active.
    
    This dependency builds on get_current_user by adding an additional
    check that the user's account is active (not disabled).
    
    Args:
        current_user: User object from get_current_user dependency
        
    Returns:
        The authenticated and active User object
        
    Raises:
        HTTPException: 400 if user account is inactive
        
    Example usage in a route:
        @router.get("/protected")
        async def protected_route(user: User = Depends(get_current_active_user)):
            # user is guaranteed to be authenticated AND active
            return {"user_id": user.id}
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    return current_user
