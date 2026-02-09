"""Pydantic schemas for request/response validation.

These schemas define the shape of data coming in and going out of the API.
They provide automatic validation and documentation.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict


class UserCreate(BaseModel):
    """Schema for user registration request.
    
    Validates:
    - Email is valid format
    - Password meets minimum requirements
    """
    email: EmailStr
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets minimum requirements.
        
        Requirements:
        - At least 8 characters long
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserResponse(BaseModel):
    """Schema for user data in responses.
    
    Note: Never includes the hashed_password field for security!
    """
    id: int
    email: str
    is_active: bool
    is_superuser: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    """Schema for login request.
    
    Accepts email and password for authentication.
    """
    email: EmailStr
    password: str


class Token(BaseModel):
    """Schema for token response.
    
    Returned after successful login.
    """
    access_token: str
    token_type: str = "bearer"
