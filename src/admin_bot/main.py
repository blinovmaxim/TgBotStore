from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from shared.config import Config
from admin_bot.handlers import post_handlers
from shared.utils.file_updater import FileUpdater
from shared.utils.price_tracker import PriceTracker
from admin_bot.utils.posting import auto_posting, check_and_delete_outdated_posts
import asyncio
import logging
import signal
import sys
import os
from aiogram.client.session.aiohttp import AiohttpSession

# Проверка на запущенные экземпляры
PID_FILE = 'admin_bot.pid'

def check_running():
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            old_pid = int(f.read())
            try:
                os.kill(old_pid, 0)
                logging.error(f"Бот уже запущен (PID: {old_pid})")
                sys.exit(1)
            except OSError:
                pass
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def cleanup():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logging.info("Получен сигнал завершения...")
    try:
        asyncio.get_event_loop().run_until_complete(shutdown(dp))
    except Exception as e:
        logging.error(f"Ошибка при завершении: {str(e)}")
    finally:
        cleanup()
        sys.exit(0)

# Инициализация
bot = Bot(token=Config.ADMIN_BOT_TOKEN)
bot.session = AiohttpSession()
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
price_tracker = PriceTracker()

# Регистрация хендлеров
dp.include_router(post_handlers.router)


async def main():
    Config.setup_logging('admin')
    logging.info("Запуск админ бота...")
    
    try:
        check_running()
        
        file_updater = FileUpdater(
            url=Config.CSV_URL,
            local_path=Config.CSV_PATH,
            update_interval=Config.UPDATE_INTERVAL
        )
        
        # Создаем и запускаем задачи
        tasks = [
            asyncio.create_task(file_updater.check_updates()),
            asyncio.create_task(auto_posting(bot)),
            asyncio.create_task(check_and_delete_outdated_posts(bot))
        ]
        
        # Запускаем бота и задачи одновременно
        await asyncio.gather(dp.start_polling(bot), *tasks)
        
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
        cleanup()
        raise

async def shutdown(dispatcher: Dispatcher):
    """Корректное завершение работы бота"""
    logging.info("Завершение работы бота...")
    try:
        # Отменяем все задачи
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        # Закрываем соединения
        await dispatcher.storage.close()
        await bot.session.close()
    finally:
        cleanup()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    asyncio.run(main()) 