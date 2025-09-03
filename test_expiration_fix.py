#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки автоматической очистки срока годности при количестве 0
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))
from database import db

def test_expiration_cleanup():
    """Тестируем автоматическую очистку срока годности при нулевом количестве"""

    print("=== ТЕСТ АВТОМАТИЧЕСКОЙ ОЧИСТКИ СРОКА ГОДНОСТИ ===\n")

    # Тест 1: Добавляем продукт с количеством > 0 и сроком годности
    print("1. Добавляем продукт 'тестовый_продукт' с количеством 5 и сроком годности")
    success = db.add_product_to_warehouse("тестовый_продукт", 5, "шт", "quantity", "2025-12-31")
    if success:
        print("✅ Продукт добавлен")
    else:
        print("❌ Ошибка добавления продукта")
        return

    # Проверяем данные
    warehouse = db.load_warehouse()
    product = warehouse['склад'].get('тестовый_продукт')
    print(f"   Количество: {product['количество']}, Срок годности: {product.get('срок_годности')}")

    # Тест 2: Устанавливаем количество в 0 через update_product_quantity
    print("\n2. Устанавливаем количество в 0 через update_product_quantity")
    success = db.update_product_quantity("тестовый_продукт", 0)
    if success:
        print("✅ Количество обновлено")
    else:
        print("❌ Ошибка обновления количества")
        return

    # Проверяем данные
    warehouse = db.load_warehouse()
    product = warehouse['склад'].get('тестовый_продукт')
    print(f"   Количество: {product['количество']}, Срок годности: {product.get('срок_годности')}")

    # Тест 3: Добавляем продукт снова с положительным количеством
    print("\n3. Добавляем продукт снова с положительным количеством (3) и новым сроком годности")
    success = db.add_product_to_warehouse("тестовый_продукт", 3, "шт", "quantity", "2025-06-15")
    if success:
        print("✅ Продукт обновлен")
    else:
        print("❌ Ошибка обновления продукта")
        return

    # Проверяем данные
    warehouse = db.load_warehouse()
    product = warehouse['склад'].get('тестовый_продукт')
    print(f"   Количество: {product['количество']}, Срок годности: {product.get('срок_годности')}")

    # Тест 4: Добавляем отрицательное количество, чтобы итоговое стало 0
    print("\n4. Добавляем отрицательное количество (-3), чтобы итоговое количество стало 0")
    success = db.add_product_to_warehouse("тестовый_продукт", -3, "шт", "quantity", "2025-06-15")
    if success:
        print("✅ Продукт обновлен")
    else:
        print("❌ Ошибка обновления продукта")
        return

    # Проверяем данные
    warehouse = db.load_warehouse()
    product = warehouse['склад'].get('тестовый_продукт')
    print(f"   Количество: {product['количество']}, Срок годности: {product.get('срок_годности')}")

    print("\n=== ТЕСТ ЗАВЕРШЕН ===")
    print("Если срок годности автоматически очищается при количестве 0, то исправления работают корректно!")

if __name__ == "__main__":
    test_expiration_cleanup()
