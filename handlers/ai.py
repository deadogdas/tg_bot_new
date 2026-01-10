import asyncio
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from openai import OpenAI
from config import OPENAI_KEY

router_ai = Router()

# OpenRouter - бесплатный провайдер AI
client = OpenAI(
    api_key=OPENAI_KEY,
    base_url="https://openrouter.ai/api/v1"
)

user_sessions = {}

SYSTEM_PROMPTS = {
    "default": "You are a helpful AI assistant. Always respond in Russian if the user writes in Russian.",
    "movie": (
        "You are a movie expert. Answer ONLY questions about films, actors, genres, directors. "
        "If asked about anything else, politely decline. Always respond in Russian if the user writes in Russian."
    )
}


def get_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "mode": None,
            "messages": []
        }
    return user_sessions[user_id]


def reset_history(user_id: int, mode: str):
    session = get_session(user_id)
    session["mode"] = mode
    session["messages"] = [
        {"role": "system", "content": SYSTEM_PROMPTS[mode]}
    ]


@router_ai.message(Command("ai"))
async def enable_default_ai(message: types.Message):
    reset_history(message.from_user.id, "default")
    await message.answer("🤖 Обычный ИИ включён!")


@router_ai.message(Command("movie_ai"))
async def enable_movie_ai(message: types.Message):
    reset_history(message.from_user.id, "movie")
    await message.answer("🎬 Кино-ИИ включён!")


@router_ai.message(Command("ai_off"))
async def disable_ai(message: types.Message):
    session = get_session(message.from_user.id)
    session["mode"] = None
    session["messages"] = []
    await message.answer("🛑 ИИ выключен!")


@router_ai.message(F.text)
async def handle_ai_message(message: types.Message):
    user_id = message.from_user.id
    session = get_session(user_id)
    
    if not session["mode"]:
        return
    
    if not session["messages"]:
        reset_history(user_id, session["mode"])
    
    session["messages"].append({
        "role": "user",
        "content": message.text
    })
    
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="meta-llama/llama-3.3-70b-instruct:free",  # Бесплатная модель
            messages=session["messages"],
            temperature=0.7,
            max_tokens=2048,
            extra_headers={
                "HTTP-Referer": "https://github.com/deadogdas/tg_bot",
                "X-Title": "Telegram Bot"
            }
        )
        
        answer = response.choices[0].message.content
        
        session["messages"].append({
            "role": "assistant",
            "content": answer
        })
        
        if len(session["messages"]) > 21:
            session["messages"] = [session["messages"][0]] + session["messages"][-20:]
        
        await message.answer(answer)
        
    except Exception as e:
        logging.error(f"OpenRouter API error for user {user_id}: {e}")
        
        error_str = str(e).lower()
        if "rate" in error_str or "limit" in error_str:
            await message.answer("❌ Превышен лимит запросов. Подождите минуту.")
        elif "invalid" in error_str or "authentication" in error_str:
            await message.answer("❌ Неверный API ключ.")
        elif "credits" in error_str:
            await message.answer("❌ Недостаточно кредитов.")
        else:
            await message.answer(f"❌ Ошибка ИИ. Попробуйте позже.")


def get_ai_router():
    return router_ai