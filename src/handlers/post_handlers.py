from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.csv_handler import read_products, Product
import os
from typing import Optional, List
import random
import logging
import re
from utils.price_tracker import PriceTracker
from utils.crm_handler import LpCrmAPI
import asyncio

router = Router()

class ProductState:
    def __init__(self):
        self.current_product: Optional[Product] = None

product_state = ProductState()

# Инициализируем трекер цен
price_tracker = PriceTracker()

# Инициализируем API
crm_api = LpCrmAPI()

def format_description(description: str, max_length: int = 800) -> str:
    """Форматирует описание товара с учетом лимита Telegram"""
    # Разбиваем на предложения
    sentences = re.split(r'(?<=[.!?])\s+', description)
    
    formatted_text = ''
    current_length = 0
    
    for sentence in sentences:
        # Проверяем, не превысит ли добавление предложения лимит
        if current_length + len(sentence) > max_length:
            if formatted_text:
                formatted_text = formatted_text.strip()
            break
        formatted_text += sentence + ' '
        current_length += len(sentence) + 1
        
    return formatted_text.strip()

@router.message(F.text == "📦 Випадковий товар")
async def button_random_product(message: types.Message):
    await show_random_product(message)

@router.message(Command("random_product"))
async def show_random_product(message: types.Message):
    try:
        products = read_products()

        available_products = [p for p in products if p.stock == 'instock']
        
        if not available_products:
            await message.answer("❌ Немає товарів в наявності")
            return
            
        product = random.choice(available_products)
        product_state.current_product = product
        
        # Формируем текст поста
        text = f"📦 {product.name}\n\n"
        text += f"💰 Ціна: {product.retail_price} грн\n"
        
        description = format_description(product.description)
        
        text += f"📝 Опис:\n{description}\n\n"
        text += f"📦 Наявність: {'В наявності' if product.stock == 'instock' else 'Немає в наявності'}"
        
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📤 Опублікувати", callback_data="post_product")]
            ]
        )
        
        if product.images:
            media = []
            for image_url in product.images[:10]:
                media.append(types.InputMediaPhoto(
                    media=image_url,
                    caption=text if len(media) == 0 else None
                ))
            await message.answer_media_group(media=media)
            await message.answer("Оберіть дію:", reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)
            
    except Exception as e:
        await message.answer(f"❌ Помилка: {str(e)}")

@router.callback_query(F.data == "post_product")
async def post_product(callback: types.CallbackQuery):
    try:
        if not product_state.current_product:
            await callback.answer("❌ Товар не знайдено", show_alert=True)
            return
            
        # Отправляем данные в CRM
        product_data = {
            'name': product_state.current_product.name,
            'article': product_state.current_product.article,
            'price': product_state.current_product.retail_price,
            'category': product_state.current_product.category,
            'description': product_state.current_product.description
        }
        
        # Отправляем в CRM
        crm_result = await crm_api.send_order_to_crm(product_data)
        if crm_result:
            logging.info(f"Заказ успешно создан в CRM: {crm_result}")
            
        # Создаем заказ в CRM
        product_data = {
            'name': product_state.current_product.name,
            'article': product_state.current_product.article,
            'price': product_state.current_product.retail_price,
            'category': product_state.current_product.category,
            'description': product_state.current_product.description
        }
        
        await crm_api.create_order(product_data)
        
        # Проверяем изменение цены
        price_diff = price_tracker.check_price_change(
            product_state.current_product.article, 
            product_state.current_product.retail_price
        )
        
        # Формируем текст поста
        text = f"📦 {product_state.current_product.name}\n\n"
        
        # Показываем скидку только если разница больше 100 грн
        if price_diff and price_diff >= 100:
            text += f"🔥 ЗНИЖКА! Стара ціна: {product_state.current_product.retail_price + price_diff} грн\n"
            text += f"💰 Нова ціна: {product_state.current_product.retail_price} грн\n"
            text += f"📉 Економія: {price_diff} грн!\n\n"
        else:
            text += f"💰 Ціна: {product_state.current_product.retail_price} грн\n"
        
        description = format_description(product_state.current_product.description)
        
        text += f"📝 Опис:\n{description}\n\n"
        text += f"📦 Наявність: {'В наявності' if product_state.current_product.stock == 'instock' else 'Немає в наявності'}"
        
        # Проверяем и фильтруем URL изображений
        valid_images = []
        if product_state.current_product.images:
            for url in product_state.current_product.images[:10]:
                if url.startswith(('http://', 'https://')):
                    # Удаляем пробелы и кавычки
                    clean_url = url.strip(' "\'\t\n\r')
                    valid_images.append(clean_url)
        
        # Добавляем кнопку заказа
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(
                    text="🛍 Замовити", 
                    callback_data=f"order_{product_state.current_product.article}"
                )]
            ]
        )
        
        # Отправляем в канал
        if valid_images:
            try:
                # Отправляем первое фото с текстом и кнопкой
                await callback.bot.send_photo(
                    chat_id=os.getenv('CHANNEL_ID'),
                    photo=valid_images[0],
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode='HTML'
                )
                
                # Если есть дополнительные фото, отправляем их группой
                if len(valid_images) > 1:
                    media = [types.InputMediaPhoto(media=url) for url in valid_images[1:]]
                    await callback.bot.send_media_group(
                        chat_id=os.getenv('CHANNEL_ID'),
                        media=media
                    )
                    
            except Exception as img_error:
                logging.error(f"Ошибка при отправке изображений: {str(img_error)}")
                await callback.bot.send_message(
                    chat_id=os.getenv('CHANNEL_ID'),
                    text=text,
                    reply_markup=keyboard
                )
        else:
            await callback.bot.send_message(
                chat_id=os.getenv('CHANNEL_ID'),
                text=text,
                reply_markup=keyboard
            )
        
        await callback.answer("✅ Товар опублікований в каналі!")
        product_state.current_product = None
        
    except Exception as e:
        logging.error(f"Ошибка при публикации: {str(e)}")
        await callback.answer(f"❌ Помилка: {str(e)}", show_alert=True) 