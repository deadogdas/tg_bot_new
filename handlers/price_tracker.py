import logging
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from utils.api_client import fetch_json

router_price = Router()

tracked_items: Dict[int, List[dict]] = {}


@router_price.message(Command("track"))
async def track_price(message: Message):
    parts = message.text.split(maxsplit=2)
    
    if len(parts) < 2:
        await message.answer(
            "📊 Отслеживание цен на Wildberries и Ozon\n\n"
            "Формат:\n"
            "/track <ссылка> [целевая_цена]\n\n"
            "Примеры:\n"
            "/track https://www.wildberries.ru/catalog/12345/detail.aspx\n"
            "/track https://www.ozon.ru/product/12345 5000"
        )
        return
    
    url = parts[1]
    target_price = None
    
    if len(parts) == 3:
        try:
            target_price = float(parts[2])
        except ValueError:
            await message.answer("❌ Неверный формат цены")
            return
    
    if not re.match(r'https?://', url):
        await message.answer("❌ Укажите корректную ссылку")
        return
    
    if "wildberries.ru" not in url and "ozon.ru" not in url:
        await message.answer("❌ Поддерживаются только WB и Ozon")
        return
    
    await message.answer("⏳ Проверяю товар...")
    
    product_info = await get_product_info(url)
    
    if not product_info:
        await message.answer("❌ Не удалось получить информацию о товаре")
        return
    
    user_id = message.from_user.id
    
    if user_id not in tracked_items:
        tracked_items[user_id] = []
    
    if len(tracked_items[user_id]) >= 10:
        await message.answer("❌ Достигнут лимит (10 товаров)")
        return
    
    for item in tracked_items[user_id]:
        if item["product_id"] == product_info["product_id"]:
            await message.answer("⚠️ Этот товар уже отслеживается")
            return
    
    item = {
        "url": url,
        "product_id": product_info["product_id"],
        "name": product_info["name"],
        "current_price": product_info["price"],
        "target_price": target_price,
        "last_check": datetime.now(),
        "currency": "₽",
        "shop": product_info["shop"],
        "chat_id": message.chat.id
    }
    
    tracked_items[user_id].append(item)
    
    shop_emoji = "🟣" if item["shop"] == "wildberries" else "🔵"
    response = (
        f"✅ Товар добавлен!\n\n"
        f"{shop_emoji} {item['shop'].upper()}\n"
        f"📦 {item['name']}\n"
        f"💰 Текущая цена: {item['current_price']:,.0f} ₽\n"
    )
    
    if target_price:
        diff = item['current_price'] - target_price
        response += f"🎯 Целевая цена: {target_price:,.0f} ₽\n"
        if diff > 0:
            response += f"📉 Нужно снижение на {diff:,.0f} ₽\n"
        response += "\n✉️ Вы получите уведомление!"
    else:
        response += "\n✉️ Уведомления об изменении цены."
    
    await message.answer(response)
    
    asyncio.create_task(monitor_price(message.bot, user_id, len(tracked_items[user_id]) - 1))


@router_price.message(Command("tracked"))
async def show_tracked(message: Message):
    user_id = message.from_user.id
    
    if user_id not in tracked_items or not tracked_items[user_id]:
        await message.answer("📋 У вас нет отслеживаемых товаров")
        return
    
    response = "📊 Ваши товары:\n\n"
    
    for idx, item in enumerate(tracked_items[user_id], 1):
        shop_emoji = "🟣" if item['shop'] == "wildberries" else "🔵"
        response += f"{idx}. {shop_emoji} {item['name'][:40]}...\n"
        response += f"   💰 {item['current_price']:,.0f} ₽"
        
        if item['target_price']:
            response += f" → 🎯 {item['target_price']:,.0f} ₽"
        
        response += "\n\n"
    
    response += "🔄 Проверка каждые 6 часов"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="price_delete")],
        [InlineKeyboardButton(text="🔄 Проверить", callback_data="price_check_now")]
    ])
    
    await message.answer(response, reply_markup=keyboard)


