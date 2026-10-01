"""
FastAPI dependency injection providers.

All shared resources (DB sessions, settings, etc.) are provided here
so individual endpoints declare what they need via function arguments.
This makes endpoints trivially testable - inject test doubles in tests.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from netmind.core.config import Settings, get_settings
from netmind.db.session import get_db_session

# ─── Type aliases for endpoint signatures ─────────────────────────────────────
# Using Annotated + Depends keeps endpoint signatures clean:
#   async def my_endpoint(db: DbSession, settings: AppSettings) -> ...

DbSession = Annotated[AsyncSession, Depends(get_db_session)]
AppSettings = Annotated[Settings, Depends(get_settings)]

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy import select
from netmind.core.security import SECRET_KEY, ALGORITHM
from netmind.models.base import User
from netmind.schemas.user import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db_session),
    token: str = Depends(oauth2_scheme)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.email == token_data.email))
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role.upper() != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Requires Admin privileges"
        )
    return current_user

async def get_network_engineer_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role.upper() not in ["ADMIN", "NETWORK ENGINEER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Requires Network Engineer privileges"
        )
    return current_user

async def get_ml_engineer_user(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role.upper() not in ["ADMIN", "ML ENGINEER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Requires ML Engineer privileges"
        )
    return current_user

# Viewer is essentially get_current_active_user since all roles have at least Viewer access
async def get_current_operator_user(current_user: User = Depends(get_current_active_user)) -> User:
    # Retaining for backwards compatibility until fully replaced
    if current_user.role.upper() not in ["OPERATOR", "ENGINEER", "ADMIN", "NETWORK ENGINEER", "ML ENGINEER"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="The user doesn't have enough privileges"
        )
    return current_user
