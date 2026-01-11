import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from utils.logger import setup_logger

from handlers.general import get_router_general
from handlers.ai import get_ai_router
from handlers.movies import get_router_movies
from handlers.currency import get_router_currency
from handlers.voice import get_router_voice
from handlers.price_tracker import get_router_price
from handlers.reminders import get_router_reminders, restart_all_reminders
from weather.weather import get_router_weather
from handlers.summary import get_router_summary
from handlers.music import get_router_music


async def main():
    setup_logger()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрация роутеров
    dp.include_router(get_router_general())
    dp.include_router(get_router_movies())
    dp.include_router(get_router_currency())
    dp.include_router(get_router_weather())
    dp.include_router(get_router_voice())
    dp.include_router(get_router_price())
    dp.include_router(get_router_reminders())
    dp.include_router(get_router_summary())
    dp.include_router(get_router_music())
    dp.include_router(get_ai_router())
    
    # Перезапускаем все активные напоминания
    restart_all_reminders(bot)
    
    logging.info("Bot started successfully")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())