import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

AI_KEY = os.getenv("AI_KEY")
if not AI_KEY:
    raise ValueError("AI_KEY not found in .env file")

WEATHER_KEY = os.getenv("WEATHER_KEY")
if not WEATHER_KEY:
    raise ValueError("WEATHER_KEY not found in .env file")

OPENAI_KEY = os.getenv("OPENAI_KEY")

MAX_HISTORY_LENGTH = 15
API_TIMEOUT = 10