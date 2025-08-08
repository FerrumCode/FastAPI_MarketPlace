from fastapi import FastAPI
from catalog_service.app.routers import categories, products
app = FastAPI()


@app.get("/")
async def welcome() -> dict:
    return {"message": "My e-commerce app"}


app.include_router(categories.router)
app.include_router(products.router)

# uvicorn catalog_service.app.main:app --reload