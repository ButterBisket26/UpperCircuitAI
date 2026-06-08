import os
import logging
from typing import AsyncGenerator, Optional
import asyncpg
from app.config import settings

logger = logging.getLogger(__name__)

class DatabaseConnectionManager:
    """Manages database connection pool with Neon serverless Postgres."""
    
    def __init__(self) -> None:
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self) -> None:
        """Initialize the asyncpg connection pool."""
        if self.pool is not None:
            return
        
        dsn = settings.DATABASE_URL
        if not dsn:
            logger.error("DATABASE_URL is not set.")
            raise ValueError("DATABASE_URL env var is missing.")
        
        try:
            # Setup pool
            self.pool = await asyncpg.create_pool(
                dsn,
                min_size=2,
                max_size=10,
                max_inactive_connection_lifetime=300.0,
                command_timeout=60.0
            )
            logger.info("Database connection pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}", exc_info=True)
            raise e

    async def close(self) -> None:
        """Close the connection pool."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed.")

    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Acquire a connection from the pool."""
        if self.pool is None:
            await self.initialize()
        
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            yield conn

db_manager = DatabaseConnectionManager()

async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency helper to get a db connection in endpoints."""
    async for conn in db_manager.get_connection():
        yield conn
