import asyncio
import logging
import os
import signal
import sys
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from handlers.post_handlers import router, format_description
from utils.file_updater import FileUpdater
from utils.csv_handler import read_products
from utils.price_tracker import PriceTracker
from handlers.order_handlers import router as order_router
from utils.crm_handler import LpCrmAPI
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import ClientTimeout, TCPConnector

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

# Проверка на запущенные экземпляры
PID_FILE = 'bot.pid'

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

# Заменяем на простую инициализацию бота
bot = Bot(token=os.getenv('BOT_TOKEN'))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp.include_router(router)
dp.include_router(order_router)

# Инициализируем трекер цен
price_tracker = PriceTracker()

# Инициализируем CRM handler
crm = LpCrmAPI()

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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привіт! Я бот для вашого каналу.",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="🚀 Почати роботу"), types.KeyboardButton(text="📦 Випадковий товар")],
                [types.KeyboardButton(text="📝 Створити пост"), types.KeyboardButton(text="📊 Статистика")],
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

@dp.message(F.text == "🚀 Почати роботу")
async def button_start_work(message: types.Message):
    text = (
        "🔥 Вітаю! Я допоможу вам керувати товарами та публікувати їх в каналі.\n\n"
        "Основні команди:\n"
        "📦 Випадковий товар - показати випадковий товар\n"
        "📝 Створити пост - створити новий пост\n"
        "📊 Статистика - переглянути статистику\n"
        "🔄 Перезапуск - перезапустити бота (тільки для адміна)\n\n"
        "Щоб почати, виберіть потрібну команду з меню 👇"
    )
    await message.answer(text)

async def auto_posting():
    """Автоматическая публикация товаров каждые 5 минут"""
    while True:
        try:
            products = read_products()
            available_products = [p for p in products if p.stock == 'instock']
            
            if available_products:
                product = random.choice(available_products)
                
                # Проверяем изменение цены
                price_diff = price_tracker.check_price_change(product.article, product.retail_price)
                
                # Формируем текст поста
                text = f"📦 {product.name}\n\n"
                
                # Показываем скидку только если разница больше 100 грн
                if price_diff and price_diff >= 100:
                    text += f"🔥 ЗНИЖКА! Стара ціна: {product.retail_price + price_diff} грн\n"
                    text += f"💰 Нова ціна: {product.retail_price} грн\n"
                    text += f"📉 Економія: {price_diff} грн!\n\n"
                else:
                    text += f"💰 Ціна: {product.retail_price} грн\n"
                
                description = format_description(product.description)
                text += f"📝 Опис:\n{description}\n\n"
                text += f"📦 Наявність: {'В наявності' if product.stock == 'instock' else 'Немає в наявності'}"
                
                # Проверяем и фильтруем URL изображений
                valid_images = []
                if product.images:
                    for url in product.images[:10]:
                        if url.startswith(('http://', 'https://')):
                            clean_url = url.strip(' "\'\t\n\r')
                            valid_images.append(clean_url)
                
                # Создаем кнопку с ID товара
                keyboard = types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(
                            text="🛍 Замовити", 
                            callback_data=f"order_{product.article}"  # Передаем артикул товара
                        )]
                    ]
                )
                
                # Отправляем в канал
                if valid_images:
                    try:
                        # Отправляем первое фото с текстом и кнопкой
                        await bot.send_photo(
                            chat_id=os.getenv('CHANNEL_ID'),
                            photo=valid_images[0],
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode='HTML'
                        )
                        
                        # Если есть дополнительные фото, отправляем их группой
                        if len(valid_images) > 1:
                            media = [types.InputMediaPhoto(media=url) for url in valid_images[1:]]
                            await bot.send_media_group(
                                chat_id=os.getenv('CHANNEL_ID'),
                                media=media
                            )
                            
                    except Exception as img_error:
                        logging.error(f"Ошибка при отправке изображений: {str(img_error)}")
                        await bot.send_message(
                            chat_id=os.getenv('CHANNEL_ID'),
                            text=text,
                            reply_markup=keyboard
                        )
                else:
                    await bot.send_message(
                        chat_id=os.getenv('CHANNEL_ID'),
                        text=text,
                        reply_markup=keyboard
                    )
                
                logging.info(f"Автопостинг: опубликован товар {product.name}")
            
        except Exception as e:
            logging.error(f"Ошибка автопостинга: {str(e)}")
            
        await asyncio.sleep(600)  # Меняем на 10 минут (600 секунд)

async def check_and_delete_outdated_posts():
    """Проверяет и удаляет посты с товарами не в наличии"""
    while True:
        try:
            products = read_products()
            available_products = {p.article: p for p in products if p.stock == 'instock'}
            
            # Получаем историю сообщений канала (используем правильный метод из aiogram 3.x)
            messages = await bot.get_updates()
            for update in messages:
                if update.channel_post:
                    message = update.channel_post
                    try:
                        # Ищем артикул в тексте сообщения
                        if message.text or message.caption:
                            text = message.text or message.caption
                            # Предполагаем, что артикул указан в тексте
                            for article in available_products.keys():
                                if article in text and article not in available_products:
                                    # Товар больше не в наличии, удаляем пост
                                    try:
                                        await bot.delete_message(
                                            chat_id=os.getenv('CHANNEL_ID'),
                                            message_id=message.message_id
                                        )
                                        logging.info(f"Удален пост с товаром {article} (нет в наличии)")
                                    except Exception as del_error:
                                        logging.error(f"Ошибка при удалении сообщения: {str(del_error)}")
                                    break
                    except Exception as msg_error:
                        logging.error(f"Ошибка при обработке сообщения: {str(msg_error)}")
                        continue
                    
        except Exception as e:
            logging.error(f"Ошибка при проверке устаревших постов: {str(e)}")
            
        await asyncio.sleep(172800)  # Проверяем раз в 2 дня

async def main():
    try:
        check_running()
        
        # Создаем сессию с базовыми настройками
        bot.session = AiohttpSession()
        
        file_updater = FileUpdater(
            url="https://websklad.biz.ua/wp-content/uploads/ExportWebskladCSV.csv",
            local_path="src/ExportWebskladCSV.csv",
            update_interval=120
        )
        
        tasks = [
            asyncio.create_task(file_updater.check_updates()),
            asyncio.create_task(auto_posting()),
            asyncio.create_task(check_and_delete_outdated_posts())
        ]
        
        await dp.start_polling(bot)
        
    except KeyboardInterrupt:
        logging.info("Получен сигнал завершения...")
        await shutdown(dp)
    except Exception as e:
        logging.error(f"Критическая ошибка: {str(e)}")
        cleanup()
        raise

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    asyncio.run(main()) 