from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from config import (
    BOT_TOKEN, CHANNEL_ID, ADMIN_ID, DB_URL,
    SUBSCRIPTION_SETTINGS, PAYMENT_METHODS
)
from keyboards import get_payment_keyboard, get_admin_keyboard, get_admin_main_keyboard, get_crypto_payment_keyboard, get_crypto_currency_keyboard, get_payment_method_keyboard
from db import create_pool, init_db, add_subscription, check_expired_subscriptions, add_user, get_all_users, get_expiring_subscriptions, get_user_subscriptions
from crypto_pay import CryptoPayAPI
from aiogram.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import aioschedule

# ID бота @CryptoBot для проверки вебхуков
CRYPTO_BOT_ID = 1559501630

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Создаем пул соединений с базой данных
pool = None
crypto_pay = CryptoPayAPI()

class PaymentStates(StatesGroup):
    waiting_for_payment = State()
    waiting_for_amount = State()
    waiting_for_confirmation = State()
    waiting_for_crypto_amount = State()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()

def get_price(duration: str) -> float:
    return SUBSCRIPTION_SETTINGS[duration]['price']

def get_price_label(duration: str) -> LabeledPrice:
    settings = SUBSCRIPTION_SETTINGS[duration]
    return LabeledPrice(
        label=f"Подписка на {settings['name'].lower()}",
        amount=settings['price']
    )

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    global pool
    # Сохраняем пользователя в базу
    await add_user(pool, message.from_user)
    
    await message.answer(
        "Добро пожаловать! Выберите срок подписки:",
        reply_markup=get_payment_keyboard()
    )

@dp.callback_query_handler(lambda c: c.data.startswith('duration_'))
async def process_duration_selection(callback_query: types.CallbackQuery, state: FSMContext):
    duration = callback_query.data.split('_')[1]
    await state.update_data(duration=duration)
    price = get_price(duration)
    
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer(
        f"Стоимость подписки: {price}₽\n"
        f"Выберите способ оплаты:",
        reply_markup=get_payment_method_keyboard(duration)
    )

