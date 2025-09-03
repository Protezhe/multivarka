#!/bin/bash

# Скрипт для остановки веб-сервера управления складом

set -e  # Остановить выполнение при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
print_message() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Получаем директорию скрипта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_message "⏹️  Остановка веб-сервера управления складом..."

# Проверяем наличие файла с PID
if [ -f "server.pid" ]; then
    SERVER_PID=$(cat server.pid)
    print_message "Найден PID сервера: $SERVER_PID"
    
    # Проверяем, что процесс действительно запущен
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        print_message "Останавливаем сервер (PID: $SERVER_PID)..."
        
        # Пытаемся корректно остановить сервер
        kill $SERVER_PID
        
        # Ждем до 10 секунд для корректного завершения
        for i in {1..10}; do
            if ! ps -p $SERVER_PID > /dev/null 2>&1; then
                print_success "✅ Сервер успешно остановлен"
                rm -f server.pid
                break
            fi
            sleep 1
        done
        
        # Если процесс все еще работает, принудительно завершаем
        if ps -p $SERVER_PID > /dev/null 2>&1; then
            print_warning "Принудительно завершаем процесс..."
            kill -9 $SERVER_PID
            sleep 1
            
            if ! ps -p $SERVER_PID > /dev/null 2>&1; then
                print_success "✅ Сервер принудительно остановлен"
                rm -f server.pid
            else
                print_error "❌ Не удалось остановить сервер"
                exit 1
            fi
        fi
    else
        print_warning "Процесс с PID $SERVER_PID не найден"
        rm -f server.pid
    fi
else
    print_warning "Файл server.pid не найден"
fi

# Дополнительная проверка - ищем процессы по имени файла
WAREHOUSE_PROCESSES=$(pgrep -f "warehouse_web/run.py" || true)

if [ -n "$WAREHOUSE_PROCESSES" ]; then
    print_message "Найдены дополнительные процессы сервера: $WAREHOUSE_PROCESSES"
    print_message "Останавливаем их..."
    
    for pid in $WAREHOUSE_PROCESSES; do
        print_message "Останавливаем процесс $pid..."
        kill $pid 2>/dev/null || true
    done
    
    # Ждем немного
    sleep 2
    
    # Проверяем, остались ли процессы
    REMAINING_PROCESSES=$(pgrep -f "warehouse_web/run.py" || true)
    if [ -n "$REMAINING_PROCESSES" ]; then
        print_warning "Принудительно завершаем оставшиеся процессы..."
        for pid in $REMAINING_PROCESSES; do
            kill -9 $pid 2>/dev/null || true
        done
    fi
    
    print_success "✅ Все процессы сервера остановлены"
else
    print_message "Дополнительные процессы сервера не найдены"
fi

# Очищаем временные файлы
if [ -f "server.pid" ]; then
    rm -f server.pid
fi

print_success "🎉 Веб-сервер полностью остановлен"
print_message "📋 Логи сервера сохранены в файле server.log"
