import logging
import asyncio
import os
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, Document
from aiogram.filters import Command
from openai import OpenAI
from config import OPENAI_KEY
import PyPDF2
import pdfplumber
import requests
from bs4 import BeautifulSoup
import io

router_summary = Router()

# OpenRouter для AI
client = OpenAI(
    api_key=OPENAI_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# Папка для временных файлов
TEMP_DIR = Path("temp_docs")
TEMP_DIR.mkdir(exist_ok=True)


# ==================== КОМАНДЫ ====================

@router_summary.message(Command("summary"))
async def summary_text(message: Message):
    """
    Саммаризация текста
    /summary [текст] или ответ на сообщение с текстом
    """
    # Получаем текст
    if message.reply_to_message and message.reply_to_message.text:
        text = message.reply_to_message.text
    else:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer(
                "📝 Использование:\n\n"
                "1. /summary [ваш текст]\n"
                "2. Ответьте на сообщение командой /summary\n"
                "3. Отправьте PDF файл"
            )
            return
        text = parts[1]
    
    # Проверяем, это URL или текст
    if text.startswith("http://") or text.startswith("https://"):
        await summary_url(message, text)
        return
    
    if len(text) < 100:
        await message.answer("❌ Текст слишком короткий для саммаризации (минимум 100 символов)")
        return
    
    await message.answer("⏳ Делаю конспект...")
    
    try:
        summary = await summarize_text(text)
        await message.answer(f"📄 Краткое содержание:\n\n{summary}")
    except Exception as e:
        logging.error(f"Summary error: {e}")
        await message.answer("❌ Ошибка при создании конспекта")


@router_summary.message(Command("keypoints"))
async def extract_keypoints(message: Message):
    """
    Извлечение ключевых моментов
    /keypoints [текст] или ответ на сообщение
    """
    # Получаем текст
    if message.reply_to_message and message.reply_to_message.text:
        text = message.reply_to_message.text
    else:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Используйте: /keypoints [текст]")
            return
        text = parts[1]
    
    if len(text) < 100:
        await message.answer("❌ Текст слишком короткий")
        return
    
    await message.answer("⏳ Извлекаю ключевые моменты...")
    
    try:
        keypoints = await extract_key_points(text)
        await message.answer(f"🎯 Ключевые моменты:\n\n{keypoints}")
    except Exception as e:
        logging.error(f"Keypoints error: {e}")
        await message.answer("❌ Ошибка при извлечении ключевых моментов")


@router_summary.message(F.document)
async def handle_document(message: Message):
    """Обработка PDF и текстовых документов"""
    document: Document = message.document
    
    # Проверяем тип файла
    if document.mime_type == "application/pdf":
        await handle_pdf(message, document)
    elif document.mime_type == "text/plain":
        await handle_text_file(message, document)
    else:
        await message.answer(
            "❌ Поддерживаются только PDF и TXT файлы\n\n"
            "💡 Попробуйте:\n"
            "• Отправить PDF документ\n"
            "• Отправить TXT файл\n"
            "• /summary [текст]\n"
            "• /summary [ссылка на статью]"
        )


# ==================== ОБРАБОТКА PDF ====================

async def handle_pdf(message: Message, document: Document):
    """Обработка PDF файла"""
    file_size_mb = document.file_size / (1024 * 1024)
    
    # Лимит 10 MB
    if file_size_mb > 10:
        await message.answer("❌ Файл слишком большой (максимум 10 MB)")
        return
    
    await message.answer("📄 Читаю PDF...")
    
    try:
        # Скачиваем файл
        file = await message.bot.get_file(document.file_id)
        file_path = file.file_path
        
        temp_file = TEMP_DIR / f"{document.file_id}.pdf"
        await message.bot.download_file(file_path, temp_file)
        
        # Читаем PDF
        text = extract_pdf_text(temp_file)
        
        # Удаляем временный файл
        os.remove(temp_file)
        
        if not text or len(text) < 100:
            await message.answer("❌ Не удалось извлечь текст из PDF или текст слишком короткий")
            return
        
        # Проверяем размер текста
        words_count = len(text.split())
        await message.answer(f"📊 Извлечено: {words_count} слов\n⏳ Создаю конспект...")
        
        # Создаём конспект
        summary = await summarize_text(text)
        
        # Отправляем конспект
        await message.answer(f"📄 Конспект документа:\n\n{summary}")
        
        # Предлагаем ключевые моменты
        keyboard = [[{"text": "🎯 Ключевые моменты", "callback_data": f"keypoints_{document.file_id}"}]]
        # Сохраняем текст для ключевых моментов (можно использовать кэш)
        
    except Exception as e:
        logging.error(f"PDF processing error: {e}")
        await message.answer("❌ Ошибка при обработке PDF")


def extract_pdf_text(file_path: Path) -> str:
    """Извлекает текст из PDF"""
    text = ""
    
    try:
        # Пробуем pdfplumber (лучше для сложных PDF)
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"
    except:
        # Fallback на PyPDF2
        try:
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for page in reader.pages:
                    text += page.extract_text() + "\n\n"
        except Exception as e:
            logging.error(f"PDF extraction error: {e}")
            return ""
    
    return text.strip()


# ==================== ОБРАБОТКА TXT ====================

async def handle_text_file(message: Message, document: Document):
    """Обработка текстового файла"""
    try:
        file = await message.bot.get_file(document.file_id)
        file_path = file.file_path
        
        temp_file = TEMP_DIR / f"{document.file_id}.txt"
        await message.bot.download_file(file_path, temp_file)
        
        with open(temp_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        os.remove(temp_file)
        
        if len(text) < 100:
            await message.answer("❌ Текст слишком короткий")
            return
        
        await message.answer("⏳ Создаю конспект...")
        
        summary = await summarize_text(text)
        await message.answer(f"📄 Конспект:\n\n{summary}")
        
    except Exception as e:
        logging.error(f"Text file error: {e}")
        await message.answer("❌ Ошибка при чтении файла")


# ==================== ОБРАБОТКА URL ====================

async def summary_url(message: Message, url: str):
    """Саммаризация статьи по URL"""
    await message.answer("🌐 Загружаю статью...")
    
    try:
        # Скачиваем страницу
        response = await asyncio.to_thread(
            lambda: requests.get(url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
        )
        
        if response.status_code != 200:
            await message.answer("❌ Не удалось загрузить страницу")
            return
        
        # Парсим HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем скрипты и стили
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Извлекаем текст
        text = soup.get_text()
        
        # Чистим текст
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        if len(text) < 200:
            await message.answer("❌ Не удалось извлечь содержимое статьи")
            return
        
        await message.answer("⏳ Создаю конспект...")
        
        summary = await summarize_text(text)
        await message.answer(f"📄 Конспект статьи:\n\n{summary}\n\n🔗 {url}")
        
    except Exception as e:
        logging.error(f"URL summary error: {e}")
        await message.answer("❌ Ошибка при обработке URL")


# ==================== AI ФУНКЦИИ ====================

async def summarize_text(text: str, max_length: int = 1000) -> str:
    """Создаёт краткое содержание текста"""
    
    # Если текст очень длинный, режем на части
    if len(text) > 15000:
        text = text[:15000] + "..."
    
    prompt = f"""Создай краткое содержание следующего текста. 
Конспект должен быть структурированным, понятным и содержать основные мысли.
Отвечай на русском языке.

Текст:
{text}

Краткое содержание:"""
    
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=max_length,
            extra_headers={
                "HTTP-Referer": "https://github.com/deadogdas/tg_bot",
                "X-Title": "Summary Bot"
            }
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logging.error(f"AI summarization error: {e}")
        raise


async def extract_key_points(text: str) -> str:
    """Извлекает ключевые моменты из текста"""
    
    if len(text) > 15000:
        text = text[:15000] + "..."
    
    prompt = f"""Извлеки ключевые моменты из следующего текста.
Представь их в виде списка (5-7 пунктов).
Каждый пункт должен быть кратким и информативным.
Отвечай на русском языке.

Текст:
{text}

Ключевые моменты:"""
    
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="meta-llama/llama-3.3-70b-instruct:free",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=800,
            extra_headers={
                "HTTP-Referer": "https://github.com/deadogdas/tg_bot",
                "X-Title": "Summary Bot"
            }
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logging.error(f"AI keypoints error: {e}")
        raise


def get_router_summary():
    return router_summary