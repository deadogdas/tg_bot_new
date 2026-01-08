from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states.movie_state import MovieState
from handlers.ai import reset_history

router_movies = Router()

GENRES = {
    "1": ("комедия", ["Маска", "1+1", "Форрест Гамп", "Один дома", "Зеленая книга"]),
    "2": ("боевик", ["Джон Уик", "Адреналин", "Люди в чёрном", "Миссия невыполнима", "Тёмный рыцарь"]),
    "3": ("ужасы", ["Оно", "Пятница 13-е", "Кошмар на улице Вязов", "Хэллоуин", "Астрал"]),
    "4": ("триллер", ["Бойцовский клуб", "Остров проклятых", "Легенда", "Области тьмы", "Гнев человеческий"]),
    "5": ("фэнтези", ["Гарри Поттер", "Властелин Колец", "Аватар", "Дэдпул", "Тор"]),
}


@router_movies.message(Command("movie"))
async def movie_start(message: Message, state: FSMContext):
    await state.set_state(MovieState.choosing)
    await message.answer(
        "🎬 Выберите жанр:\n"
        "1. Комедия\n2. Боевик\n3. Ужасы\n"
        "4. Триллер\n5. Фэнтези\n6. ИИ-помощник"
    )


@router_movies.message(MovieState.choosing)
async def handle_genre_choice(message: Message, state: FSMContext):
    choice = message.text.strip()
    
    if choice.lower() in ["помощь", "6", "ии", "ai"]:
        reset_history(message.from_user.id, "movie")
        await message.answer(
            "🎬 Кино-ИИ включён!\n"
            "Опиши, что хочешь посмотреть."
        )
        await state.clear()
        return
    
    genre_key = None
    for key, (name, _) in GENRES.items():
        if choice == key or choice.lower() == name.lower():
            genre_key = key
            break
    
    if not genre_key:
        await message.answer("❌ Неверный выбор. Введи цифру от 1 до 6.")
        return
    
    genre_name, movies = GENRES[genre_key]
    movie_list = "\n".join(f"{i+1}. {movie}" for i, movie in enumerate(movies))
    
    await message.answer(f"🎥 Лучшие {genre_name}:\n{movie_list}")
    await state.clear()


def get_router_movies():
    return router_movies