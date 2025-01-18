import asyncio
import logging
import os
import signal
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from handlers.post_handlers import router
from utils.file_updater import FileUpdater

# Загружаем переменные окружения
load_dotenv()

# Включаем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Инициализируем бота и диспетчер
bot = Bot(token=os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(router)

async def shutdown(dispatcher: Dispatcher):
    """Корректное завершение работы бота"""
    logging.info("Завершение работы бота...")
    await dispatcher.storage.close()
    await bot.session.close()

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logging.info("Получен сигнал завершения...")
    raise KeyboardInterrupt

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привіт! Я бот для вашого каналу.",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="📦 Випадковий товар")],
                [types.KeyboardButton(text="📝 Створити пост")],
                [types.KeyboardButton(text="📊 Статистика")],
                [types.KeyboardButton(text="🔄 Перезапуск")]
            ],
            resize_keyboard=True
        )
    )

@dp.message(F.text == "🔄 Перезапуск")
async def button_restart(message: types.Message):
    if str(message.from_user.id) == os.getenv('ADMIN_ID'):
        await message.answer("🔄 Перезапуск бота...")
        try:
            await shutdown(dp)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            await message.answer(f"❌ Помилка при перезапуску: {str(e)}")
    else:
        await message.answer("❌ У вас нет прав для выполнения этой команды")

async def main():
    try:
        # Инициализируем обновление файла
        file_updater = FileUpdater(
            url="https://websklad.biz.ua/wp-content/uploads/ExportWebskladCSV.csv",
            local_path="src/ExportWebskladCSV.csv",
            update_interval=172800  # 2 дня в секундах (2 * 24 * 60 * 60)
        )
        
        # Запускаем задачу обновления файла
        update_task = asyncio.create_task(file_updater.check_updates())
        
        # Запускаем бота
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logging.info("Получен сигнал завершения...")
        await shutdown(dp)
        if 'update_task' in locals():
            update_task.cancel()
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен") 