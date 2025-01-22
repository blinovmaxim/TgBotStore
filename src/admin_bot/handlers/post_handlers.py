from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from shared.utils.csv_handler import read_products, Product
from shared.utils.price_tracker import PriceTracker
import os
from typing import Optional, List
import logging
import re
import sys
from shared.utils.crm_handler import LpCrmAPI
import asyncio
from shared.config import Config
from admin_bot.context import context
from admin_bot.keyboards.admin_kb import get_admin_keyboard, get_settings_keyboard
from aiogram.types import CallbackQuery

router = Router(name='admin_handlers')

class ProductState:
    def __init__(self):
        self.current_product: Optional[Product] = None

class SettingsStates(StatesGroup):
    waiting_post_interval = State()
    waiting_csv_interval = State()
    waiting_post_format = State()

product_state = ProductState()
price_tracker = PriceTracker()
crm_api = LpCrmAPI()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("❌ У вас нет доступа к админ-панели")
        return
        
    await message.answer(
        "👋 Привіт! Я адмін-бот для керування магазином.",
        reply_markup=get_admin_keyboard()
    )

@router.message(F.text == "📊 Статистика")
async def handle_statistics(message: types.Message):
    """Обработчик кнопки статистики"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    try:
        # Получаем список товаров
        products = read_products()
        total_products = len(products)
        available_products = len([p for p in products if p.stock == 'instock'])
        
        # Получаем статистику цен
        price_stats = price_tracker.get_price_statistics()
        
        # Формируем текст статистики
        text = "📊 Статистика магазина:\n\n"
        text += f"📦 Всего товаров: {total_products}\n"
        text += f"✅ В наличии: {available_products}\n"
        text += f"❌ Нет в наличии: {total_products - available_products}\n\n"
        
        if price_stats:
            text += "💰 Статистика цен за последние 30 дней:\n"
            text += f"📈 Повышение цен: {price_stats['increased']}\n"
            text += f"📉 Снижение цен: {price_stats['decreased']}\n"
            text += f"📊 Средняя скидка: {price_stats['avg_discount']:.2f} грн\n"
        
        await message.answer(text)
        
    except Exception as e:
        logging.error(f"Ошибка при получении статистики: {str(e)}")
        await message.answer("❌ Помилка при отриманні статистики")

@router.message(F.text == "⚙️ Налаштування")
async def handle_settings(message: types.Message):
    """Обработчик кнопки настроек"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    await message.answer(
        "⚙️ Настройки бота:\n\n"
        f"⏱ Частота постів: {Config.POST_INTERVAL // 60} хвилин\n"
        f"🔄 Інтервал оновлення CSV: {Config.UPDATE_INTERVAL // 3600} годин\n",
        reply_markup=get_settings_keyboard()
    )

@router.callback_query(lambda c: c.data and c.data.startswith('settings_'))
async def handle_settings_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик callback-кнопок настроек"""
    if callback.from_user.id not in Config.ADMIN_IDS:
        await callback.answer("❌ У вас нет доступа к настройкам", show_alert=True)
        return

    setting = callback.data.split('_')[1]
    
    if setting == 'post_interval':
        await callback.message.edit_text(
            "⏱ Введіть інтервал між постами в хвилинах (від 1 до 1440):",
            reply_markup=None
        )
        await state.set_state(SettingsStates.waiting_post_interval)
    
    elif setting == 'csv_interval':
        await callback.message.edit_text(
            "🔄 Введіть інтервал оновлення CSV в годинах (від 1 до 24):",
            reply_markup=None
        )
        await state.set_state(SettingsStates.waiting_csv_interval)
    
    elif setting == 'post_format':
        await callback.message.edit_text(
            "📝 Налаштування формату постів в розробці...",
            reply_markup=None
        )
    
    await callback.answer()

@router.message(SettingsStates.waiting_post_interval)
async def process_post_interval(message: types.Message, state: FSMContext):
    """Обработчик ввода интервала постов"""
    try:
        interval = int(message.text)
        if 1 <= interval <= 1440:
            Config.POST_INTERVAL = interval * 60
            # Возвращаем клавиатуру настроек
            await message.answer(
                f"✅ Інтервал між постами встановлено: {interval} хвилин",
                reply_markup=get_admin_keyboard()
            )
            await state.clear()
        else:
            await message.answer("❌ Введіть число від 1 до 1440")
    except ValueError:
        await message.answer("❌ Введіть коректне число")

@router.message(SettingsStates.waiting_csv_interval)
async def process_csv_interval(message: types.Message, state: FSMContext):
    """Обработчик ввода интервала обновления CSV"""
    try:
        interval = int(message.text)
        if 1 <= interval <= 24:
            Config.UPDATE_INTERVAL = interval * 3600
            # Возвращаем клавиатуру настроек
            await message.answer(
                f"✅ Інтервал оновлення CSV встановлено: {interval} годин",
                reply_markup=get_admin_keyboard()
            )
            await state.clear()
        else:
            await message.answer("❌ Введіть число від 1 до 24")
    except ValueError:
        await message.answer("❌ Введіть коректне число")

@router.message(F.text == "🔄 Рестарт")
async def handle_restart(message: types.Message):
    """Обработчик кнопки рестарта"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    try:
        await message.answer("♻️ Перезапуск бота...")
        logging.info(f"Запрошен рестарт админом {message.from_user.id}")
        
        await context.shutdown()
        
        python = sys.executable
        os.execv(python, [python] + sys.argv)
        
    except Exception as e:
        logging.error(f"Ошибка при перезапуске: {str(e)}")
        await message.answer("❌ Помилка при перезапуску бота")

@router.message(F.text == "❌ Відміна")
async def handle_cancel(message: types.Message, state: FSMContext):
    """Обработчик кнопки отмены"""
    if message.from_user.id not in Config.ADMIN_IDS:
        return
        
    await state.clear()
    await message.answer(
        "🔄 Дію скасовано. Повернення до головного меню",
        reply_markup=get_admin_keyboard()
    )
