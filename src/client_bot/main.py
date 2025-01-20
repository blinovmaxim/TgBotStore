from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from shared.config import Config
from client_bot.handlers import order_handlers
import asyncio
import logging
import signal
import sys
import os

# Проверка на запущенные экземпляры
PID_FILE = 'client_bot.pid'

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

# Инициализация
bot = Bot(token=Config.CLIENT_BOT_TOKEN)
bot.session = AiohttpSession()
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация хендлеров
dp.include_router(order_handlers.router)

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

async def main():
    Config.setup_logging('client')
    logging.info("Запуск клиентского бота...")
    
    try:
        check_running()
        await dp.start_polling(bot)
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