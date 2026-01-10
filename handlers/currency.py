from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from utils.api_client import fetch_json

router_currency = Router()

valute_json ="https://www.cbr-xml-daily.ru/daily_json.js"

@router_currency.message(Command("usd"))
async def get_usd_rate(message: Message):
    data = await fetch_json(valute_json)
    
    if not data:
        await message.answer("❌ Не удалось получить курс USD")
        return
    
    try:
        rate = data["Valute"]["USD"]["Value"]
        await message.answer(f"💵 USD/RUB\n1 USD = {rate:.2f} ₽")
    except KeyError:
        await message.answer("❌ Ошибка обработки данных")

@router_currency.message(Command("eur"))
async def get_eur_rate(message: Message):
    data = await fetch_json(valute_json)
    
    if not data:
        await message.answer("❌ Не удалось получить курс EUR")
        return
    
    try:
        rate = data["Valute"]["EUR"]["Value"]
        await message.answer(f"💶 EUR/RUB\n1 EUR = {rate:.2f} ₽")
    except KeyError:
        await message.answer("❌ Ошибка обработки данных")

@router_currency.message(Command("cny"))
async def get_cny_rate(message: Message):
    data = await fetch_json(valute_json)
    
    if not data:
        await message.answer("❌ Не удалось получить курс CNY")
        return
    
    try:
        rate = data["Valute"]["CNY"]["Value"]
        await message.answer(f"💴 CNY/RUB\n1 CNY = {rate:.2f} ₽")
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
            f"Bitcoin:\n"
            f"1 BTC = ${btc_usd:,.0f}\n"
            f"1 BTC = {btc_rub:,.0f} ₽"
        )
    except KeyError:
        await message.answer("❌ Ошибка обработки данных")

@router_currency.message(Command("doge"))
async def get_doge_rate(message: Message):
    url = "https://api.coingecko.com/api/v3/simple/price?ids=Dogecoin&vs_currencies=usd,rub"
    data = await fetch_json(url)
    
    if not data:
        await message.answer("❌ Не удалось получить курс DOGE")
        return
    
    try:
        doge_usd = data["dogecoin"]["usd"]
        doge_rub = data["dogecoin"]["rub"]
        await message.answer(
            f"Dogecoin:\n"
            f"1 DOGE = ${doge_usd:,.0f}\n"
            f"1 DOGE = {doge_rub:,.0f} ₽"
        )
    except KeyError:
        await message.answer("❌ Ошибка обработки данных")

@router_currency.message(Command("eth"))
async def get_eth_rate(message: Message):
    url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd,rub"
    data = await fetch_json(url)
    
    if not data:
        await message.answer("❌ Не удалось получить курс ETH")
        return
    
    try:
        eth_usd = data["ethereum"]["usd"]
        eth_rub = data["ethereum"]["rub"]
        await message.answer(
            f"Ethereum:\n"
            f"1 ETH = ${eth_usd:,.0f}\n"
            f"1 ETH = {eth_rub:,.0f} ₽"
        )
    except KeyError:
        await message.answer("❌ Ошибка обработки данных")

@router_currency.message(Command("sol"))
async def get_sol_rate(message: Message):
    url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd,rub"
    data = await fetch_json(url)
    
    if not data:
        await message.answer("❌ Не удалось получить курс SOL")
        return
    
    try:
        sol_usd = data["solana"]["usd"]
        sol_rub = data["solana"]["rub"]
        await message.answer(
            f"Solana:\n"
            f"1 SOL = ${sol_usd:,.0f}\n"
            f"1 SOL = {sol_rub:,.0f} ₽"
        )
    except KeyError:
        await message.answer("❌ Ошибка обработки данных")

def get_router_currency():
    return router_currency