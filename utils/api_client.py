import asyncio
import logging
from typing import Optional
import requests


async def fetch_json(url: str, timeout: int = 10) -> Optional[dict]:
    """
    Асинхронный GET-запрос с обработкой ошибок
    
    Args:
        url: URL для запроса
        timeout: Таймаут в секундах
        
    Returns:
        dict или None в случае ошибки
    """
    try:
        response = await asyncio.to_thread(
            lambda: requests.get(url, timeout=timeout)
        )
        response.raise_for_status()
        return response.json()
        
    except requests.Timeout:
        logging.error(f"Request timeout: {url}")
        return None
        
    except requests.HTTPError as e:
        logging.error(f"HTTP error: {url} | Status: {e.response.status_code}")
        return None
        
    except requests.RequestException as e:
        logging.error(f"Request failed: {url} | Error: {e}")
        return None
        
    except ValueError as e:
        logging.error(f"Invalid JSON response: {url} | Error: {e}")
        return None