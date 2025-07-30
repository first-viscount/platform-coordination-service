"""Base repository interface."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(ABC, Generic[ModelType]):
    """Abstract base repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        self.session = session

    @abstractmethod
    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new entity."""
        ...

    @abstractmethod
    async def get(self, id: Any) -> ModelType | None:
        """Get entity by ID."""
        ...

    @abstractmethod
    async def update(self, id: Any, **kwargs: Any) -> ModelType | None:
        """Update entity."""
        ...

    @abstractmethod
    async def delete(self, id: Any) -> bool:
        """Delete entity."""
        ...

    @abstractmethod
    async def list(self, **filters: Any) -> list[ModelType]:
        """List entities with optional filters."""
        ...
