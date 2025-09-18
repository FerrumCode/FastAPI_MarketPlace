import time
from datetime import datetime


def get_fresh_data():
    return f"Данные: {datetime.now()}"

def process_data(data):
    print(f"Обрабатываем: {data}")

# Каждый раз вызывается заново!
process_data(get_fresh_data())
time.sleep(3)
process_data(get_fresh_data())