@router_price.callback_query(F.data == "price_check_now")
async def check_prices_now(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in tracked_items or not tracked_items[user_id]:
        await callback.answer("Нет товаров")
        return
    
    await callback.answer("⏳ Проверяю...")
    
    results = []
    for item in tracked_items[user_id]:
        product_info = await get_product_info(item["url"])
        
        if product_info:
            old_price = item["current_price"]
            new_price = product_info["price"]
            
            if new_price != old_price:
                diff = old_price - new_price
                percent = (diff / old_price) * 100
                
                shop_emoji = "🟣" if item['shop'] == "wildberries" else "🔵"
                
                if diff > 0:
                    results.append(
                        f"{shop_emoji} {item['name'][:30]}...\n"
                        f"📉 {old_price:,.0f} → {new_price:,.0f} ₽ (-{percent:.1f}%)"
                    )
                else:
                    results.append(
                        f"{shop_emoji} {item['name'][:30]}...\n"
                        f"📈 {old_price:,.0f} → {new_price:,.0f} ₽ (+{abs(percent):.1f}%)"
                    )
                
                item["current_price"] = new_price
                item["last_check"] = datetime.now()
    
    if results:
        response = "🔄 Изменения:\n\n" + "\n\n".join(results)
    else:
        response = "✅ Цены не изменились"
    
    await callback.message.answer(response)


@router_price.callback_query(F.data == "price_delete")
async def delete_tracked_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in tracked_items or not tracked_items[user_id]:
        await callback.answer("Нет товаров")
        return
    
    buttons = []
    for idx, item in enumerate(tracked_items[user_id]):
        shop_emoji = "🟣" if item['shop'] == "wildberries" else "🔵"
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {shop_emoji} {item['name'][:30]}...",
                callback_data=f"price_del_{idx}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="price_cancel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Выберите товар:", reply_markup=keyboard)


@router_price.callback_query(F.data.startswith("price_del_"))
async def delete_tracked_item(callback: CallbackQuery):
    user_id = callback.from_user.id
    idx = int(callback.data.split("_")[2])
    
    if user_id in tracked_items and 0 <= idx < len(tracked_items[user_id]):
        tracked_items[user_id].pop(idx)
        await callback.answer("✅ Удалено")
        await callback.message.edit_text("✅ Товар удалён")
    else:
        await callback.answer("❌ Не найден")


@router_price.callback_query(F.data == "price_cancel")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text("❌ Отменено")


async def get_product_info(url: str) -> Optional[dict]:
    if "wildberries.ru" in url:
        return await parse_wildberries(url)
    elif "ozon.ru" in url:
        return await parse_ozon(url)
    return None


async def parse_wildberries(url: str) -> Optional[dict]:
    try:
        match = re.search(r'/catalog/(\d+)/', url)
        if not match:
            return None
        
        article = match.group(1)
        vol = article[:len(article) - 5]
        part = article[:len(article) - 3]
        basket = get_wb_basket(int(vol))
        
        api_url = f"https://basket-{basket:02d}.wbbasket.ru/vol{vol}/part{part}/{article}/info/ru/card.json"
        data = await fetch_json(api_url)
        
        if not data:
            return None
        
        name = data.get("imt_name", "Товар Wildberries")
        
        price = 0
        if "extended" in data and "basicPriceU" in data["extended"]:
            price = data["extended"]["basicPriceU"] / 100
        elif "salePriceU" in data:
            price = data["salePriceU"] / 100
        
        if price == 0:
            return None
        
        return {
            "product_id": article,
            "name": name,
            "price": price,
            "shop": "wildberries"
        }
    
    except Exception as e:
        logging.error(f"WB parse error: {e}")
        return None


def get_wb_basket(vol: int) -> int:
    if vol <= 143:
        return 1
    elif vol <= 287:
        return 2
    elif vol <= 431:
        return 3
    elif vol <= 719:
        return 4
    elif vol <= 1007:
        return 5
    elif vol <= 1061:
        return 6
    elif vol <= 1115:
        return 7
    elif vol <= 1169:
        return 8
    elif vol <= 1313:
        return 9
    elif vol <= 1601:
        return 10
    elif vol <= 1655:
        return 11
    elif vol <= 1919:
        return 12
    elif vol <= 2045:
        return 13
    elif vol <= 2189:
        return 14
    else:
        return 15


async def parse_ozon(url: str) -> Optional[dict]:
    try:
        match = re.search(r'-(\d+)/?', url)
        if not match:
            return None
        
        product_id = match.group(1)
        api_url = f"https://www.ozon.ru/api/composer-api.bx/page/json/v2?url=/product/{product_id}/"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        import requests
        response = await asyncio.to_thread(
            lambda: requests.get(api_url, headers=headers, timeout=10)
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        widgets = data.get("widgetStates", {})
        
        product_data = None
        for key, value in widgets.items():
            if isinstance(value, str):
                try:
                    import json
                    parsed = json.loads(value)
                    if "name" in parsed and "price" in parsed:
                        product_data = parsed
                        break
                except:
                    continue
        
        if not product_data:
            for key, value in widgets.items():
                if "webPrice" in key or "webAPrice" in key:
                    try:
                        import json
                        parsed = json.loads(value) if isinstance(value, str) else value
                        if "price" in parsed:
                            product_data = parsed
                            break
                    except:
                        continue
        
        if not product_data:
            return None
        
        name = product_data.get("name", "Товар Ozon")
        
        price = 0
        if "price" in product_data:
            price_str = product_data["price"]
            price = float(re.sub(r'[^\d.]', '', str(price_str)))
        
        if price == 0:
            return None
        
        return {
            "product_id": product_id,
            "name": name[:100],
            "price": price,
            "shop": "ozon"
        }
    
    except Exception as e:
        logging.error(f"Ozon parse error: {e}")
        return None


async def monitor_price(bot, user_id: int, item_index: int):
    while True:
        try:
            await asyncio.sleep(21600)  # 6 часов
            
            if user_id not in tracked_items or item_index >= len(tracked_items[user_id]):
                break
            
            item = tracked_items[user_id][item_index]
            product_info = await get_product_info(item["url"])
            
            if not product_info:
                continue
            
            new_price = product_info["price"]
            old_price = item["current_price"]
            
            item["current_price"] = new_price
            item["last_check"] = datetime.now()
            
            shop_emoji = "🟣" if item['shop'] == "wildberries" else "🔵"
            
            if new_price < old_price:
                price_drop = old_price - new_price
                percent_drop = (price_drop / old_price) * 100
                
                message = (
                    f"📉 Цена снизилась!\n\n"
                    f"{shop_emoji} {item['shop'].upper()}\n"
                    f"📦 {item['name']}\n\n"
                    f"💰 Было: {old_price:,.0f} ₽\n"
                    f"💰 Стало: {new_price:,.0f} ₽\n"
                    f"📊 Снижение: {price_drop:,.0f} ₽ (-{percent_drop:.1f}%)\n\n"
                    f"🔗 {item['url']}"
                )
                
                if item["target_price"] and new_price <= item["target_price"]:
                    message = "🎯 " + message + "\n\n✅ Целевая цена!"
                
                await bot.send_message(item["chat_id"], message)
            
            elif new_price > old_price:
                price_increase = new_price - old_price
                percent_increase = (price_increase / old_price) * 100
                
                if percent_increase > 10:
                    message = (
                        f"📈 Цена выросла!\n\n"
                        f"{shop_emoji} {item['shop'].upper()}\n"
                        f"📦 {item['name']}\n\n"
                        f"💰 Было: {old_price:,.0f} ₽\n"
                        f"💰 Стало: {new_price:,.0f} ₽\n"
                        f"📊 Рост: {price_increase:,.0f} ₽ (+{percent_increase:.1f}%)\n\n"
                        f"🔗 {item['url']}"
                    )
                    
                    await bot.send_message(item["chat_id"], message)
        
        except Exception as e:
            logging.error(f"Monitor error: {e}")


def get_router_price():
    return router_price