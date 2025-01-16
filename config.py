BOT_TOKEN = "7209977785:AAGenurLAvCR2qkmq4A-oGnRdLZ-o0s0y8I"
CHANNEL_ID = "7209977785"
ADMIN_ID = "6537869072"
DB_URL = "postgresql://bot_user:your_password@localhost/telegram_bot"
PROVIDER_TOKEN = "YOUR_PROVIDER_TOKEN"  # Токен для Telegram Payments
CRYPTO_PAY_TOKEN = ""  # Токен от @CryptoBot -> Crypto Pay -> Create App
CRYPTO_PAY_API_URL = "https://pay.crypt.bot/api"  # Основная сеть
# CRYPTO_PAY_API_URL = "https://testnet-pay.crypt.bot/api"  # Тестовая сеть 

# Настройки подписок
SUBSCRIPTION_SETTINGS = {
    'month': {
        'days': 30,           # Длительность в днях
        'price': 249,        # Цена в рублях
        'name': 'Месяц',      # Название для отображения
        'emoji': '💳'         # Эмодзи для кнопки
    },
    'year': {
        'days': 365,
        'price': 999,
        'name': 'Год',
        'emoji': '💳'
    },
    'forever': {
        'days': None,         # None для бессрочной подписки
        'price': 1999,
        'name': 'Навсегда',
        'emoji': '💳'
    }
}

# Настройки способов оплаты
PAYMENT_METHODS = {
    'tg_stars': {
        'name': 'Оплата картой',
        'emoji': '💳'
    },
    'p2p': {
        'name': 'Оплата переводом',
        'emoji': '💸',
        'card_number': '5599002083176414'  # Номер карты для P2P переводов
    },
    'crypto': {
        'name': 'Оплата криптовалютой',
        'emoji': '₿',
        'currencies': {
            'TON': '💎',
            'USDT': '💵',
            'BTC': '₿',
            'ETH': '⟠'
        }
    }
} 