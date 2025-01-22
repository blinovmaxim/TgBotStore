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

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    print("\n") # Добавляем перенос строки для чистого вывода
    logging.info("Получен сигнал завершения...")
    try:
        # Создаем новый event loop для корректного завершения
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(shutdown())
    except Exception as e:
        logging.error(f"Ошибка при завершении: {str(e)}")
    finally:
        cleanup()
        sys.exit(0)

async def main():
    Config.setup_logging('admin')
    Config.init_directories()
    
    # Инициализация бота и диспетчера
    storage = MemoryStorage()
    bot = Bot(token=Config.ADMIN_BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутера
    dp.include_router(post_handlers.router)
    
    logging.info("Запуск админ бота...")
    
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
        
        file_updater = FileUpdater(
            url=Config.CSV_URL,
            local_path=Config.CSV_PATH,
            update_interval=Config.UPDATE_INTERVAL
        )
        
        # Создаем и запускаем задачи с обработкой ошибок
        tasks = []
        try:
            tasks = [
                asyncio.create_task(file_updater.check_updates()),
                asyncio.create_task(auto_posting(bot)),
                asyncio.create_task(check_and_delete_outdated_posts(bot))
            ]
            
            # Запускаем бота и задачи одновременно
            await asyncio.gather(dp.start_polling(bot), *tasks)
        except Exception as e:
            logging.error(f"Ошибка при запуске задач: {str(e)}")
            for task in tasks:
                task.cancel()
            raise
        
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
        cleanup()
        raise

async def shutdown():
    """Корректное завершение работы бота"""
    logging.info("Завершение работы бота...")
    try:
        # Сначала останавливаем диспетчер
        await context.dp.stop_polling()
        
        # Отменяем все задачи
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        for task in tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Закрываем соединения
        await context.shutdown()
        await context.bot.session.close()
    finally:
        cleanup()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    asyncio.run(main()) 