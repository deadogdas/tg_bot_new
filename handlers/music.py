import os
import asyncio
from aiogram import Router, types
from aiogram.filters import Command
from yt_dlp import YoutubeDL
from aiogram.types import FSInputFile

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

router_music = Router()

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(DOWNLOAD_DIR, '%(title)s.%(ext)s'),
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}


def sanitize_filename(title: str) -> str:
    """Удаляем все опасные символы из имени файла для Telegram"""
    return "".join(c for c in title if c.isalnum() or c in ("_", "-"))


async def download_track(query: str) -> str | None:
    """Ищет трек на YouTube и скачивает его. Возвращает путь к файлу или None"""
    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            None,
            lambda: YoutubeDL(YDL_OPTIONS).extract_info(f"ytsearch1:{query}", download=True)
        )

        # Получаем название и расширение скачанного файла
        track = info['entries'][0]
        title = track['title']
        ext = "mp3"  # yt-dlp конвертирует в mp3 через postprocessor
        safe_title = sanitize_filename(title)
        file_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}.{ext}")

        # Если yt-dlp по какой-то причине дал другое имя файла, ищем его в папке
        if not os.path.exists(file_path):
            for f in os.listdir(DOWNLOAD_DIR):
                if f.startswith(title[:10]):
                    file_path = os.path.join(DOWNLOAD_DIR, f)
                    break

        return file_path if os.path.exists(file_path) else None

    except Exception as e:
        print(f"Ошибка при скачивании: {e}")
        return None


@router_music.message(Command("music"))
async def cmd_music(message: types.Message):
    query = message.text.replace("/music", "").strip()
    if not query:
        await message.answer("Введите название трека, например:\n/music imagine dragons believer")
        return

    await message.answer(f"🔎 Ищу и скачиваю трек: <b>{query}</b>…")

    file_path = await download_track(query)
    if not file_path:
        await message.answer("❌ Не удалось скачать трек.")
        return

    try:
        audio_file = FSInputFile(file_path)
        await message.answer_audio(audio=audio_file, title=query, caption="🎧 Вот ваш трек!")
    except Exception as e:
        print(f"Ошибка при отправке аудио: {e}")
        await message.answer("❌ Произошла ошибка при отправке трека.")


def get_router_music():
    return router_music
