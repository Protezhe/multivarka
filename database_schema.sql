-- Схема базы данных SQLite для проекта мультиварки

-- Таблица склада (warehouse)
CREATE TABLE IF NOT EXISTS warehouse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL UNIQUE,
    quantity REAL NOT NULL DEFAULT 0,
    unit TEXT NOT NULL,
    product_type TEXT NOT NULL DEFAULT 'quantity', -- 'quantity' или 'availability'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица рецептов (recipes) - каждый рецепт это один прием пищи (single format)
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,  -- название блюда
    meal_type TEXT NOT NULL,  -- завтрак, второй_завтрак, обед, полдник, ужин
    is_ready BOOLEAN DEFAULT FALSE,  -- готово ли блюдо
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица ингредиентов рецептов
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT NOT NULL,
    ingredient_type TEXT NOT NULL DEFAULT 'quantity', -- 'quantity' или 'availability'
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- Таблица инструкций рецептов
CREATE TABLE IF NOT EXISTS recipe_instructions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_id INTEGER NOT NULL,
    step_number INTEGER NOT NULL,
    instruction TEXT NOT NULL,
    FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
);

-- Таблица для хранения текущего рецепта (только один активный рецепт)
CREATE TABLE IF NOT EXISTS current_recipe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipe_data TEXT NOT NULL,  -- JSON данные текущего рецепта
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_recipes_meal_type ON recipes(meal_type);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe_id ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_product ON recipe_ingredients(product_name);
CREATE INDEX IF NOT EXISTS idx_recipe_instructions_recipe_id ON recipe_instructions(recipe_id);
CREATE INDEX IF NOT EXISTS idx_warehouse_product ON warehouse(product_name);

-- Триггеры для автоматического обновления updated_at
CREATE TRIGGER IF NOT EXISTS update_warehouse_timestamp 
    AFTER UPDATE ON warehouse
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE warehouse SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_recipes_timestamp 
    AFTER UPDATE ON recipes
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE recipes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
