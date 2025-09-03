#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для запуска веб-сервера управления складом
"""

import os
import sys

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print("🚀 Запуск веб-сервера управления складом...")
    print("📱 Откройте браузер и перейдите по адресу: http://localhost:8080")
    print("⏹️  Для остановки сервера нажмите Ctrl+C")
    print("-" * 50)
    
    try:
        app.run(debug=True, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        print("\n👋 Сервер остановлен")
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
