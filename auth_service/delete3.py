import time
from datetime import datetime


def process_data(data):
    print(f"Обрабатываем: {data}")


def my_depends():
    # any depends
    return f"Данные: {datetime.now()}"


# Каждый раз вызывается заново!
process_data(my_depends())
time.sleep(3)
process_data(my_depends())