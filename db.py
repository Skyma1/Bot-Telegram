import aiosqlite
import asyncio
from datetime import datetime, timedelta
from aiogram import types
import os

DB_PATH = 'bot_database.db'

async def create_pool():
    # В SQLite не нужен пул соединений, возвращаем путь к базе
    return DB_PATH

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # Создаем таблицу подписок
        await db.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP,
                subscription_type TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                amount REAL NOT NULL
            )
        ''')
        
        # Создаем таблицу пользователей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем таблицу платежей
        await db.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES subscriptions(user_id)
            )
        ''')
        await db.commit()

async def add_subscription(db_path, user_id: int, duration: str, payment_method: str, amount: float):
    now = datetime.now()
    
    if duration == 'month':
        end_date = now + timedelta(days=30)
    elif duration == 'year':
        end_date = now + timedelta(days=365)
    elif duration == 'forever':
        end_date = None
    else:
        raise ValueError("Invalid duration")
    
    async with aiosqlite.connect(db_path) as db:
        # Добавляем или обновляем подписку
        await db.execute('''
            INSERT OR REPLACE INTO subscriptions 
            (user_id, start_date, end_date, subscription_type, payment_method, amount)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, now, end_date, duration, payment_method, amount))
        
        # Записываем платёж
        await db.execute('''
            INSERT INTO payments (user_id, amount, status, payment_method, completed_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, amount, 'completed', payment_method, now))
        
        await db.commit()

async def get_expiring_subscriptions(db_path, days_left: int):
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        date_check = datetime.now() + timedelta(days=days_left)
        
        query = '''
            SELECT user_id, end_date 
            FROM subscriptions 
            WHERE end_date IS NOT NULL 
            AND end_date <= ?
            AND end_date > ?
        '''
        
        async with db.execute(query, (date_check, datetime.now())) as cursor:
            rows = await cursor.fetchall()
            return [(row['user_id'], datetime.fromisoformat(row['end_date'])) for row in rows]

async def check_expired_subscriptions(db_path):
    async with aiosqlite.connect(db_path) as db:
        now = datetime.now()
        async with db.execute('''
            SELECT user_id FROM subscriptions 
            WHERE end_date IS NOT NULL AND end_date < ?
        ''', (now,)) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def add_user(db_path, user: types.User):
    async with aiosqlite.connect(db_path) as db:
        await db.execute('''
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (user.id, user.username, user.first_name, user.last_name))
        await db.commit()

async def get_all_users(db_path):
    async with aiosqlite.connect(db_path) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def get_user_subscriptions(db_path, user_id: int):
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT 
                subscription_type,
                payment_method,
                start_date,
                end_date,
                amount,
                CASE 
                    WHEN end_date IS NULL THEN 'active'
                    WHEN end_date < CURRENT_TIMESTAMP THEN 'expired'
                    ELSE 'active'
                END as status,
                CASE 
                    WHEN end_date IS NULL THEN NULL
                    WHEN end_date < CURRENT_TIMESTAMP THEN NULL
                    ELSE (julianday(end_date) - julianday(CURRENT_TIMESTAMP))
                END as days_left
            FROM subscriptions 
            WHERE user_id = ?
            ORDER BY start_date DESC
        ''', (user_id,)) as cursor:
            return await cursor.fetchall() 