import datetime

def get_current_time():
    """Функция возвращает текущее время"""
    return datetime.datetime.now()

def print_time(time_arg = get_current_time()):
    """Функция с аргументом по умолчанию"""
    print(f"Время: {time_arg}")

# Тестируем
print("Первый вызов:")
print_time()  # Время зафиксируется при загрузке модуля

print("\nЖдем 2 секунды...")
import time
time.sleep(2)

print("Второй вызов:")
print_time()  # Покажет то же самое время!

print("Третий вызов:")
print_time()  # Снова то же время!