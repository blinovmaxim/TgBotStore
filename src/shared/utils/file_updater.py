import os
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
import hashlib

class FileUpdater:
    def __init__(self, url: str, local_path: str, update_interval: int = 120):
        """
        url: URL файла на сайте поставщика
        local_path: путь к локальному файлу
        update_interval: интервал обновления в секундах (по умолчанию 10 минут)
        """ 
        self.url = url
        self.local_path = local_path
        self.update_interval = update_interval
        self.last_update = None
        self.last_hash = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/csv,application/csv,text/plain',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://websklad.biz.ua/',
            'Origin': 'https://websklad.biz.ua',
            'Connection': 'keep-alive'
        }
        
    async def download_file(self) -> bool:
        """Загружает файл с сайта поставщика"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(self.url, allow_redirects=True, ssl=False) as response:
                    if response.status == 200:
                        content = await response.read()
                        # Проверяем изменился ли файл
                        current_hash = hashlib.md5(content).hexdigest()
                        
                        if self.last_hash != current_hash:
                            with open(self.local_path, 'wb') as f:
                                f.write(content)
                            self.last_hash = current_hash
                            self.last_update = datetime.now()
                            logging.info(f"Файл успешно обновлен: {self.local_path}")
                            return True
                        return False
                    else:
                        logging.error(f"Ошибка загрузки файла: {response.status} - {await response.text()}")
                        return False
        except Exception as e:
            logging.error(f"Ошибка при обновлении файла: {str(e)}")
            return False
            
    async def should_update(self) -> bool:
        """Проверяет, нужно ли обновлять файл"""
        if not os.path.exists(self.local_path):
            return True
            
        file_time = os.path.getmtime(self.local_path)
        file_datetime = datetime.fromtimestamp(file_time)
        
        return datetime.now() - file_datetime > timedelta(seconds=self.update_interval)
    
    async def check_updates(self):
        while True:
            try:
                if await self.should_update():
                    await self.download_file()
            except Exception as e:
                logging.error(f"Ошибка при проверке обновлений: {str(e)}")
            await asyncio.sleep(60)  # Проверяем каждую минуту 