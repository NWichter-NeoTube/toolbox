"""SQLModel database models.

Define your domain models here. Each model maps to a PostgreSQL table.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class ItemBase(SQLModel):
    """Shared fields for Item create/read."""

    title: str = Field(max_length=255)
    description: str = ""
    is_active: bool = True


class Item(ItemBase, table=True):
    """Persisted Item in the database."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    owner_id: str | None = Field(default=None, index=True)


class ItemCreate(ItemBase):
    """Request body for creating an Item."""

    pass


class ItemRead(ItemBase):
    """Response body for reading an Item."""

    id: uuid.UUID
    created_at: datetime
    owner_id: str | None
