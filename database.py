#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Модуль для работы с SQLite базой данных проекта мультиварки.
Заменяет JSON файлы для хранения рецептов и склада.
"""

import sqlite3
import threading
import os
import random
from typing import Dict, List, Optional, Tuple


class MultivarkaDatabase:
    def __init__(self, db_path='multivarka.db'):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_database()
    
    def init_database(self):
        """Инициализирует базу данных с помощью схемы"""
        try:
            schema_path = os.path.join(os.path.dirname(__file__), 'database_schema.sql')
            with open(schema_path, 'r', encoding='utf-8') as f:
                schema = f.read()
            
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                conn.executescript(schema)
                
                # Проверяем и добавляем колонку expiration_date если её нет
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(warehouse)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'expiration_date' not in columns:
                    cursor.execute("ALTER TABLE warehouse ADD COLUMN expiration_date DATE")
                    print("Добавлена колонка expiration_date в таблицу warehouse")
                
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Ошибка инициализации БД: {e}")
            raise
    
    def get_connection(self):
        """Возвращает соединение с базой данных"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Для удобного доступа к колонкам
        return conn
    
    # === РАБОТА СО СКЛАДОМ ===
    
    def load_warehouse(self) -> Dict:
        """Загружает данные склада в формате, совместимом с текущим кодом"""
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT product_name, quantity, unit, product_type, expiration_date FROM warehouse")
            rows = cursor.fetchall()
            conn.close()
            
            warehouse = {"склад": {}}
            for row in rows:
                product_data = {
                    "количество": row['quantity'],
                    "единица": row['unit'],
                    "тип": row['product_type']
                }
                if row['expiration_date']:
                    product_data["срок_годности"] = row['expiration_date']
                warehouse["склад"][row['product_name']] = product_data
            
            return warehouse
    
    def save_warehouse(self, warehouse_data: Dict) -> bool:
        """Сохраняет данные склада"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Очищаем текущий склад
                cursor.execute("DELETE FROM warehouse")
                
                # Добавляем новые данные
                for product_name, product_data in warehouse_data.get("склад", {}).items():
                    product_type = product_data.get('тип', 'quantity')
                    expiration_date = product_data.get('срок_годности')
                    cursor.execute("""
                        INSERT INTO warehouse (product_name, quantity, unit, product_type, expiration_date)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product_name, product_data['количество'], product_data['единица'], product_type, expiration_date))
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"Ошибка сохранения склада: {e}")
            return False
    
    def update_product_quantity(self, product_name: str, quantity: float) -> bool:
        """Обновляет количество продукта на складе"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE warehouse 
                    SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE product_name = ?
                """, (quantity, product_name))
                
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                return success
        except Exception as e:
            print(f"Ошибка обновления продукта: {e}")
            return False
    
    def update_product_expiration(self, product_name: str, expiration_date: str) -> bool:
        """Обновляет срок годности продукта на складе"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE warehouse 
                    SET expiration_date = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE product_name = ?
                """, (expiration_date, product_name))
                
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                return success
        except Exception as e:
            print(f"Ошибка обновления срока годности: {e}")
            return False
    
    def add_product_to_warehouse(self, product_name: str, quantity: float, unit: str, product_type: str = 'quantity', expiration_date: str = None) -> bool:
        """Добавляет продукт к складу или увеличивает его количество"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Проверяем, есть ли продукт
                cursor.execute("SELECT quantity, product_type FROM warehouse WHERE product_name = ?", (product_name,))
                row = cursor.fetchone()
                
                if row:
                    # Для продуктов с типом 'availability' просто устанавливаем наличие
                    if product_type == 'availability' or row['product_type'] == 'availability':
                        cursor.execute("""
                            UPDATE warehouse 
                            SET quantity = 1, product_type = 'availability', expiration_date = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE product_name = ?
                        """, (expiration_date, product_name))
                    else:
                        # Увеличиваем количество для обычных продуктов
                        new_quantity = row['quantity'] + quantity
                        cursor.execute("""
                            UPDATE warehouse 
                            SET quantity = ?, expiration_date = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE product_name = ?
                        """, (new_quantity, expiration_date, product_name))
                else:
                    # Добавляем новый продукт
                    cursor.execute("""
                        INSERT INTO warehouse (product_name, quantity, unit, product_type, expiration_date)
                        VALUES (?, ?, ?, ?, ?)
                    """, (product_name, quantity, unit, product_type, expiration_date))
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"Ошибка добавления продукта: {e}")
            return False
    
    def delete_product_from_warehouse(self, product_name: str) -> bool:
        """Удаляет продукт со склада"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM warehouse WHERE product_name = ?", (product_name,))
                
                conn.commit()
                success = cursor.rowcount > 0
                conn.close()
                return success
        except Exception as e:
            print(f"Ошибка удаления продукта: {e}")
            return False
    
    # === РАБОТА С РЕЦЕПТАМИ ===
    
    def get_all_recipes(self) -> List[Dict]:
        """Возвращает все рецепты в формате, совместимом с текущим кодом"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, meal_type, is_ready 
            FROM recipes 
            ORDER BY created_at DESC
        """)
        recipes_data = cursor.fetchall()
        
        recipes = []
        for recipe_row in recipes_data:
            recipe_id = recipe_row['id']
            
            # Получаем ингредиенты
            cursor.execute("""
                SELECT product_name, quantity, unit, ingredient_type
                FROM recipe_ingredients 
                WHERE recipe_id = ?
                ORDER BY id
            """, (recipe_id,))
            ingredients_data = cursor.fetchall()
            
            # Получаем инструкции
            cursor.execute("""
                SELECT step_number, instruction
                FROM recipe_instructions 
                WHERE recipe_id = ?
                ORDER BY step_number
            """, (recipe_id,))
            instructions_data = cursor.fetchall()
            
            # Формируем структуру рецепта
            meal_data = {
                "блюдо": recipe_row['name']
            }
            
            if recipe_row['is_ready']:
                meal_data["готово"] = True
            
            # Обрабатываем ингредиенты
            ingredients = []
            for ing in ingredients_data:
                ingredient = {
                    "продукт": ing['product_name'],
                    "количество": ing['quantity'],
                    "единица": ing['unit'],
                    "тип": ing['ingredient_type']
                }
                ingredients.append(ingredient)
            
            if ingredients:
                meal_data["ингредиенты"] = ingredients
            
            # Обрабатываем инструкции
            instructions = []
            for inst in instructions_data:
                instructions.append(inst['instruction'])
            
            if instructions:
                meal_data["инструкции"] = instructions
            
            # Создаем рецепт в старом формате
            recipe = {
                "меню": {
                    recipe_row['meal_type']: meal_data
                }
            }
            recipes.append(recipe)
        
        conn.close()
        return recipes
    
    def get_recipes_by_meal_type(self, meal_type: str) -> List[Dict]:
        """Возвращает рецепты определенного типа приема пищи"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, is_ready 
            FROM recipes 
            WHERE meal_type = ?
            ORDER BY created_at DESC
        """, (meal_type,))
        
        recipes_data = cursor.fetchall()
        recipes = []
        
        for recipe_row in recipes_data:
            recipe_id = recipe_row['id']
            
            # Получаем ингредиенты и инструкции
            cursor.execute("""
                SELECT product_name, quantity, unit, ingredient_type
                FROM recipe_ingredients 
                WHERE recipe_id = ?
                ORDER BY id
            """, (recipe_id,))
            ingredients_data = cursor.fetchall()
            
            cursor.execute("""
                SELECT step_number, instruction
                FROM recipe_instructions 
                WHERE recipe_id = ?
                ORDER BY step_number
            """, (recipe_id,))
            instructions_data = cursor.fetchall()
            
            # Формируем meal_data
            meal_data = {"блюдо": recipe_row['name']}
            
            if recipe_row['is_ready']:
                meal_data["готово"] = True
            
            # Обрабатываем ингредиенты
            ingredients = []
            for ing in ingredients_data:
                ingredient = {
                    "продукт": ing['product_name'],
                    "количество": ing['quantity'],
                    "единица": ing['unit'],
                    "тип": ing['ingredient_type']
                }
                ingredients.append(ingredient)
            
            if ingredients:
                meal_data["ингредиенты"] = ingredients
            
            # Обрабатываем инструкции  
            instructions = []
            for inst in instructions_data:
                instructions.append(inst['instruction'])
            
            if instructions:
                meal_data["инструкции"] = instructions
            
            recipes.append(meal_data)
        
        conn.close()
        return recipes
    
    def add_single_recipe(self, meal_type: str, meal_data: Dict) -> bool:
        """Добавляет одиночный рецепт в базу данных"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Создаем запись рецепта
                cursor.execute("""
                    INSERT INTO recipes (name, meal_type, is_ready)
                    VALUES (?, ?, ?)
                """, (
                    meal_data.get('блюдо', ''),
                    meal_type,
                    meal_data.get('готово', False)
                ))
                
                recipe_id = cursor.lastrowid
                
                # Добавляем ингредиенты
                if 'ингредиенты' in meal_data:
                    self._add_ingredients(cursor, recipe_id, meal_data['ингредиенты'])
                
                # Добавляем инструкции
                if 'инструкции' in meal_data:
                    self._add_instructions(cursor, recipe_id, meal_data['инструкции'])
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            print(f"Ошибка добавления рецепта: {e}")
            return False
    
    def _add_ingredients(self, cursor, recipe_id: int, ingredients: List[Dict]):
        """Добавляет ингредиенты рецепта"""
        for ingredient in ingredients:
            ingredient_type = ingredient.get('тип', 'quantity')
            cursor.execute("""
                INSERT INTO recipe_ingredients (recipe_id, product_name, quantity, unit, ingredient_type)
                VALUES (?, ?, ?, ?, ?)
            """, (
                recipe_id,
                ingredient['продукт'],
                ingredient['количество'],
                ingredient['единица'],
                ingredient_type
            ))
    
    def _add_instructions(self, cursor, recipe_id: int, instructions: List[str]):
        """Добавляет инструкции рецепта"""
        for step_num, instruction in enumerate(instructions, 1):
            cursor.execute("""
                INSERT INTO recipe_instructions (recipe_id, step_number, instruction)
                VALUES (?, ?, ?)
            """, (recipe_id, step_num, instruction))
    
    def get_mixed_recipe(self) -> Optional[Dict]:
        """Создает смешанный рецепт, выбирая случайные блюда для каждого приема пищи"""
        # Сначала пытаемся загрузить текущий рецепт
        current_recipe = self.get_current_recipe()
        if current_recipe:
            return current_recipe
        
        # Если текущего рецепта нет, создаем новый
        meal_types = ["завтрак", "второй_завтрак", "обед", "полдник", "ужин"]
        mixed_recipe = {"меню": {}}
        
        for meal_type in meal_types:
            recipes = self.get_recipes_by_meal_type(meal_type)
            if recipes:
                mixed_recipe['меню'][meal_type] = random.choice(recipes)
        
        if mixed_recipe['меню']:
            # Сохраняем новый рецепт как текущий
            self.save_current_recipe(mixed_recipe)
            return mixed_recipe
        
        return None
    
    def optimize_recipe_for_warehouse(self) -> Optional[Dict]:
        """Создает оптимизированный рецепт для минимизации покупок"""
        # Загружаем текущий рецепт для сохранения статусов skip_cooking
        current_recipe = self.get_current_recipe()
        
        meal_types = ["завтрак", "второй_завтрак", "обед", "полдник", "ужин"]
        warehouse_data = self.load_warehouse()
        optimized_recipe = {"меню": {}}
        
        for meal_type in meal_types:
            # Проверяем, остановлено ли это блюдо в текущем рецепте
            current_skip_status = False
            if current_recipe and meal_type in current_recipe['меню']:
                current_skip_status = current_recipe['меню'][meal_type].get('skip_cooking', False)
            
            # Если блюдо остановлено, сохраняем его как есть
            if current_skip_status and current_recipe and meal_type in current_recipe['меню']:
                optimized_recipe['меню'][meal_type] = current_recipe['меню'][meal_type]
                continue
            
            # Иначе подбираем оптимальное блюдо
            recipes = self.get_recipes_by_meal_type(meal_type)
            if not recipes:
                continue
            
            best_meal = None
            best_score = float('inf')
            
            for recipe_meal in recipes:
                # Вычисляем "стоимость" блюда
                total_cost = 0
                missing_ingredients = 0
                
                # Основные ингредиенты
                if 'ингредиенты' in recipe_meal:
                    cost, missing = self._calculate_meal_cost(recipe_meal['ингредиенты'], warehouse_data)
                    total_cost += cost
                    missing_ingredients += missing
                

                
                score = total_cost * 10 + missing_ingredients
                if score < best_score:
                    best_score = score
                    best_meal = recipe_meal
            
            if best_meal:
                optimized_recipe['меню'][meal_type] = best_meal
        
        return optimized_recipe if optimized_recipe['меню'] else None
    
    def _get_expiration_priority_bonus(self, expiration_date_str: str) -> float:
        """Вычисляет бонус приоритета для продукта на основе срока годности"""
        if not expiration_date_str:
            return 0  # Нет срока годности - нет бонуса
        
        try:
            from datetime import datetime, date
            expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d').date()
            today = date.today()
            days_until_expiration = (expiration_date - today).days
            
            if days_until_expiration < 0:
                # Просроченный продукт - штраф
                return 50
            elif days_until_expiration == 0:
                # Истекает сегодня - максимальный приоритет
                return -100
            elif days_until_expiration <= 3:
                # Скоро истекает - высокий приоритет
                return -50
            elif days_until_expiration <= 7:
                # Истекает на неделе - средний приоритет
                return -20
            else:
                # Свежий продукт - небольшой бонус
                return -5
        except ValueError:
            return 0  # Ошибка парсинга даты - нет бонуса

    def _calculate_meal_cost(self, ingredients: List[Dict], warehouse_data: Dict) -> Tuple[float, int]:
        """Вычисляет стоимость блюда с учётом сроков годности и наличия на складе"""
        total_cost = 0
        missing_ingredients = 0
        
        for ingredient in ingredients:
            product = ingredient['продукт']
            amount = ingredient['количество']
            ingredient_type = ingredient.get('тип', 'quantity')
            
            if product in warehouse_data['склад']:
                available = warehouse_data['склад'][product]['количество']
                product_type = warehouse_data['склад'][product].get('тип', 'quantity')
                expiration_date = warehouse_data['склад'][product].get('срок_годности')
                
                # Получаем бонус за срок годности
                expiration_bonus = self._get_expiration_priority_bonus(expiration_date)
                
                # Для продуктов с простым наличием
                if ingredient_type == 'availability' or product_type == 'availability':
                    if available == 0:
                        total_cost += 1  # Нужно купить один продукт
                        missing_ingredients += 1
                    else:
                        # Продукт есть - применяем бонус за срок годности
                        total_cost += expiration_bonus
                else:
                    # Для обычных продуктов с количеством
                    if available < amount:
                        shortage = amount - available
                        total_cost += shortage
                        missing_ingredients += 1
                        # Частично есть - применяем небольшой бонус за срок годности
                        if available > 0:
                            total_cost += expiration_bonus * 0.3
                    else:
                        # Продукта достаточно - применяем полный бонус за срок годности
                        total_cost += expiration_bonus
            else:
                # Продукта нет на складе
                if ingredient_type == 'availability':
                    total_cost += 1  # Нужно купить один продукт
                else:
                    total_cost += amount
                missing_ingredients += 1
        
        return total_cost, missing_ingredients
    
    def get_all_products_from_recipes(self) -> Dict[str, str]:
        """Возвращает все продукты, используемые в рецептах, и их единицы измерения"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT product_name, unit 
            FROM recipe_ingredients
            ORDER BY product_name
        """)
        
        products = {}
        for row in cursor.fetchall():
            products[row['product_name']] = row['unit']
        
        conn.close()
        return products
    
    def consume_ingredients_for_meal(self, meal_type: str, meal_data: Dict) -> bool:
        """Удаляет ингредиенты со склада после приготовления блюда"""
        try:
            # Пропускаем блюда, которые не нужно готовить
            if meal_data.get('skip_cooking', False):
                return True
                
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Основные ингредиенты
                if 'ингредиенты' in meal_data:
                    for ingredient in meal_data['ингредиенты']:
                        self._consume_ingredient(cursor, ingredient)
                

                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            print(f"Ошибка потребления ингредиентов: {e}")
            return False
    
    def _consume_ingredient(self, cursor, ingredient: Dict):
        """Уменьшает количество ингредиента на складе"""
        ingredient_type = ingredient.get('тип', 'quantity')
        
        if ingredient_type == 'availability':
            # Для продуктов с простым наличием просто сбрасываем в 0
            cursor.execute("""
                UPDATE warehouse 
                SET quantity = 0, updated_at = CURRENT_TIMESTAMP
                WHERE product_name = ?
            """, (ingredient['продукт'],))
        else:
            # Для обычных продуктов уменьшаем количество
            cursor.execute("""
                UPDATE warehouse 
                SET quantity = MAX(0, quantity - ?), updated_at = CURRENT_TIMESTAMP
                WHERE product_name = ?
            """, (ingredient['количество'], ingredient['продукт']))
    
    def get_recipe_by_id(self, recipe_id: int) -> Optional[Dict]:
        """Возвращает рецепт по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Получаем основную информацию о рецепте
        cursor.execute("""
            SELECT id, name, meal_type, is_ready, created_at
            FROM recipes 
            WHERE id = ?
        """, (recipe_id,))
        
        recipe_row = cursor.fetchone()
        if not recipe_row:
            conn.close()
            return None
        
        # Получаем ингредиенты
        cursor.execute("""
            SELECT product_name, quantity, unit, ingredient_type
            FROM recipe_ingredients 
            WHERE recipe_id = ?
            ORDER BY id
        """, (recipe_id,))
        ingredients_data = cursor.fetchall()
        
        # Получаем инструкции
        cursor.execute("""
            SELECT step_number, instruction
            FROM recipe_instructions 
            WHERE recipe_id = ?
            ORDER BY step_number
        """, (recipe_id,))
        instructions_data = cursor.fetchall()
        
        conn.close()
        
        # Формируем структуру рецепта
        recipe_info = {
            "id": recipe_row['id'],
            "название": recipe_row['name'],
            "тип_приема": recipe_row['meal_type'],
            "готово": bool(recipe_row['is_ready']),
            "создан": recipe_row['created_at']
        }
        
        # Обрабатываем ингредиенты
        ingredients = []
        for ing in ingredients_data:
            ingredient = {
                "продукт": ing['product_name'],
                "количество": ing['quantity'],
                "единица": ing['unit']
            }
            ingredients.append(ingredient)
        
        if ingredients:
            recipe_info["ингредиенты"] = ingredients
        
        # Обрабатываем инструкции
        instructions = []
        for inst in instructions_data:
            instructions.append(inst['instruction'])
        
        if instructions:
            recipe_info["инструкции"] = instructions
        
        return recipe_info
    
    def get_all_recipes_with_info(self) -> List[Dict]:
        """Возвращает список всех рецептов с краткой информацией для управления"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT r.id, r.name, r.meal_type, r.is_ready, r.created_at,
                   COUNT(DISTINCT ri.id) as ingredient_count
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            GROUP BY r.id, r.name, r.meal_type, r.is_ready, r.created_at
            ORDER BY r.created_at DESC
        """)
        
        recipes = []
        for row in cursor.fetchall():
            recipes.append({
                "id": row['id'],
                "название": row['name'],
                "тип_приема": row['meal_type'],
                "готово": bool(row['is_ready']),
                "создан": row['created_at'],
                "количество_ингредиентов": row['ingredient_count']
            })
        
        conn.close()
        return recipes
    
    def update_recipe(self, recipe_id: int, meal_data: Dict) -> bool:
        """Обновляет существующий рецепт"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Проверяем, что рецепт существует
                cursor.execute("SELECT id FROM recipes WHERE id = ?", (recipe_id,))
                if not cursor.fetchone():
                    conn.close()
                    return False
                
                # Обновляем основную информацию рецепта
                cursor.execute("""
                    UPDATE recipes 
                    SET name = ?, is_ready = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    meal_data.get('блюдо', ''),
                    meal_data.get('готово', False),
                    recipe_id
                ))
                
                # Удаляем старые ингредиенты и инструкции
                cursor.execute("DELETE FROM recipe_ingredients WHERE recipe_id = ?", (recipe_id,))
                cursor.execute("DELETE FROM recipe_instructions WHERE recipe_id = ?", (recipe_id,))
                
                # Добавляем новые ингредиенты и инструкции
                if 'ингредиенты' in meal_data:
                    self._add_ingredients(cursor, recipe_id, meal_data['ингредиенты'])
                
                if 'инструкции' in meal_data:
                    self._add_instructions(cursor, recipe_id, meal_data['инструкции'])
                
                conn.commit()
                conn.close()
                return True
                
        except Exception as e:
            print(f"Ошибка обновления рецепта: {e}")
            return False
    
    def delete_recipe(self, recipe_id: int) -> bool:
        """Удаляет рецепт по ID"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Удаляем рецепт (каскадное удаление ингредиентов и инструкций)
                cursor.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
                
                success = cursor.rowcount > 0
                conn.commit()
                conn.close()
                return success
                
        except Exception as e:
            print(f"Ошибка удаления рецепта: {e}")
            return False
    
    def search_recipes(self, query: str = None, meal_type: str = None) -> List[Dict]:
        """Поиск рецептов по названию или типу приема пищи"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT r.id, r.name, r.meal_type, r.is_ready, r.created_at,
                   COUNT(DISTINCT ri.id) as ingredient_count
            FROM recipes r
            LEFT JOIN recipe_ingredients ri ON r.id = ri.recipe_id
            WHERE 1=1
        """
        params = []
        
        if query:
            sql += " AND (r.name LIKE ? OR r.name LIKE ?)"
            params.extend([f"%{query}%", f"%{query.lower()}%"])
        
        if meal_type:
            sql += " AND r.meal_type = ?"
            params.append(meal_type)
        
        sql += " GROUP BY r.id ORDER BY r.created_at DESC"
        
        cursor.execute(sql, params)
        
        recipes = []
        for row in cursor.fetchall():
            recipes.append({
                "id": row['id'],
                "название": row['name'],
                "тип_приема": row['meal_type'],
                "готово": bool(row['is_ready']),
                "создан": row['created_at'],
                "количество_ингредиентов": row['ingredient_count']
            })
        
        conn.close()
        return recipes
    
    # === РАБОТА С ТЕКУЩИМ РЕЦЕПТОМ ===
    
    def get_current_recipe(self) -> Optional[Dict]:
        """Загружает текущий сохраненный рецепт"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT recipe_data FROM current_recipe LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            
            if row:
                import json
                return json.loads(row['recipe_data'])
            return None
        except Exception as e:
            print(f"Ошибка загрузки текущего рецепта: {e}")
            return None
    
    def save_current_recipe(self, recipe: Dict) -> bool:
        """Сохраняет текущий рецепт"""
        try:
            import json
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                
                # Удаляем старый текущий рецепт
                cursor.execute("DELETE FROM current_recipe")
                
                # Сохраняем новый
                cursor.execute("""
                    INSERT INTO current_recipe (recipe_data)
                    VALUES (?)
                """, (json.dumps(recipe, ensure_ascii=False),))
                
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"Ошибка сохранения текущего рецепта: {e}")
            return False
    
    def replace_meal_in_current_recipe(self, meal_type: str) -> Optional[Dict]:
        """Заменяет конкретное блюдо в текущем рецепте"""
        try:
            # Загружаем текущий рецепт
            current_recipe = self.get_current_recipe()
            if not current_recipe:
                return None
            
            # Сохраняем текущий статус skip_cooking
            current_skip_status = False
            if meal_type in current_recipe['меню']:
                current_skip_status = current_recipe['меню'][meal_type].get('skip_cooking', False)
            
            # Получаем новое блюдо для замены
            new_meals = self.get_recipes_by_meal_type(meal_type)
            if not new_meals:
                return None
            
            # Исключаем текущее блюдо из выбора
            current_dish = None
            if meal_type in current_recipe['меню'] and 'блюдо' in current_recipe['меню'][meal_type]:
                current_dish = current_recipe['меню'][meal_type]['блюдо']
            
            # Фильтруем блюда, исключая текущее
            available_meals = [meal for meal in new_meals if meal.get('блюдо') != current_dish]
            if not available_meals:
                # Если все блюда одинаковые, берем любое
                available_meals = new_meals
            
            # Выбираем случайное новое блюдо
            new_meal = random.choice(available_meals)
            
            # Сохраняем статус skip_cooking в новом блюде
            new_meal['skip_cooking'] = current_skip_status
            
            # Обновляем рецепт
            current_recipe['меню'][meal_type] = new_meal
            
            # Сохраняем обновленный рецепт
            if self.save_current_recipe(current_recipe):
                return current_recipe
            
            return None
        except Exception as e:
            print(f"Ошибка замены блюда в текущем рецепте: {e}")
            return None
    
    def clear_current_recipe(self) -> bool:
        """Очищает текущий рецепт (для создания нового)"""
        try:
            with self.lock:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM current_recipe")
                conn.commit()
                conn.close()
                return True
        except Exception as e:
            print(f"Ошибка очистки текущего рецепта: {e}")
            return False
    
    def toggle_skip_cooking(self, meal_type: str) -> Optional[Dict]:
        """Переключает статус skip_cooking для конкретного блюда в текущем рецепте"""
        try:
            # Загружаем текущий рецепт
            current_recipe = self.get_current_recipe()
            if not current_recipe or meal_type not in current_recipe['меню']:
                return None
            
            # Переключаем статус
            meal_data = current_recipe['меню'][meal_type]
            current_status = meal_data.get('skip_cooking', False)
            meal_data['skip_cooking'] = not current_status
            
            # Сохраняем обновленный рецепт
            if self.save_current_recipe(current_recipe):
                return current_recipe
            
            return None
        except Exception as e:
            print(f"Ошибка переключения статуса skip_cooking: {e}")
            return None


# Глобальный экземпляр базы данных
# Путь к БД относительно корня проекта
db_path = os.path.join(os.path.dirname(__file__), 'multivarka.db')
db = MultivarkaDatabase(db_path)
