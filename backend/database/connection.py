"""
Database Connection
Handles database connection and session management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from .models import Base

# Database URL from environment or default (use SQLite for development)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./traffic_db.sqlite"
)

# Check if using SQLite or PostgreSQL
USE_SQLITE = DATABASE_URL.startswith("sqlite")

if USE_SQLITE:
    # SQLite configuration
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)
    # For SQLite async, use aiosqlite
    ASYNC_DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    # PostgreSQL configuration
    engine = create_engine(DATABASE_URL, echo=False)
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# Create async engine
try:
    async_engine = create_async_engine(ASYNC_DATABASE_URL, echo=False)
except Exception:
    # Fallback: use sync engine only if async fails
    async_engine = None

# Session factories
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def init_db():
    """
    Initialize database tables
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    Close database connections
    """
    await async_engine.dispose()


def get_db():
    """
    Get synchronous database session
    
    Usage:
        with get_db() as db:
            db.query(...)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Get asynchronous database session
    
    Usage:
        async with get_async_db() as db:
            await db.execute(...)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database session
    
    Usage:
        async with get_db_session() as db:
            await db.execute(...)
    """
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


class Database:
    """
    Database connection manager class
    """
    
    def __init__(self, database_url: str = None):
        """
        Initialize database manager
        
        Args:
            database_url: Database connection URL
        """
        self.database_url = database_url or DATABASE_URL
        self.async_url = self.database_url.replace(
            "postgresql://", "postgresql+asyncpg://"
        )
        
        self.engine = None
        self.async_engine = None
        self.session_factory = None
        self.async_session_factory = None
        
    async def connect(self):
        """
        Connect to database
        """
        self.engine = create_engine(self.database_url, echo=False)
        self.async_engine = create_async_engine(self.async_url, echo=False)
        
        self.session_factory = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        self.async_session_factory = sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create tables
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
    async def disconnect(self):
        """
        Disconnect from database
        """
        if self.async_engine:
            await self.async_engine.dispose()
        if self.engine:
            self.engine.dispose()
            
    async def get_session(self) -> AsyncSession:
        """
        Get async database session
        """
        return self.async_session_factory()
    
    def get_sync_session(self):
        """
        Get sync database session
        """
        return self.session_factory()


# Global database instance
db_instance = Database()
