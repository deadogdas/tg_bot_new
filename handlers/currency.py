from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from utils.api_client import fetch_json

router_currency = Router()


@router_currency.message(Command("usd"))
async def get_usd_rate(message: Message):
    data = await fetch_json("https://www.cbr-xml-daily.ru/daily_json.js")
    
    if not data:
        await message.answer("❌ Не удалось получить курс USD")
        return
    
    try:
        rate = data["Valute"]["USD"]["Value"]
        await message.answer(f"💵 USD/RUB\n1 USD = {rate:.2f} ₽")
    except KeyError:
        await message.answer("❌ Ошибка обработки данных")


@router_currency.message(Command("btc"))
async def get_btc_rate(message: Message):
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,rub"
    data = await fetch_json(url)
    
    if not data:
        await message.answer("❌ Не удалось получить курс BTC")
        return
    
    try:
        btc_usd = data["bitcoin"]["usd"]
        btc_rub = data["bitcoin"]["rub"]
        await message.answer(
            f"₿ Bitcoin:\n"
            f"1 BTC = ${btc_usd:,.0f}\n"
            f"1 BTC = {btc_rub:,.0f} ₽"
        )
    except KeyError:
        await message.answer("❌ Ошибка обработки данных")


def get_router_currency():
    return router_currency