"""CRUD routes for Items — demonstrates SQLModel + Auth integration."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_session
from app.middleware.auth import AuthUser, get_current_user
from app.models import Item, ItemCreate, ItemRead

router = APIRouter(prefix="/api/v1/items", tags=["items"])


@router.get("", response_model=list[ItemRead])
async def list_items(
    session: AsyncSession = Depends(get_session),
    user: AuthUser = Depends(get_current_user),
) -> list[Item]:
    """List all items owned by the current user."""
    result = await session.execute(
        select(Item).where(Item.owner_id == user.user_id, Item.is_active)
    )
    return list(result.scalars().all())


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    body: ItemCreate,
    session: AsyncSession = Depends(get_session),
    user: AuthUser = Depends(get_current_user),
) -> Item:
    """Create a new item."""
    item = Item(**body.model_dump(), owner_id=user.user_id)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: AuthUser = Depends(get_current_user),
) -> Item:
    """Get a single item by ID."""
    item = await session.get(Item, item_id)
    if not item or item.owner_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    user: AuthUser = Depends(get_current_user),
) -> None:
    """Soft-delete an item."""
    item = await session.get(Item, item_id)
    if not item or item.owner_id != user.user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    item.is_active = False
    session.add(item)
    await session.commit()