@dp.callback_query_handler(lambda c: c.data.startswith('tg_stars_'))
async def process_tg_stars(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    duration = callback_query.data.split('_')[2]  # tg_stars_month/year/forever
    
    price = get_price_label(duration)
    
    await bot.send_invoice(
        chat_id=callback_query.from_user.id,
        title=f'Подписка на приватный канал ({duration})',
        description='Оплата доступа к приватному каналу',
        payload=f'channel_subscription_{duration}',
        provider_token='YOUR_PROVIDER_TOKEN',
        currency='RUB',
        prices=[price],
        start_parameter='subscription',
        protect_content=True
    )

@dp.pre_checkout_query_handler()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    global pool
    duration = message.successful_payment.invoice_payload.split('_')[2]
    await add_subscription(
        pool,
        message.from_user.id,
        duration,
        'tg_stars',
        float(message.successful_payment.total_amount) / 100
    )
    
    await bot.approve_chat_join_request(CHANNEL_ID, message.from_user.id)
    
    duration_text = {
        'month': 'месяц',
        'year': 'год',
        'forever': 'неограниченный срок'
    }
    
    await bot.send_message(
        message.from_user.id,
        f"Спасибо за оплату! Доступ к каналу открыт на {duration_text[duration]}."
    )

@dp.callback_query_handler(lambda c: c.data.startswith('p2p_'))
async def process_p2p(callback_query: types.CallbackQuery, state: FSMContext):
    duration = callback_query.data.split('_')[1]
    price = get_price(duration)
    await state.update_data(duration=duration, amount=price)
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer(
        f"Переведите {price}₽ на карту: {PAYMENT_METHODS['p2p']['card_number']}\n"
        "После перевода нажмите кнопку 'Я оплатил'"
    )
    await PaymentStates.waiting_for_payment.set()
    
    # Уведомление админу
    await bot.send_message(
        ADMIN_ID,
        f"Новый запрос на оплату:\nПользователь: {callback_query.from_user.id}\n"
        f"Сумма: {price}₽\nДлительность: {duration}",
        reply_markup=get_admin_keyboard(callback_query.from_user.id)
    )

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_'))
async def confirm_payment(callback_query: types.CallbackQuery, state: FSMContext):
    global pool
    user_id = int(callback_query.data.split('_')[1])
    
    # Получаем данные из состояния
    data = await state.get_data()
    amount = data.get('amount', 0)
    
    # Определяем тип подписки на основе суммы
    if amount >= 500:
        duration = 'forever'
    elif amount >= 100:
        duration = 'year'
    else:
        duration = 'month'
    
    await add_subscription(
        pool,
        user_id,
        duration,
        'p2p',
        amount
    )
    
    # Добавляем пользователя в канал
    await bot.approve_chat_join_request(CHANNEL_ID, user_id)
    
    duration_text = {
        'month': 'месяц',
        'year': 'год',
        'forever': 'неограниченный срок'
    }
    
    await bot.send_message(
        user_id,
        f"Ваша оплата подтверждена! Доступ к каналу открыт на {duration_text[duration]}."
    )
    await bot.answer_callback_query(callback_query.id)
    
    # Очищаем состояние
    await state.finish()

@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if str(message.from_user.id) == ADMIN_ID:
        await message.answer(
            "Панель администратора:",
            reply_markup=get_admin_main_keyboard()
        )

@dp.callback_query_handler(lambda c: c.data == 'create_broadcast')
async def create_broadcast(callback_query: types.CallbackQuery):
    if str(callback_query.from_user.id) == ADMIN_ID:
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(
            callback_query.from_user.id,
            "Отправьте сообщение для рассылки (можно использовать текст, фото, видео):"
        )
        await BroadcastStates.waiting_for_message.set()

@dp.message_handler(state=BroadcastStates.waiting_for_message, content_types=types.ContentTypes.ANY)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    if str(message.from_user.id) != ADMIN_ID:
        return
    
    global pool
    users = await get_all_users(pool)
    
    sent = 0
    failed = 0
    
    await message.answer("Начинаю рассылку...")
    
    for user_id in users:
        try:
            if message.content_type == 'text':
                await bot.send_message(user_id, message.text)
            elif message.content_type == 'photo':
                await bot.send_photo(
                    user_id,
                    message.photo[-1].file_id,
                    caption=message.caption
                )
            elif message.content_type == 'video':
                await bot.send_video(
                    user_id,
                    message.video.file_id,
                    caption=message.caption
                )
            sent += 1
            await asyncio.sleep(0.05)  # Небольшая задержка между отправками
        except Exception as e:
            failed += 1
            print(f"Failed to send message to {user_id}: {e}")
    
    await message.answer(
        f"Рассылка завершена!\n"
        f"Успешно отправлено: {sent}\n"
        f"Ошибок: {failed}"
    )
    await state.finish()

async def check_subscriptions():
    global pool
    # Проверяем подписки, истекающие через неделю
    week_expiring = await get_expiring_subscriptions(pool, 7)
    for user_id, end_date in week_expiring:
        try:
            await bot.send_message(
                user_id,
                f"⚠️ Ваша подписка истекает через неделю - {end_date.strftime('%d.%m.%Y')}.\n"
                "Не забудьте продлить подписку, чтобы сохранить доступ к каналу!"
            )
        except Exception as e:
            print(f"Error sending week notification to user {user_id}: {e}")
    
    # Проверяем подписки, истекающие через сутки
    day_expiring = await get_expiring_subscriptions(pool, 1)
    for user_id, end_date in day_expiring:
        try:
            await bot.send_message(
                user_id,
                f"⚠️ Ваша подписка истекает через 24 часа - {end_date.strftime('%d.%m.%Y')}.\n"
                "Продлите подписку сейчас, чтобы не потерять доступ к каналу!",
                reply_markup=get_payment_keyboard()
            )
        except Exception as e:
            print(f"Error sending day notification to user {user_id}: {e}")
    
    # Проверяем истекшие подписки
    expired_users = await check_expired_subscriptions(pool)
    for user_id in expired_users:
        try:
            await bot.ban_chat_member(
                chat_id=CHANNEL_ID,
                user_id=user_id,
                until_date=0
            )
            await bot.send_message(
                user_id,
                "❌ Ваша подписка истекла. Для восстановления доступа оформите новую подписку.",
                reply_markup=get_payment_keyboard()
            )
        except Exception as e:
            print(f"Error removing user {user_id}: {e}")

async def scheduler():
    # Проверяем подписки каждый час
    aioschedule.every().hour.at(":00").do(check_subscriptions)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(3600)  # проверка каждый час

async def on_startup(dispatcher: Dispatcher):
    global pool
    # Создаем пул соединений с базой данных
    pool = await create_pool()
    
    # Инициализируем базу данных
    await init_db(pool)
    
    # Устанавливаем команды бота
    await bot.set_my_commands([
        types.BotCommand("start", "Начать работу с ботом"),
        types.BotCommand("subscriptions", "Мои подписки"),
        types.BotCommand("admin", "Панель администратора")
    ])
    
    # Сохраняем пул в диспетчере бота для доступа из хендлеров
    dispatcher["db_pool"] = pool
    
    # Запускаем планировщик
    asyncio.create_task(scheduler())

@dp.callback_query_handler(lambda c: c.data.startswith('crypto_'))
async def process_crypto_payment(callback_query: types.CallbackQuery, state: FSMContext):
    duration = callback_query.data.split('_')[1]
    await state.update_data(duration=duration)
    await bot.answer_callback_query(callback_query.id)
    
    price = get_price(duration)
    await callback_query.message.answer(
        f"Стоимость подписки: {price}₽\n"
        f"Выберите криптовалюту для оплаты:",
        reply_markup=get_crypto_currency_keyboard(duration)
    )

@dp.callback_query_handler(lambda c: c.data.startswith('crypto_pay_'))
async def process_crypto_currency_selected(callback_query: types.CallbackQuery, state: FSMContext):
    _, _, asset, duration = callback_query.data.split('_')
    price = get_price(duration)
    
    await state.update_data(crypto_asset=asset, amount=price)
    await bot.answer_callback_query(callback_query.id)

    # Создаем инвойс
    invoice = await crypto_pay.create_invoice(
        amount=price,
        asset=asset,
        description=f"Подписка на канал на {duration} ({asset})"
    )

    if invoice.get('ok'):
        invoice_data = invoice['result']
        await callback_query.message.answer(
            f"Оплатите {price} {asset} по ссылке:\n"
            f"{invoice_data['bot_invoice_url']}\n\n"
            "После оплаты вы автоматически получите доступ к каналу."
        )
        
        # Сохраняем invoice_id для проверки статуса
        await state.update_data(invoice_id=invoice_data['invoice_id'])
        
    else:
        await callback_query.message.answer("Произошла ошибка при создании платежа. Попробуйте позже.")

@dp.message_handler(content_types=types.ContentTypes.ANY, state='*')
async def process_crypto_webhook(message: types.Message):
    try:
        if message.from_user.id == CRYPTO_BOT_ID:  # ID @CryptoBot
            data = message.get_json()
            if data.get('status') == 'paid':
                invoice_id = data.get('invoice_id')
                
                # Получаем информацию об инвойсе
                invoice = await crypto_pay.get_invoice(invoice_id)
                if invoice:
                    user_id = invoice['user_id']
                    amount = float(invoice['amount'])
                    
                    # Определяем длительность подписки по сумме
                    duration = None
                    for dur, price in SUBSCRIPTION_SETTINGS.items():
                        if abs(price['price'] - amount) < 0.01:  # Учитываем возможную погрешность
                            duration = dur
                            break
                    
                    if duration:
                        await add_subscription(
                            pool,
                            user_id,
                            duration,
                            'crypto',
                            amount
                        )
                        
                        await bot.approve_chat_join_request(CHANNEL_ID, user_id)
                        
                        duration_text = {
                            'month': 'месяц',
                            'year': 'год',
                            'forever': 'неограниченный срок'
                        }
                        
                        await bot.send_message(
                            user_id,
                            f"Оплата получена! Доступ к каналу открыт на {duration_text[duration]}."
                        )
    except Exception as e:
        print(f"Error processing crypto webhook: {e}")

@dp.callback_query_handler(lambda c: c.data == 'my_subscriptions')
async def show_subscriptions(callback_query: types.CallbackQuery):
    global pool
    subscriptions = await get_user_subscriptions(pool, callback_query.from_user.id)
    
    if not subscriptions:
        await callback_query.message.answer(
            "У вас пока нет подписок. Выберите тариф для оформления:",
            reply_markup=get_payment_keyboard()
        )
        await bot.answer_callback_query(callback_query.id)
        return
    
    # Формируем сообщение со списком подписок
    message_text = "📋 Ваши подписки:\n\n"
    
    for sub in subscriptions:
        status_emoji = "✅" if sub['status'] == 'active' else "❌"
        payment_method_text = {
            'tg_stars': 'Картой',
            'p2p': 'Переводом',
            'crypto': 'Криптовалютой'
        }.get(sub['payment_method'], sub['payment_method'])
        
        message_text += (
            f"{status_emoji} {sub['subscription_type'].capitalize()}\n"
            f"💰 Оплачено: {sub['amount']}₽\n"
            f"💳 Способ оплаты: {payment_method_text}\n"
            f"📅 Дата начала: {sub['start_date'].strftime('%d.%m.%Y')}\n"
        )
        
        if sub['end_date']:
            if sub['status'] == 'active':
                message_text += f"⏳ Осталось дней: {sub['days_left']}\n"
                message_text += f"📅 Дата окончания: {sub['end_date'].strftime('%d.%m.%Y')}\n"
            else:
                message_text += f"❌ Истекла: {sub['end_date'].strftime('%d.%m.%Y')}\n"
        else:
            message_text += "♾️ Бессрочная подписка\n"
        
        message_text += "\n"
    
    # Добавляем кнопку продления, если есть активная подписка
    has_active = any(sub['status'] == 'active' for sub in subscriptions)
    keyboard = InlineKeyboardMarkup()
    if has_active:
        keyboard.add(InlineKeyboardButton("🔄 Продлить подписку", callback_data="duration_month"))
    else:
        keyboard.add(InlineKeyboardButton("📝 Оформить подписку", callback_data="duration_month"))
    
    await callback_query.message.answer(message_text, reply_markup=keyboard)
    await bot.answer_callback_query(callback_query.id)

@dp.message_handler(commands=['subscriptions'])
async def subscriptions_command(message: types.Message):
    # Переиспользуем логику из callback-хендлера
    callback_query = types.CallbackQuery(
        id='0',
        from_user=message.from_user,
        chat_instance='0',
        message=message,
        data='my_subscriptions'
    )
    await show_subscriptions(callback_query)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup) 