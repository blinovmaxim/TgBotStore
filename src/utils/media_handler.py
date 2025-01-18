from aiogram import types
from typing import Union, List
from functools import lru_cache
import aiohttp
from collections import Counter
import json

async def process_media(message: types.Message) -> Union[List[str], None]:
    """Обработка медиафайлов в сообщении"""
    if message.photo:
        return [message.photo[-1].file_id]
    elif message.video:
        return [message.video.file_id]
    elif message.document:
        return [message.document.file_id]
    return None 

@lru_cache(maxsize=100)
async def cache_image(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return url
            return None 

class Stats:
    def __init__(self):
        self.views = Counter()
        self.posts = Counter()
        
    def add_view(self, product_id: str):
        self.views[product_id] += 1
        
    def add_post(self, product_id: str):
        self.posts[product_id] += 1
        
    def save(self):
        with open('stats.json', 'w') as f:
            json.dump({'views': dict(self.views), 'posts': dict(self.posts)}, f) 