#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import random
import re
import time
import sys
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

# Добавляем родительскую папку в путь для импорта database
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from database import db

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # В продакшене использовать безопасный ключ

# Добавляем фильтр для форматирования чисел
@app.template_filter('format_number')
def format_number(value):
    """Форматирует числа, убирая ненужные десятичные знаки"""
    if isinstance(value, (int, float)):
        if value == int(value):
            return str(int(value))
        else:
            return f"{value:.1f}".rstrip('0').rstrip('.')
    return str(value)

# Добавляем функцию для работы с датами в шаблонах
@app.template_global()
def get_product_expiration_status(expiration_date_str):
    """Определяет статус продукта на основе срока годности"""
    if not expiration_date_str:
        return None, None
    
    try:
        from datetime import datetime, date
        expiration_date = datetime.strptime(expiration_date_str, '%Y-%m-%d').date()
        today = date.today()
        days_until_expiration = (expiration_date - today).days
        
        if days_until_expiration < 0:
            return 'expired', 'Просрочен'
        elif days_until_expiration == 0:
            return 'expires_today', 'Сегодня истекает'
        elif days_until_expiration <= 2:
            return 'expiring_soon', 'Скоро истекает'
        elif days_until_expiration <= 7:
            return 'expiring_week', 'Истекает на неделе'
        else:
            return 'fresh', 'Свежий'
    except ValueError:
        return None, None

def load_sklad():
    """Загружает данные склада из базы данных"""
    return db.load_warehouse()

def create_default_sklad():
    """Создает базовую структуру склада в базе данных"""
    default_products = [
        ("яйца", 0, "шт", "quantity"),
        ("молоко", 0, "мл", "quantity"),
        ("творог", 0, "г", "quantity"),
        ("картофель", 0, "шт", "quantity"),
        ("морковь", 0, "шт", "quantity"),
        ("курица", 0, "кг", "quantity"),
        ("говядина", 0, "кг", "quantity"),
        ("сахар", 0, "ч.л.", "availability"),  # Просто наличие
        ("чай", 0, "пакетик", "availability"),  # Просто наличие
        ("рис", 0, "г", "quantity"),
        ("рыба", 0, "шт", "quantity"),
        ("вода", 0, "л", "availability")  # Просто наличие
    ]
    
    default_sklad = {"склад": {}}
    for product, quantity, unit, product_type in default_products:
        db.add_product_to_warehouse(product, quantity, unit, product_type)
        default_sklad["склад"][product] = {"количество": quantity, "единица": unit, "тип": product_type}
    
    return default_sklad

def save_sklad(sklad_data):
    """Сохраняет данные склада в базу данных"""
    return db.save_warehouse(sklad_data)



def get_mixed_recipe():
    """Создает смешанный рецепт, выбирая случайные блюда для каждого приема пищи из базы данных"""
    return db.get_mixed_recipe()

def replace_meal_in_recipe(meal_type):
    """Заменяет конкретное блюдо в текущем рецепте на случайное из того же типа"""
    return db.replace_meal_in_current_recipe(meal_type)

def optimize_recipe_for_warehouse():
    """Создает оптимизированный рецепт, сохраняя все приемы пищи, но минимизируя покупки на основе текущего склада"""
    return db.optimize_recipe_for_warehouse()

