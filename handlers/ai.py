import asyncio
import logging
from aiogram import Router, F, types
from aiogram.filters import Command
from mistralai import Mistral
from config import AI_KEY

router_ai = Router()

user_sessions = {}

client = Mistral(api_key=AI_KEY)
MODEL = "mistral-large-latest"

SYSTEM_PROMPTS = {
    "default": "You are a helpful AI assistant.",
    "movie": (
        "You are a movie expert. Answer ONLY about films, actors, genres, directors. "
        "Politely decline other topics."
    )
}


def get_session(user_id: int) -> dict:
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            "mode": None,
            "history": []
        }
    return user_sessions[user_id]


def reset_history(user_id: int, mode: str):
    session = get_session(user_id)
    session["mode"] = mode
    session["history"] = [{"role": "system", "content": SYSTEM_PROMPTS[mode]}]


@router_ai.message(Command("ai"))
async def enable_default_ai(message: types.Message):
    user_id = message.from_user.id
    reset_history(user_id, "default")
    await message.answer("🤖 Обычный ИИ включён!")


@router_ai.message(Command("movie_ai"))
async def enable_movie_ai(message: types.Message):
    user_id = message.from_user.id
    reset_history(user_id, "movie")
    await message.answer("🎬 Кино-ИИ включён!")


@router_ai.message(Command("ai_off"))
async def disable_ai(message: types.Message):
    user_id = message.from_user.id
    session = get_session(user_id)
    session["mode"] = None
    session["history"] = []
    await message.answer("🛑 ИИ выключен!")


@router_ai.message(F.text)
async def handle_ai_message(message: types.Message):
    user_id = message.from_user.id
    session = get_session(user_id)
    
    if not session["mode"]:
        return
    
    if not session["history"]:
        reset_history(user_id, session["mode"])
    
    session["history"].append({"role": "user", "content": message.text})
    
    try:
        response = await asyncio.to_thread(
            client.chat.complete,
            model=MODEL,
            messages=session["history"]
        )
        
        answer = response.choices[0].message.content
        session["history"].append({"role": "assistant", "content": answer})
        
        if len(session["history"]) > 15:
            session["history"] = [session["history"][0]] + session["history"][-12:]
        
        await message.answer(answer, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"AI error for user {user_id}: {e}")
        await message.answer("❌ Ошибка при обращении к ИИ. Попробуйте позже.")


def get_ai_router():
    return router_ai