from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated
from sqlalchemy import insert
from slugify import slugify

from catalog_service.app.models.db_depends import get_db
from catalog_service.app.schemas.categories import CreateCategory
from catalog_service.app.models.categories import Category
from catalog_service.app.models.products import Product

router = APIRouter(prefix='/category', tags=['categories'])


@router.get('/')
async def get_all_categories():
    pass


@router.post('/', status_code=status.HTTP_201_CREATED)
async def create_category(db: Annotated[Session, Depends(get_db)], create_category: CreateCategory):
    db.execute(insert(Category).values(name=create_category.name,
                                       parent_id=create_category.parent_id,
                                       slug=slugify(create_category.name)))
    db.commit()
    return {
        'status_code': status.HTTP_201_CREATED,
        'transaction': 'Successful'
    }


@router.put('/')
async def update_category():
    pass


@router.delete('/')
async def delete_category():
    pass