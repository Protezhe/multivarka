#!/bin/bash

# Скрипт для запуска веб-сервера управления складом
# Автоматически создает виртуальное окружение, устанавливает зависимости и запускает сервер

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

print_message "🚀 Запуск веб-сервера управления складом..."

# Проверяем наличие Python3
if ! command -v python3 &> /dev/null; then
    print_error "Python3 не найден! Установите Python3 для продолжения."
    exit 1
fi

print_success "Python3 найден: $(python3 --version)"

# Проверяем наличие venv модуля
if ! python3 -c "import venv" 2>/dev/null; then
    print_warning "Модуль venv не найден. Устанавливаем python3-venv..."
    
    # Определяем дистрибутив Linux
    if command -v apt-get &> /dev/null; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y python3-venv
    elif command -v yum &> /dev/null; then
        # CentOS/RHEL
        sudo yum install -y python3-venv
    elif command -v dnf &> /dev/null; then
        # Fedora
        sudo dnf install -y python3-venv
    elif command -v pacman &> /dev/null; then
        # Arch Linux
        sudo pacman -S python-venv
    elif command -v zypper &> /dev/null; then
        # openSUSE
        sudo zypper install python3-venv
    else
        print_error "Не удалось определить дистрибутив Linux для установки python3-venv"
        print_error "Установите python3-venv вручную и запустите скрипт снова"
        exit 1
    fi
    
    print_success "python3-venv установлен"
fi

# Проверяем наличие виртуального окружения
if [ ! -d "venv" ]; then
    print_message "Создаем виртуальное окружение..."
    python3 -m venv venv
    print_success "Виртуальное окружение создано"
else
    print_success "Виртуальное окружение уже существует"
fi

# Активируем виртуальное окружение
print_message "Активируем виртуальное окружение..."
source venv/bin/activate

# Обновляем pip
print_message "Обновляем pip..."
pip install --upgrade pip

# Проверяем наличие requirements.txt
if [ ! -f "requirements.txt" ]; then
    print_error "Файл requirements.txt не найден!"
    print_error "Создайте файл requirements.txt с зависимостями проекта"
    exit 1
fi

# Устанавливаем зависимости
print_message "Устанавливаем зависимости из requirements.txt..."
pip install -r requirements.txt

print_success "Все зависимости установлены"

# Проверяем наличие файла запуска
if [ ! -f "warehouse_web/run.py" ]; then
    print_error "Файл warehouse_web/run.py не найден!"
    exit 1
fi

# Проверяем, не запущен ли уже сервер
if pgrep -f "warehouse_web/run.py" > /dev/null; then
    print_warning "Сервер уже запущен!"
    print_message "Для остановки используйте: ./stop_server.sh"
    exit 1
fi

# Запускаем сервер в фоновом режиме
print_message "Запускаем веб-сервер..."
nohup python warehouse_web/run.py > server.log 2>&1 &
SERVER_PID=$!

# Сохраняем PID сервера
echo $SERVER_PID > server.pid

# Ждем немного, чтобы сервер успел запуститься
sleep 2

# Проверяем, что сервер запустился
if ps -p $SERVER_PID > /dev/null; then
    print_success "✅ Сервер успешно запущен!"
    print_success "📱 Откройте браузер и перейдите по адресу: http://localhost:8080"
    print_success "📋 Логи сервера: server.log"
    print_success "🆔 PID сервера: $SERVER_PID"
    print_message "⏹️  Для остановки сервера используйте: ./stop_server.sh"
else
    print_error "❌ Не удалось запустить сервер"
    print_error "Проверьте логи в файле server.log"
    exit 1
fi
