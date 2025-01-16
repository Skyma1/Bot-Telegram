# Telegram Бот для Управления Подпиской на Приватный Канал

## Описание
Бот для организации платного доступа к приватному Telegram-каналу с возможностью оплаты через Telegram Payments и P2P-переводы.

## Подготовка к установке

### 1. Установка Python
1. Скачайте Python версии 3.8 или выше:
   - Windows: [Python для Windows](https://www.python.org/downloads/windows/)
   - Linux: `sudo apt-get install python3`
   - macOS: [Python для macOS](https://www.python.org/downloads/macos/)

2. При установке на Windows обязательно поставьте галочку "Add Python to PATH"

### 2. Установка PostgreSQL
1. Скачайте PostgreSQL:
   - Windows: [Установщик PostgreSQL](https://www.enterprisedb.com/downloads/postgres-postgresql-downloads)
   - Linux: `sudo apt-get install postgresql postgresql-contrib`
   - macOS: [PostgreSQL для macOS](https://www.postgresql.org/download/macosx/)

2. Запомните пароль, который вы укажете при установке

## Настройка проекта

### 1. Создание базы данных
Откройте терминал (командную строку):

#### Windows:

Перейдите в папку с PostgreSQL

```bash
cd "C:\Program Files\PostgreSQL\17\bin"
```

Запустите psql

```bash
psql -U postgres
```

**Linux/Mac:**
```bash
sudo -u postgres psql
```

Выполните следующие команды SQL:
```sql
CREATE USER bot_user WITH PASSWORD 'your_password';
CREATE DATABASE telegram_bot;
GRANT ALL PRIVILEGES ON DATABASE telegram_bot TO bot_user;
\c telegram_bot
GRANT ALL ON SCHEMA public TO bot_user;
\q
```

### 4. Установка зависимостей

Откройте командную строку в папке с ботом и выполните:
```bash
pip install -r requirements.txt
```

### 5. Настройка конфигурации

1. Откройте файл `config.py`
2. Заполните следующие параметры:
   ```python
   BOT_TOKEN = "YOUR_BOT_TOKEN"  # Получите у @BotFather
   CHANNEL_ID = "YOUR_CHANNEL_ID"  # ID вашего приватного канала
   ADMIN_ID = "YOUR_ADMIN_ID"  # Ваш Telegram ID
   DB_URL = "postgresql://bot_user:your_password@localhost/telegram_bot"  # Замените your_password на пароль, который вы указали при создании базы данных
   PROVIDER_TOKEN = "YOUR_PROVIDER_TOKEN"  # Токен от Telegram Payments (получите у @BotFather)
   ```requirements.txt

### 6. Настройка канала

1. Создайте приватный канал в Telegram
2. Добавьте бота в администраторы канала
3. Включите обязательное подтверждение новых подписчиков
4. Скопируйте ID канала (можно получить, переслав любое сообщение боту @getidsbot)

## Запуск бота

1. Откройте командную строку в папке с ботом
2. Выполните команду:
```bash
python bot.py
```

## Использование

### Для пользователей
1. Запустите бота командой /start
2. Выберите тип подписки
3. Оплатите удобным способом
4. После успешной оплаты вы получите доступ к каналу

### Для администратора
1. Отправьте команду /admin
2. Доступные функции:
   - Подтверждение P2P платежей
   - Создание рассылок всем пользователям

## Возможные проблемы

### Ошибка подключения к базе данных
- Проверьте правильность данных в DB_URL
- Убедитесь, что PostgreSQL запущен
- Проверьте правильность создания пользователя и базы данных

### Ошибка при запуске бота
- Проверьте, что все токены в config.py указаны правильно
- Убедитесь, что бот добавлен в администраторы канала

## Требования
- Python 3.8+
- PostgreSQL 12+
- Операционная система: Windows/Linux/MacOS

## Дополнительная информация

Для работы с Telegram Payments необходимо:
1. Получить токен у @BotFather через команду /payments
2. Настроить платежную систему через @BotFather
3. Указать PROVIDER_TOKEN в config.py

### Настройка Crypto Pay

1. Откройте @CryptoBot
2. Перейдите в Crypto Pay
3. Нажмите Create App
4. Получите API токен и укажите его в CRYPTO_PAY_TOKEN
5. В настройках приложения включите Webhooks и укажите URL вашего сервера

## Поддержка

Если у вас возникли проблемы:
1. Проверьте наличие всех необходимых зависимостей
2. Убедитесь, что все настройки указаны правильно
3. Проверьте права доступа к базе данных