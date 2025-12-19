"""JWT authentication middleware for secure API access."""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..models.user import User

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Security scheme
security = HTTPBearer()


def create_access_token(user_id: uuid.UUID, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a new JWT access token for the given user.
    
    Args:
        user_id: The user's UUID
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT token as string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> uuid.UUID:
    """
    Verify a JWT token and extract the user ID.
    
    Args:
        token: JWT token string
        
    Returns:
        User UUID
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        
        if user_id_str is None:
            raise credentials_exception
            
        user_id = uuid.UUID(user_id_str)
        return user_id
        
    except JWTError:
        raise credentials_exception
    except ValueError:
        raise credentials_exception


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency for FastAPI endpoints to get the current authenticated user.
    
    Args:
        credentials: HTTP Bearer token from request
        db: Database session
        
    Returns:
        Current authenticated User
        
    Raises:
        HTTPException: If user not found or token invalid
    """
    token = credentials.credentials
    user_id = verify_token(token)
    
    # Query user from database
    from sqlalchemy import select
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication - returns None if no token provided.
    
    Args:
        credentials: Optional HTTP Bearer token
        db: Database session
        
    Returns:
        User if authenticated, None otherwise
    """
    if credentials is None:
        return None
        
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None