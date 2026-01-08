import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import json
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command

router_reminders = Router()

reminders: Dict[int, List[dict]] = {}
reminder_counter = 0

REMINDERS_FILE = Path("data/reminders.json")
REMINDERS_FILE.parent.mkdir(exist_ok=True)


def save_reminders():
    try:
        data = {}
        for user_id, user_reminders in reminders.items():
            data[str(user_id)] = [
                {
                    **r,
                    "time": r["time"].isoformat() if isinstance(r["time"], datetime) else r["time"]
                }
                for r in user_reminders
            ]
        
        with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error saving reminders: {e}")


def load_reminders():
    global reminders, reminder_counter
    
    if not REMINDERS_FILE.exists():
        return
    
    try:
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for user_id_str, user_reminders in data.items():
            user_id = int(user_id_str)
            reminders[user_id] = []
            
            for r in user_reminders:
                r["time"] = datetime.fromisoformat(r["time"])
                reminders[user_id].append(r)
                
                if r["id"] >= reminder_counter:
                    reminder_counter = r["id"] + 1
        
        logging.info(f"Loaded {sum(len(r) for r in reminders.values())} reminders")
    except Exception as e:
        logging.error(f"Error loading reminders: {e}")


@router_reminders.message(Command("remind"))
async def set_reminder(message: Message):
    parts = message.text.split(maxsplit=2)
    
    if len(parts) < 3:
        await message.answer(
            "⏰ Установка напоминаний\n\n"
            "Форматы:\n"
            "/remind <время> <текст>\n\n"
            "Примеры:\n"
            "• /remind 10m Проверить почту\n"
            "• /remind 2h Позвонить маме\n"
            "• /remind 1d Оплатить счета\n"
            "• /remind завтра 15:00 Встреча\n"
            "• /remind каждый_день 09:00 Зарядка\n\n"
            "Время:\n"
            "• 10m = 10 минут\n"
            "• 2h = 2 часа\n"
            "• 1d = 1 день"
        )
        return
    
    time_str = parts[1].lower()
    text = parts[2]
    
    remind_time, repeat_type = parse_time(time_str)
    
    if not remind_time:
        await message.answer(
            "❌ Неверный формат времени.\n"
            "Используйте: 10m, 2h, 1d, завтра"
        )
        return
    
    global reminder_counter
    reminder_id = reminder_counter
    reminder_counter += 1
    
    user_id = message.from_user.id
    
    reminder = {
        "id": reminder_id,
        "text": text,
        "time": remind_time,
        "repeat": repeat_type,
        "chat_id": message.chat.id
    }
    
    if user_id not in reminders:
        reminders[user_id] = []
    
    reminders[user_id].append(reminder)
    save_reminders()
    
    time_format = remind_time.strftime("%d.%m.%Y %H:%M")
    response = f"✅ Напоминание установлено!\n\n"
    response += f"📝 {text}\n"
    response += f"⏰ {time_format}\n"
    
    if repeat_type:
        repeat_names = {
            "daily": "каждый день",
            "weekly": "каждую неделю"
        }
        response += f"🔄 Повтор: {repeat_names.get(repeat_type, repeat_type)}"
    
    await message.answer(response)
    
    asyncio.create_task(send_reminder_task(message.bot, user_id, reminder_id))


@router_reminders.message(Command("reminders"))
async def show_reminders(message: Message):
    user_id = message.from_user.id
    
    if user_id not in reminders or not reminders[user_id]:
        await message.answer(
            "📋 У вас нет активных напоминаний.\n"
            "Используйте /remind для создания."
        )
        return
    
    sorted_reminders = sorted(reminders[user_id], key=lambda r: r["time"])
    
    response = "⏰ Ваши напоминания:\n\n"
    
    for r in sorted_reminders:
        time_str = r["time"].strftime("%d.%m %H:%M")
        response += f"• {time_str} - {r['text']}"
        
        if r["repeat"]:
            response += " 🔄"
        
        response += f" (ID: {r['id']})\n"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data="remind_delete")]
    ])
    
    await message.answer(response, reply_markup=keyboard)


