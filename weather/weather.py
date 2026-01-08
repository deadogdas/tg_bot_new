import logging
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from utils.api_client import fetch_json

router_weather = Router()


def get_router_weather():
    return router_weather


@router_weather.message(Command("weather"))
async def get_weather(message: Message):
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите город после команды\n"
            "Пример: /weather Москва"
        )
        return
    
    city = parts[1].strip()
    
    from config import WEATHER_KEY
    
    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={WEATHER_KEY}&units=metric&lang=ru"
    )
    
    data = await fetch_json(url)
    
    if not data:
        await message.answer("❌ Ошибка подключения к сервису погоды")
        return
    
    if data.get("cod") != 200:
        error_msg = data.get("message", "Неизвестная ошибка")
        if data.get("cod") == "404":
            await message.answer(f"❌ Город '{city}' не найден")
        else:
            await message.answer(f"❌ Ошибка API: {error_msg}")
        return
    
    try:
        temp = data["main"]["temp"]
        feels_like = data["main"]["feels_like"]
        humidity = data["main"]["humidity"]
        description = data["weather"][0]["description"].capitalize()
        wind_speed = data["wind"]["speed"]
        
        weather_report = (
            f"🌤 Погода в городе {city.capitalize()}:\n\n"
            f"🌡 Температура: {temp:.1f}°C (ощущается как {feels_like:.1f}°C)\n"
            f"☁️ Описание: {description}\n"
            f"💧 Влажность: {humidity}%\n"
            f"💨 Ветер: {wind_speed} м/с"
        )
        
        await message.answer(weather_report)
        
    except KeyError as e:
        logging.error(f"Weather data parsing error: {e}")
        await message.answer("❌ Ошибка обработки данных о погоде")