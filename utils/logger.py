import logging
from logging.handlers import RotatingFileHandler


def setup_logger():
    """Настройка логгера с ротацией файлов"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(
                "bot.log",
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3
            ),
            logging.StreamHandler()
        ]
    )