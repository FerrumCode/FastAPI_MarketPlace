from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase  # New

# engine = create_engine('sqlite:///catalog_service.db', echo=True) # по стёпику
# engine = create_engine('sqlite:///./catalog_service.db', echo=True) # по чатгпт
# SQLALCHEMY_DATABASE_URL = "sqlite:///C:/path/to/your/project/instance/catalog_service.db"
engine = create_engine('sqlite:///C:/Users/rezon/PycharmProjects/fastapi_market_place_01/catalog_service.db', echo=True) # по стёпику
# C:\Users\rezon\PycharmProjects\fastapi_market_place_01

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):  # New
    pass






from sqlalchemy import inspect

inspector = inspect(engine)
if "categories" not in inspector.get_table_names():
    print("Таблица 'categories' не найдена в БД!")
else:
    print("Таблица существует.")

from sqlalchemy import create_engine
import os

print(f"Файл БД существует: {os.path.exists('sqlite:///C:/Users/rezon/PycharmProjects/fastapi_market_place_01/catalog_service.db')}")