@router_reminders.callback_query(F.data == "remind_delete")
async def delete_reminder_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    if user_id not in reminders or not reminders[user_id]:
        await callback.answer("Нет напоминаний")
        return
    
    buttons = []
    for r in reminders[user_id]:
        time_str = r["time"].strftime("%d.%m %H:%M")
        buttons.append([
            InlineKeyboardButton(
                text=f"🗑 {time_str} - {r['text'][:30]}",
                callback_data=f"remind_del_{r['id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="remind_cancel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Выберите напоминание:", reply_markup=keyboard)


@router_reminders.callback_query(F.data.startswith("remind_del_"))
async def delete_reminder(callback: CallbackQuery):
    user_id = callback.from_user.id
    reminder_id = int(callback.data.split("_")[2])
    
    if user_id in reminders:
        for i, r in enumerate(reminders[user_id]):
            if r["id"] == reminder_id:
                removed = reminders[user_id].pop(i)
                save_reminders()
                await callback.answer(f"✅ Удалено")
                await callback.message.edit_text("✅ Напоминание удалено")
                return
    
    await callback.answer("❌ Не найдено")


@router_reminders.callback_query(F.data == "remind_cancel")
async def cancel_delete_reminder(callback: CallbackQuery):
    await callback.message.edit_text("❌ Отменено")


@router_reminders.message(Command("timer"))
async def set_timer(message: Message):
    parts = message.text.split(maxsplit=2)
    
    if len(parts) < 2:
        await message.answer(
            "⏱ Быстрый таймер\n\n"
            "Формат: /timer <время> [текст]\n\n"
            "Примеры:\n"
            "• /timer 5m\n"
            "• /timer 30m Пицца\n"
            "• /timer 1h Встреча"
        )
        return
    
    time_str = parts[1].lower()
    text = parts[2] if len(parts) > 2 else "Таймер"
    
    delta = parse_relative_time(time_str)
    
    if not delta:
        await message.answer("❌ Неверный формат. Используйте: 5m, 30m, 1h")
        return
    
    await message.answer(f"⏱ Таймер на {time_str} установлен!")
    
    await asyncio.sleep(delta.total_seconds())
    
    await message.answer(f"⏰ {text}")


def parse_time(time_str: str) -> tuple:
    time_str = time_str.lower().replace("_", " ")
    
    if "каждый день" in time_str or "daily" in time_str:
        parts = time_str.split()
        if len(parts) > 2:
            time_part = parts[2]
            try:
                hour, minute = map(int, time_part.split(":"))
                now = datetime.now()
                remind_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                if remind_time <= now:
                    remind_time += timedelta(days=1)
                
                return (remind_time, "daily")
            except:
                pass
        
        return (datetime.now() + timedelta(days=1), "daily")
    
    if "каждую неделю" in time_str or "weekly" in time_str:
        return (datetime.now() + timedelta(weeks=1), "weekly")
    
    delta = parse_relative_time(time_str)
    if delta:
        return (datetime.now() + delta, None)
    
    if "завтра" in time_str:
        parts = time_str.split()
        if len(parts) > 1:
            time_part = parts[1]
            try:
                hour, minute = map(int, time_part.split(":"))
                remind_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
                remind_time += timedelta(days=1)
                return (remind_time, None)
            except:
                pass
        
        return (datetime.now() + timedelta(days=1), None)
    
    return (None, None)


def parse_relative_time(time_str: str) -> timedelta:
    try:
        if time_str.endswith('m'):
            minutes = int(time_str[:-1])
            return timedelta(minutes=minutes)
        elif time_str.endswith('h'):
            hours = int(time_str[:-1])
            return timedelta(hours=hours)
        elif time_str.endswith('d'):
            days = int(time_str[:-1])
            return timedelta(days=days)
    except ValueError:
        pass
    
    return None


async def send_reminder_task(bot, user_id: int, reminder_id: int):
    try:
        while True:
            if user_id not in reminders:
                break
            
            reminder = None
            for r in reminders[user_id]:
                if r["id"] == reminder_id:
                    reminder = r
                    break
            
            if not reminder:
                break
            
            now = datetime.now()
            wait_seconds = (reminder["time"] - now).total_seconds()
            
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            
            await bot.send_message(
                reminder["chat_id"],
                f"⏰ Напоминание:\n{reminder['text']}"
            )
            
            if reminder["repeat"]:
                if reminder["repeat"] == "daily":
                    reminder["time"] += timedelta(days=1)
                elif reminder["repeat"] == "weekly":
                    reminder["time"] += timedelta(weeks=1)
                
                save_reminders()
            else:
                reminders[user_id].remove(reminder)
                save_reminders()
                break
    
    except Exception as e:
        logging.error(f"Reminder task error: {e}")


def restart_all_reminders(bot):
    for user_id, user_reminders in reminders.items():
        for reminder in user_reminders:
            asyncio.create_task(
                send_reminder_task(bot, user_id, reminder["id"])
            )


def get_router_reminders():
    return router_reminders


load_reminders()