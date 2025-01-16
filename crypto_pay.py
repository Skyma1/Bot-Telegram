import aiohttp
from config import CRYPTO_PAY_TOKEN, CRYPTO_PAY_API_URL

class CryptoPayAPI:
    def __init__(self):
        self.token = CRYPTO_PAY_TOKEN
        self.base_url = CRYPTO_PAY_API_URL
        self.headers = {
            'Crypto-Pay-API-Token': self.token
        }
    
    async def create_invoice(self, amount: float, asset: str = "TON", description: str = None):
        """
        Создает инвойс для оплаты в криптовалюте
        """
        url = f"{self.base_url}/createInvoice"
        params = {
            "asset": asset,
            "amount": str(amount),
            "description": description or "Оплата подписки на канал",
            "paid_btn_name": "callback",
            "paid_btn_url": "https://t.me/your_bot",  # Замените на ссылку вашего бота
            "expires_in": 3600  # Срок действия инвойса - 1 час
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                return await response.json()

    async def get_invoice(self, invoice_id: int):
        """
        Получает информацию об инвойсе
        """
        url = f"{self.base_url}/getInvoices"
        params = {
            "invoice_ids": str(invoice_id)
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                data = await response.json()
                return data.get('result', [None])[0]

    async def get_currencies(self):
        """
        Получает список доступных криптовалют
        """
        url = f"{self.base_url}/getCurrencies"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers) as response:
                return await response.json() 