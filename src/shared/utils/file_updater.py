import os
import logging
import aiohttp
import asyncio
from datetime import datetime, timedelta
import hashlib
from shared.utils.csv_handler import read_products
import importlib
import sys

class FileUpdater:
    def __init__(self, url: str, local_path: str, update_interval: int = 3600):
        """
        url: URL файла на сайте поставщика
        local_path: путь к локальному файлу
        update_interval: интервал обновления в секундах (по умолчанию 1 час)
        """ 
        self.url = url
        self.local_path = local_path
        self.update_interval = update_interval
        self.last_modified = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/csv,application/csv,text/plain',
            'Accept-Language': 'uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://websklad.biz.ua/',
            'Origin': 'https://websklad.biz.ua',
            'Connection': 'keep-alive'
        }
        
    async def download_file(self) -> bool:
        """Скачивает файл и возвращает True если файл был обновлен"""
        try:
            # Создаем директорию если её нет
            os.makedirs(os.path.dirname(self.local_path), exist_ok=True)
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(self.url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Если файла нет - сразу сохраняем
                        if not os.path.exists(self.local_path):
                            with open(self.local_path, 'wb') as f:
                                f.write(content)
                            logging.info(f"Файл успешно создан: {self.local_path}")
                            return True
                        
                        # Если файл есть - проверяем изменения
                        with open(self.local_path, 'rb') as f:
                            old_content = f.read()
                            if old_content == content:
                                return False
                        
                        # Сохраняем обновленный файл
                        with open(self.local_path, 'wb') as f:
                            f.write(content)
                        logging.info(f"Файл успешно обновлен: {self.local_path}")
                        return True
                    else:
                        logging.error(f"Ошибка при скачивании файла: {response.status}")
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
        
        # Добавляем проверку на первый запуск
        if not hasattr(self, '_last_check'):
            self._last_check = datetime.now()
            return False
        
        time_diff = datetime.now() - file_datetime
        return time_diff > timedelta(seconds=self.update_interval)
    
    async def check_updates(self):
        """Проверяет обновления файла"""
        while True:
            try:
                if not os.path.exists(self.local_path):
                    is_updated = await self.download_file()
                    if not is_updated:
                        logging.error("Не удалось загрузить файл")
                        await asyncio.sleep(self.update_interval)
                        continue
                        
                    await asyncio.sleep(5)
                    products = read_products()
                    if not products:
                        logging.error("Файл загружен, но не удалось прочитать товары")
                        await asyncio.sleep(self.update_interval)
                        continue
                        
                    logging.info(f"Файл успешно загружен. Товаров: {len(products)}")
                    
                # Если файл есть - проверяем обновления
                if await self.should_update():
                    is_updated = await self.download_file()
                    if is_updated:
                        await asyncio.sleep(5)  # Ждем полной загрузки
                        read_products.cache_clear()
                        importlib.reload(sys.modules['shared.utils.csv_handler'])
                        logging.info("Кэш очищен, модуль перезагружен")
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logging.error(f"Ошибка при проверке обновлений: {str(e)}")
                await asyncio.sleep(self.update_interval)

    async def initial_check(self):
        """Первичная проверка и загрузка файла"""
        try:
            if not os.path.exists(self.local_path):
                is_updated = await self.download_file()
                if not is_updated:
                    logging.error("Не удалось загрузить файл")
                    return False
                    
                await asyncio.sleep(5)
                products = read_products()
                if not products:
                    logging.error("Файл загружен, но не удалось прочитать товары")
                    return False
                    
                logging.info(f"Файл успешно загружен. Товаров: {len(products)}")
                return True
            return True
            
        except Exception as e:
            logging.error(f"Ошибка при начальной проверке: {str(e)}")
            return False 