def analyze_ingredients(recipe, sklad):
    """Анализирует ингредиенты рецепта и сравнивает со складом"""
    needed_products = {}
    
    def process_ingredients(ingredients_list):
        for ingredient in ingredients_list:
            product = ingredient['продукт']
            amount = ingredient['количество']
            unit = ingredient['единица']
            ingredient_type = ingredient.get('тип', 'quantity')
            
            if product in sklad['склад']:
                available = sklad['склад'][product]['количество']
                product_type = sklad['склад'][product].get('тип', 'quantity')
                
                # Для продуктов с простым наличием
                if ingredient_type == 'availability' or product_type == 'availability':
                    if available == 0:
                        needed_products[product] = {
                            'нужно': 1,
                            'единица': unit,
                            'есть': 0,
                            'тип': 'availability'
                        }
                else:
                    # Для обычных продуктов с количеством
                    needed = amount - available
                    if needed > 0:
                        needed_products[product] = {
                            'нужно': needed,
                            'единица': unit,
                            'есть': available,
                            'тип': 'quantity'
                        }
            else:
                # Продукта нет на складе
                if ingredient_type == 'availability':
                    needed_products[product] = {
                        'нужно': 1,
                        'единица': unit,
                        'есть': 0,
                        'тип': 'availability'
                    }
                else:
                    needed_products[product] = {
                        'нужно': amount,
                        'единица': unit,
                        'есть': 0,
                        'тип': 'quantity'
                    }
    
    # Обрабатываем все приемы пищи
    for meal_name, meal_data in recipe['меню'].items():
        # Пропускаем блюда, которые не нужно готовить
        if meal_data.get('skip_cooking', False):
            continue
        if 'ингредиенты' in meal_data:
            process_ingredients(meal_data['ингредиенты'])
    
    return needed_products



@app.route('/')
def index():
    """Главная страница - показывает рецепт и текущее состояние склада"""
    # Загружаем склад
    sklad = load_sklad()
    if not sklad:
        flash('❌ Не удалось загрузить склад', 'error')
        return render_template('index.html', sklad={}, recipe=None, needed_products={})
    
    # Создаем смешанный рецепт из всех доступных
    recipe = get_mixed_recipe()
    if not recipe:
        flash('❌ Не удалось загрузить рецепт', 'error')
        return render_template('index.html', sklad=sklad['склад'], recipe=None, needed_products={})
    
    # Анализируем ингредиенты
    needed_products = analyze_ingredients(recipe, sklad)
    
    # Сортируем продукты холодильника в алфавитном порядке
    sorted_sklad = dict(sorted(sklad['склад'].items(), key=lambda x: x[0].lower()))
    
    return render_template('index.html', 
                         sklad=sorted_sklad, 
                         recipe=recipe, 
                         needed_products=needed_products)

@app.route('/update_products', methods=['POST'])
def update_products():
    """Обновление продуктов на складе на основе рецептов"""
    try:
        # Загружаем текущий склад
        sklad = load_sklad()
        if not sklad:
            flash('❌ Не удалось загрузить склад', 'error')
            return redirect(url_for('index'))
        
        # Получаем все продукты из рецептов
        products_from_recipes = db.get_all_products_from_recipes()
        if not products_from_recipes:
            flash('❌ Не найдено рецептов для анализа', 'error')
            return redirect(url_for('index'))
        
        # Анализируем текущий склад
        current_products = set(sklad['склад'].keys())
        needed_products = set(products_from_recipes.keys())
        
        # Продукты для удаления (не используются в рецептах)
        products_to_remove = current_products - needed_products
        
        # Продукты для добавления (используются в рецептах, но нет на складе)
        products_to_add = needed_products - current_products
        
        # Продукты для обновления единиц измерения
        products_to_update_units = needed_products & current_products
        
        changes_made = []
        
        # Удаляем ненужные продукты
        for product in products_to_remove:
            db.delete_product_from_warehouse(product)
            changes_made.append(f"🗑️ Удален: {product}")
        
        # Добавляем нужные продукты
        for product in products_to_add:
            db.add_product_to_warehouse(product, 0, products_from_recipes[product])
            changes_made.append(f"➕ Добавлен: {product} ({products_from_recipes[product]})")
        
        # Обновляем единицы измерения для существующих продуктов
        for product in products_to_update_units:
            if sklad['склад'][product]['единица'] != products_from_recipes[product]:
                old_unit = sklad['склад'][product]['единица']
                # Обновляем единицу через обновление всего продукта
                current_quantity = sklad['склад'][product]['количество']
                db.delete_product_from_warehouse(product)
                db.add_product_to_warehouse(product, current_quantity, products_from_recipes[product])
                changes_made.append(f"🔄 Обновлена единица: {product} ({old_unit} → {products_from_recipes[product]})")
        
        if changes_made:
            changes_text = "\n".join(changes_made)
            flash(f'✅ Склад обновлен!\n{changes_text}', 'success')
        else:
            flash('✅ Склад уже актуален, изменения не требуются', 'success')
            
    except Exception as e:
        flash(f'❌ Ошибка при обновлении продуктов: {str(e)}', 'error')
        print(f"Ошибка в update_products: {e}")
    
    return redirect(url_for('index'))

