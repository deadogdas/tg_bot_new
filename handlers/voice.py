import logging
import os
import asyncio
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, Voice
from openai import OpenAI
from config import OPENAI_KEY

router_voice = Router()

if OPENAI_KEY:
    client = OpenAI(api_key=OPENAI_KEY)
    VOICE_ENABLED = True
else:
    VOICE_ENABLED = False
    logging.warning("OPENAI_KEY not found. Voice transcription disabled.")

TEMP_DIR = Path("temp_audio")
TEMP_DIR.mkdir(exist_ok=True)


@router_voice.message(F.voice)
async def handle_voice(message: Message):
    if not VOICE_ENABLED:
        await message.answer(
            "❌ Транскрибация голоса недоступна.\n"
            "Добавьте OPENAI_KEY в .env файл."
        )
        return
    
    voice: Voice = message.voice
    await message.bot.send_chat_action(message.chat.id, "typing")
    
    try:
        file_id = voice.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path
        
        temp_file = TEMP_DIR / f"{file_id}.ogg"
        await message.bot.download_file(file_path, temp_file)
        
        transcription = await transcribe_audio(temp_file)
        
        os.remove(temp_file)
        
        if transcription:
            await message.answer(f"🎤 Распознанный текст:\n\n{transcription}")
        else:
            await message.answer("❌ Не удалось распознать речь")
    
    except Exception as e:
        logging.error(f"Voice transcription error: {e}")
        await message.answer("❌ Ошибка при обработке голосового сообщения")


async def transcribe_audio(audio_file: Path) -> str:
    try:
        def _transcribe():
            with open(audio_file, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language="ru"
                )
                return transcript.text
        
        text = await asyncio.to_thread(_transcribe)
        return text
    
    except Exception as e:
        logging.error(f"Whisper API error: {e}")
        return None


def get_router_voice():
    return router_voice