"""
Client Mode Authentication Service.

In client mode (local installation), we automatically create and manage
a single local user that is always authenticated. This simplifies the
user experience for personal installations.
"""

import logging
import secrets
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User
from ..models.database import async_session_maker
from ..config import settings
from ..utils.auth import create_access_token

logger = logging.getLogger(__name__)

# Local user constants
LOCAL_USER_EMAIL = "local@localhost"
LOCAL_USER_ID = "local-client-user"


async def get_or_create_local_user(db: AsyncSession) -> User:
    """
    Get or create the local user for client mode.

    This user is automatically created on first startup and used for all
    operations in client mode. The client_secret is set to MED_CLIENT_SECRET
    for encryption compatibility.
    """
    # Check if local user exists
    result = await db.execute(select(User).where(User.email == LOCAL_USER_EMAIL))
    user = result.scalar_one_or_none()

    if user:
        logger.debug(f"[CLIENT_AUTH] Local user found: {user.email}")
        return user

    # Create local user with MED credentials
    logger.info("[CLIENT_AUTH] Creating local user for client mode...")

    user = User(
        id=LOCAL_USER_ID,
        email=LOCAL_USER_EMAIL,
        hashed_password="",  # No password needed in client mode
        client_id=settings.MED_CLIENT_ID or f"cli_{secrets.token_urlsafe(32)}",
        client_secret=settings.MED_CLIENT_SECRET or secrets.token_urlsafe(64),
        is_active=True,
        is_admin=True,  # Local user has full access
        email_verified=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(f"[CLIENT_AUTH] Local user created: {user.email}")
    return user


async def initialize_client_auth() -> str | None:
    """
    Initialize client mode authentication.

    Creates the local user if needed and returns a permanent JWT token
    that the frontend can use.

    Returns:
        JWT token for the local user, or None if initialization fails.
    """
    if not settings.CLIENT_MODE:
        return None

    try:
        async with async_session_maker() as db:
            user = await get_or_create_local_user(db)

            # Create a long-lived token (365 days)
            from datetime import timedelta
            token = create_access_token(
                data={"sub": user.id},
                expires_delta=timedelta(days=365)
            )

            logger.info("[CLIENT_AUTH] Client authentication initialized")
            return token

    except Exception as e:
        logger.error(f"[CLIENT_AUTH] Failed to initialize: {e}")
        return None


# Cache the local user token
_local_token: str | None = None


async def get_local_token() -> str | None:
    """Get the cached local token, initializing if needed."""
    global _local_token

    if _local_token is None:
        _local_token = await initialize_client_auth()

    return _local_token
