import asyncpg
from datetime import datetime, timedelta
from config import DB_URL
import asyncio
from aiogram import types

async def create_pool():
    return await asyncpg.create_pool(DB_URL)

async def init_db(pool):
    async with pool.acquire() as conn:
        # Создаем таблицу подписок
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id BIGINT PRIMARY KEY,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP,
                subscription_type VARCHAR(10) NOT NULL,
                payment_method VARCHAR(10) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL
            )
        ''')
        
        # Создаем таблицу всех пользователей бота
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                joined_date TIMESTAMP NOT NULL DEFAULT NOW()
            )
        ''')
        
        # Создаем таблицу платежей
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                payment_id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                status VARCHAR(20) NOT NULL,
                payment_method VARCHAR(10) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES subscriptions(user_id)
            )
        ''')

async def add_subscription(pool, user_id: int, duration: str, payment_method: str, amount: float):
    now = datetime.now()
    
    if duration == 'month':
        end_date = now + timedelta(days=30)
    elif duration == 'year':
        end_date = now + timedelta(days=365)
    elif duration == 'forever':
        end_date = None
    else:
        raise ValueError("Invalid duration")
    
    async with pool.acquire() as conn:
        # Добавляем или обновляем подписку
        await conn.execute('''
            INSERT INTO subscriptions (user_id, start_date, end_date, subscription_type, payment_method, amount)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id) DO UPDATE 
            SET start_date = $2,
                end_date = $3,
                subscription_type = $4,
                payment_method = $5,
                amount = $6
        ''', user_id, now, end_date, duration, payment_method, amount)
        
        # Записываем платёж
        await conn.execute('''
            INSERT INTO payments (user_id, amount, status, payment_method, completed_at)
            VALUES ($1, $2, $3, $4, $5)
        ''', user_id, amount, 'completed', payment_method, now)

async def get_expiring_subscriptions(pool, days_left: int):
    """
    Получает список пользователей, у которых подписка истекает через указанное количество дней
    """
    async with pool.acquire() as conn:
        expiring = await conn.fetch('''
            SELECT user_id, end_date 
            FROM subscriptions 
            WHERE end_date IS NOT NULL 
            AND end_date > NOW() 
            AND end_date <= NOW() + interval '1 day' * $1
            AND end_date > NOW() + interval '1 day' * ($1 - 1)
        ''', days_left)
        return [(record['user_id'], record['end_date']) for record in expiring]

async def check_expired_subscriptions(pool):
    async with pool.acquire() as conn:
        expired = await conn.fetch('''
            SELECT user_id FROM subscriptions 
            WHERE end_date IS NOT NULL AND end_date < NOW()
        ''')
        return [record['user_id'] for record in expired]

async def is_active_subscription(pool, user_id: int) -> bool:
    async with pool.acquire() as conn:
        sub = await conn.fetchrow('''
            SELECT * FROM subscriptions 
            WHERE user_id = $1 
            AND (end_date IS NULL OR end_date > NOW())
        ''', user_id)
        return bool(sub)

async def add_pending_payment(pool, user_id: int, amount: float, payment_method: str):
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO payments (user_id, amount, status, payment_method)
            VALUES ($1, $2, $3, $4)
        ''', user_id, amount, 'pending', payment_method)

async def confirm_payment(pool, user_id: int, payment_id: int):
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE payments 
            SET status = 'completed', completed_at = NOW()
            WHERE payment_id = $1 AND user_id = $2
        ''', payment_id, user_id) 

async def add_user(pool, user: types.User):
    async with pool.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE 
            SET username = $2,
                first_name = $3,
                last_name = $4
        ''', user.id, user.username, user.first_name, user.last_name)

async def get_all_users(pool):
    async with pool.acquire() as conn:
        users = await conn.fetch('SELECT user_id FROM users')
        return [record['user_id'] for record in users]

async def get_user_subscriptions(pool, user_id: int):
    """
    Получает все подписки пользователя с информацией о статусе
    """
    async with pool.acquire() as conn:
        subscriptions = await conn.fetch('''
            SELECT 
                subscription_type,
                payment_method,
                start_date,
                end_date,
                amount,
                CASE 
                    WHEN end_date IS NULL THEN 'active'
                    WHEN end_date < NOW() THEN 'expired'
                    ELSE 'active'
                END as status,
                CASE 
                    WHEN end_date IS NULL THEN NULL
                    WHEN end_date < NOW() THEN NULL
                    ELSE EXTRACT(DAY FROM (end_date - NOW()))::integer
                END as days_left
            FROM subscriptions 
            WHERE user_id = $1 
            ORDER BY start_date DESC
        ''', user_id)
        return subscriptions

async def test_connection():
    try:
        conn = await asyncpg.connect('postgresql://bot_user:your_password@localhost/telegram_bot')
        await conn.close()
        print("Подключение успешно!")
    except Exception as e:
        print(f"Ошибка подключения: {e}")

asyncio.run(test_connection()) 