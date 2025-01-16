from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import SUBSCRIPTION_SETTINGS, PAYMENT_METHODS

def get_payment_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📋 Мои подписки", callback_data="my_subscriptions"))
    for duration, settings in SUBSCRIPTION_SETTINGS.items():
        keyboard.add(InlineKeyboardButton(
            f"{settings['emoji']} {settings['name']} - {settings['price']}₽",
            callback_data=f"duration_{duration}"
        ))
    return keyboard

def get_payment_method_keyboard(duration: str):
    keyboard = InlineKeyboardMarkup()
    for method, settings in PAYMENT_METHODS.items():
        keyboard.add(InlineKeyboardButton(
            f"{settings['emoji']} {settings['name']}",
            callback_data=f"{method}_{duration}"
        ))
    return keyboard

def get_admin_keyboard(user_id: int):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Подтвердить оплату", callback_data=f"confirm_{user_id}"))
    return keyboard

def get_admin_main_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Создать рассылку", callback_data="create_broadcast"))
    return keyboard 

def get_crypto_payment_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("₿ Месяц - 1000₽", callback_data="crypto_month"))
    keyboard.add(InlineKeyboardButton("₿ Год - 10000₽", callback_data="crypto_year"))
    keyboard.add(InlineKeyboardButton("₿ Навсегда - 50000₽", callback_data="crypto_forever"))
    return keyboard

def get_crypto_currency_keyboard(duration: str):
    keyboard = InlineKeyboardMarkup()
    for currency, emoji in PAYMENT_METHODS['crypto']['currencies'].items():
        keyboard.add(InlineKeyboardButton(
            f"{emoji} {currency}",
            callback_data=f"crypto_pay_{currency}_{duration}"
        ))
    return keyboard 