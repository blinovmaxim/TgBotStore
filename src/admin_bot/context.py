from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from shared.config import Config
from aiogram.client.session.aiohttp import AiohttpSession

class BotContext:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_bot()
        return cls._instance
    
    def _init_bot(self):
        """Инициализация нового бота"""
        self.bot = Bot(token=Config.ADMIN_BOT_TOKEN)
        self.bot.session = AiohttpSession()
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)
        
    async def restart(self):
        """Пересоздание бота и диспетчера"""
        await self.shutdown()
        self._init_bot()
        
    async def shutdown(self):
        """Корректное завершение работы бота"""
        import asyncio
        import logging
        
        logging.info("Завершение работы бота...")
        try:
            for task in asyncio.all_tasks():
                if task is not asyncio.current_task():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            await self.dp.storage.close()
            await self.bot.session.close()
        except Exception as e:
            logging.error(f"Ошибка при завершении: {str(e)}")

# Создаем глобальный экземпляр контекста
context = BotContext() 