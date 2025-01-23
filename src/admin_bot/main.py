from aiogram import Bot, Dispatcher
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
import random
from admin_bot.context import context
from admin_bot.keyboards.admin_kb import get_admin_keyboard

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

async def shutdown():
    """Корректное завершение бота"""
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    [task.cancel() for task in tasks]
    await asyncio.gather(*tasks, return_exceptions=True)
    
def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logging.info("Получен сигнал завершения...")
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(shutdown())
        loop.stop()
    except Exception as e:
        logging.error(f"Ошибка при завершении: {str(e)}")
    finally:
        cleanup()
        sys.exit(0)

async def main():
    Config.setup_logging('admin')
    Config.init_directories()
    
    storage = MemoryStorage()
    bot = Bot(token=Config.ADMIN_BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    dp.include_router(post_handlers.router)
    
    logging.info("Запуск админ бота...")
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        check_running()
        
        # Отправляем клавиатуру админам
        for admin_id in Config.ADMIN_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    "Бот запущен. Используйте клавиатуру для управления:",
                    reply_markup=get_admin_keyboard()
                )
            except Exception as e:
                logging.error(f"Не удалось отправить клавиатуру админу {admin_id}: {e}")
        
        # Сначала инициализируем и запускаем FileUpdater
        file_updater = FileUpdater(
            url=Config.CSV_URL,
            local_path=Config.CSV_PATH,
            update_interval=Config.UPDATE_INTERVAL
        )
        
        # Выполняем первичную проверку
        if not await file_updater.initial_check():
            logging.error("Не удалось инициализировать файл товаров")
            return
            
        # Запускаем все задачи параллельно
        tasks = [
            dp.start_polling(bot),
            auto_posting(bot),
            check_and_delete_outdated_posts(bot),
            file_updater.check_updates()
        ]
        
        await asyncio.gather(*tasks)
            
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
        cleanup()
        raise

if __name__ == "__main__":
    asyncio.run(main()) 