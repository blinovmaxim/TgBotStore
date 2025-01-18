from aiogram import types
from typing import Union, List

async def process_media(message: types.Message) -> Union[List[str], None]:
    """Обработка медиафайлов в сообщении"""
    if message.photo:
        return [message.photo[-1].file_id]
    elif message.video:
        return [message.video.file_id]
    elif message.document:
        return [message.document.file_id]
    return None 