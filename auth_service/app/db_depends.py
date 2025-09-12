# from .db import SessionLocal
#
#
# async def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


from .db import AsyncSessionLocal

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