@app.route('/delete/<product>', methods=['POST'])
def delete_product(product):
    """Удаление продукта"""
    if db.delete_product_from_warehouse(product):
        flash(f'Продукт "{product}" удален!', 'success')
    else:
        flash('Продукт не найден или ошибка при удалении!', 'error')
    
    return redirect(url_for('index'))

@app.route('/api/sklad')
def api_sklad():
    """API endpoint для получения данных склада"""
    sklad = load_sklad()
    return jsonify(sklad)

@app.route('/api/products')
def api_products():
    """API endpoint для получения списка продуктов со склада для автодополнения"""
    sklad = load_sklad()
    products = []
    for product_name, product_data in sklad.get('склад', {}).items():
        products.append({
            'name': product_name,
            'unit': product_data.get('единица', ''),
            'quantity': product_data.get('количество', 0)
        })
    return jsonify(products)

@app.route('/api/update/<product>', methods=['POST'])
def api_update_product(product):
    """API endpoint для обновления продукта"""
    try:
        data = request.get_json()
        quantity = float(data.get('quantity', 0))
        expiration_date = data.get('expiration_date')
        
        if quantity < 0:
            return jsonify({'error': 'Количество не может быть отрицательным'}), 400
        
        if db.update_product_quantity(product, quantity):
            # Обновляем срок годности (включая null для очистки)
            db.update_product_expiration(product, expiration_date)
            return jsonify({'success': True, 'message': f'Количество {product} обновлено'})
        else:
            return jsonify({'error': 'Продукт не найден'}), 404
            
    except (ValueError, KeyError):
        return jsonify({'error': 'Некорректные данные'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/api/add_single_meal', methods=['POST'])
def api_add_single_meal():
    """Добавляет рецепт для одного приема пищи в базу данных."""
    try:
        data = request.get_json() or {}

        meal_type = data.get('meal_type')
        meal_data = data.get('meal_data') or {}

        valid_meal_types = ["завтрак", "второй_завтрак", "обед", "полдник", "ужин"]
        if meal_type not in valid_meal_types:
            return jsonify({'error': 'Некорректный тип приема пищи'}), 400

        # Базовая валидация
        dish_name = (meal_data.get('блюдо') or '').strip()
        ingredients = meal_data.get('ингредиенты') or []
        
        if not dish_name:
            return jsonify({'error': 'Не указано название блюда (блюдо)'}), 400

        # Проверяем ингредиенты
        has_ingredients = isinstance(ingredients, list) and len(ingredients) > 0
        
        if not has_ingredients:
            return jsonify({'error': 'Нужно указать хотя бы один ингредиент'}), 400

        # Приводим ингредиенты к ожидаемому виду и проверяем
        normalized_ingredients = []
        
        # Обрабатываем основные ингредиенты (если есть)
        for ing in ingredients:
            product = (ing.get('продукт') or '').strip()
            unit = (ing.get('единица') or '').strip()
            try:
                amount = float(ing.get('количество'))
            except Exception:
                return jsonify({'error': f"Некорректное количество для ингредиента '{product or '?'}'"}), 400

            if not product or not unit or amount < 0:
                return jsonify({'error': f"Ингредиент должен содержать продукт, единицу и неотрицательное количество"}), 400

            normalized_ingredients.append({
                'продукт': product,
                'количество': amount,
                'единица': unit
            })

        # Собираем итоговую структуру блюда
        single_meal = {
            'блюдо': dish_name
        }
        
        # Добавляем ингредиенты только если они есть
        if normalized_ingredients:
            single_meal['ингредиенты'] = normalized_ingredients

        # Необязательные поля
        if isinstance(meal_data.get('готово'), bool):
            single_meal['готово'] = meal_data['готово']
        if isinstance(meal_data.get('инструкции'), list) and meal_data['инструкции']:
            single_meal['инструкции'] = [str(i) for i in meal_data['инструкции']]

        # Сохраняем рецепт в базу данных
        if db.add_single_recipe(meal_type, single_meal):
            return jsonify({'success': True, 'message': f'Рецепт на {meal_type} добавлен: {dish_name}'})
        else:
            return jsonify({'error': 'Не удалось сохранить рецепт в базу данных'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/buy_single_product', methods=['POST'])
def api_buy_single_product():
    """API endpoint для добавления одного купленного продукта на склад"""
    try:
        data = request.get_json()
        product = data.get('product')
        quantity = data.get('quantity')
        unit = data.get('unit')
        product_type = data.get('product_type', 'quantity')
        expiration_date = data.get('expiration_date')
        
        if not product or quantity is None or not unit:
            return jsonify({'error': 'Не все параметры указаны'}), 400
        
        if quantity < 0:
            return jsonify({'error': 'Количество не может быть отрицательным'}), 400
        
        if db.add_product_to_warehouse(product, quantity, unit, product_type, expiration_date):
            if product_type == 'availability':
                message = f'Продукт "{product}" добавлен на склад (есть в наличии)'
            else:
                message = f'Продукт "{product}" добавлен на склад (+{quantity} {unit})'
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'error': 'Ошибка при сохранении'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/create_new_product', methods=['POST'])
def api_create_new_product():
    """API endpoint для создания нового продукта на складе с нулевым количеством"""
    try:
        data = request.get_json()
        product = data.get('product')
        unit = data.get('unit')
        product_type = data.get('product_type', 'quantity')
        expiration_date = data.get('expiration_date')
        
        if not product or not unit:
            return jsonify({'error': 'Не указано название продукта или единица измерения'}), 400
        
        product = product.strip()
        unit = unit.strip()
        
        if not product or not unit:
            return jsonify({'error': 'Название продукта и единица измерения не могут быть пустыми'}), 400
        
        # Проверяем, что продукт не существует уже
        sklad = load_sklad()
        if product in sklad.get('склад', {}):
            return jsonify({'error': f'Продукт "{product}" уже существует на складе'}), 409
        
        # Добавляем продукт с нулевым количеством
        if db.add_product_to_warehouse(product, 0, unit, product_type, expiration_date):
            return jsonify({
                'success': True, 
                'message': f'Новый продукт "{product}" ({unit}) создан на складе',
                'product': {
                    'name': product,
                    'unit': unit,
                    'quantity': 0,
                    'type': product_type,
                    'expiration_date': expiration_date
                }
            })
        else:
            return jsonify({'error': 'Ошибка при сохранении в базу данных'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/toggle_skip_cooking', methods=['POST'])
def api_toggle_skip_cooking():
    """API endpoint для переключения статуса 'не готовить' для блюда"""
    try:
        data = request.get_json()
        meal_type = data.get('meal_type')
        
        if not meal_type:
            return jsonify({'error': 'Не указан тип приема пищи'}), 400
        
        # Переключаем статус в базе данных
        updated_recipe = db.toggle_skip_cooking(meal_type)
        if not updated_recipe:
            return jsonify({'error': 'Не удалось обновить статус блюда'}), 500
        
        # Получаем новый статус
        new_status = updated_recipe['меню'][meal_type].get('skip_cooking', False)
        
        # Пересчитываем список покупок для обновленного рецепта
        sklad = load_sklad()
        needed_products = analyze_ingredients(updated_recipe, sklad)
        
        # Формируем сообщение
        status_text = "не готовить" if new_status else "готовить"
        message = f"Блюдо '{meal_type}' теперь отмечено как '{status_text}'"
        
        return jsonify({
            'success': True,
            'message': message,
            'meal_type': meal_type,
            'skip_cooking': new_status,
            'needed_products': needed_products
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh_recipe', methods=['POST'])
def api_refresh_recipe():
    """API endpoint для обновления рецепта на случайный новый"""
    try:
        # Очищаем текущий рецепт для создания нового
        db.clear_current_recipe()
        
        # Создаем новый смешанный рецепт
        new_recipe = get_mixed_recipe()
        if not new_recipe:
            return jsonify({'error': 'Не удалось загрузить новый рецепт'}), 500
        
        # Формируем сообщение с названиями блюд
        meal_names = []
        for meal_name, meal_data in new_recipe['меню'].items():
            if 'блюдо' in meal_data:
                meal_names.append(f"{meal_name}: {meal_data['блюдо']}")
        
        meal_list = ", ".join(meal_names)
        
        return jsonify({
            'success': True, 
            'message': f'Рецепт обновлен! Новые блюда: {meal_list}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/optimize_recipe', methods=['POST'])
def api_optimize_recipe():
    """API endpoint для оптимизации рецепта (минимизация покупок)"""
    try:
        # Создаем оптимизированный рецепт (сохраняя статусы skip_cooking)
        optimized_recipe = optimize_recipe_for_warehouse()
        if not optimized_recipe:
            return jsonify({'error': 'Не удалось создать оптимизированный рецепт'}), 500
        
        # Сохраняем оптимизированный рецепт как текущий
        db.save_current_recipe(optimized_recipe)
        
        # Анализируем ингредиенты для подсчета экономии
        sklad = load_sklad()
        needed_products = analyze_ingredients(optimized_recipe, sklad)
        
        # Подсчитываем общую стоимость покупок
        total_cost = sum(info['нужно'] for info in needed_products.values())
        
        # Формируем сообщение с названиями блюд и экономией
        meal_names = []
        for meal_name, meal_data in optimized_recipe['меню'].items():
            if 'блюдо' in meal_data:
                meal_names.append(f"{meal_name}: {meal_data['блюдо']}")
        
        meal_list = ", ".join(meal_names)
        
        if total_cost == 0:
            message = f"Отлично! Подобран идеальный рецепт из имеющихся продуктов: {meal_list}"
        else:
            message = f"Подобран оптимальный рецепт! Все блюда сохранены, но нужно докупить продуктов на {total_cost} единиц: {meal_list}"
        
        return jsonify({
            'success': True, 
            'message': message,
            'total_cost': total_cost,
            'optimized_recipe': optimized_recipe,
            'needed_products': needed_products
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/replace_meal', methods=['POST'])
def api_replace_meal():
    """API endpoint для замены конкретного блюда на случайное из того же типа"""
    try:
        data = request.get_json()
        meal_type = data.get('meal_type')
        
        if not meal_type:
            return jsonify({'error': 'Не указан тип приема пищи'}), 400
        
        # Заменяем блюдо в текущем рецепте
        updated_recipe = replace_meal_in_recipe(meal_type)
        if not updated_recipe:
            return jsonify({'error': f'Не удалось заменить блюдо для {meal_type}'}), 500
        
        # Формируем сообщение с новым блюдом
        if meal_type in updated_recipe['меню'] and 'блюдо' in updated_recipe['меню'][meal_type]:
            meal_name = updated_recipe['меню'][meal_type]['блюдо']
            new_meal_data = updated_recipe['меню'][meal_type]
        else:
            meal_name = meal_type
            new_meal_data = {}
        
        # Пересчитываем список покупок для обновленного рецепта
        sklad = load_sklad()
        needed_products = analyze_ingredients(updated_recipe, sklad)
        
        return jsonify({
            'success': True, 
            'message': f'Блюдо для {meal_type} заменено на: {meal_name}',
            'new_meal_data': new_meal_data,
            'needed_products': needed_products
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/cook_meal', methods=['POST'])
def api_cook_meal():
    """API endpoint для удаления продуктов после приготовления"""
    try:
        data = request.get_json()
        meal_name = data.get('meal_name')
        
        # Загружаем текущий смешанный рецепт
        recipe = get_mixed_recipe()
        if not recipe:
            return jsonify({'error': 'Не удалось загрузить рецепт'}), 500
        
        # Находим ингредиенты для указанного приема пищи
        if meal_name in recipe['меню']:
            meal_data = recipe['меню'][meal_name]
            
            if db.consume_ingredients_for_meal(meal_name, meal_data):
                return jsonify({'success': True, 'message': f'Блюдо "{meal_name}" приготовлено! Продукты удалены со склада'})
            else:
                return jsonify({'error': 'Ошибка при обновлении склада'}), 500
        else:
            return jsonify({'error': 'Блюдо не найдено в рецепте'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === API ENDPOINTS ДЛЯ УПРАВЛЕНИЯ РЕЦЕПТАМИ ===

@app.route('/api/recipes')
def api_get_all_recipes():
    """API endpoint для получения списка всех рецептов"""
    try:
        query = request.args.get('query', '').strip()
        meal_type = request.args.get('meal_type', '').strip()
        
        if query or meal_type:
            recipes = db.search_recipes(query if query else None, meal_type if meal_type else None)
        else:
            recipes = db.get_all_recipes_with_info()
        
        return jsonify({
            'success': True,
            'recipes': recipes,
            'total': len(recipes)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<int:recipe_id>')
def api_get_recipe(recipe_id):
    """API endpoint для получения конкретного рецепта"""
    try:
        recipe = db.get_recipe_by_id(recipe_id)
        if recipe:
            return jsonify({
                'success': True,
                'recipe': recipe
            })
        else:
            return jsonify({'error': 'Рецепт не найден'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<int:recipe_id>', methods=['PUT'])
def api_update_recipe(recipe_id):
    """API endpoint для обновления рецепта"""
    try:
        data = request.get_json()
        meal_data = data.get('meal_data', {})
        
        # Базовая валидация
        if not meal_data.get('блюдо', '').strip():
            return jsonify({'error': 'Не указано название блюда'}), 400
        
        if 'ингредиенты' not in meal_data or not meal_data['ингредиенты']:
            return jsonify({'error': 'Нужно указать хотя бы один ингредиент'}), 400
        
        if db.update_recipe(recipe_id, meal_data):
            return jsonify({
                'success': True,
                'message': f'Рецепт "{meal_data["блюдо"]}" обновлен'
            })
        else:
            return jsonify({'error': 'Рецепт не найден или ошибка обновления'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/recipes/<int:recipe_id>', methods=['DELETE'])
def api_delete_recipe(recipe_id):
    """API endpoint для удаления рецепта"""
    try:
        # Сначала получаем информацию о рецепте для сообщения
        recipe = db.get_recipe_by_id(recipe_id)
        if not recipe:
            return jsonify({'error': 'Рецепт не найден'}), 404
        
        recipe_name = recipe['название']
        
        if db.delete_recipe(recipe_id):
            return jsonify({
                'success': True,
                'message': f'Рецепт "{recipe_name}" удален'
            })
        else:
            return jsonify({'error': 'Ошибка при удалении рецепта'}), 500
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# === СТРАНИЦЫ ===


@app.route('/recipes')
def manage_recipes():
    """Страница управления рецептами"""
    return render_template('manage_recipes.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8081)
