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
