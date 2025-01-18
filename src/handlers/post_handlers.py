from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.csv_handler import read_products, Product
import os
from typing import Optional
import random
import logging
import re

router = Router()

# Хранилище для текущего товара
current_product: Optional[Product] = None

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
        
        # Формируем текст поста
        text = f"📦 {product.name}\n\n"
        text += f"💰 Ціна: {product.retail_price} грн\n"
        
        description = format_description(product.description)
        
        text += f"📝 Опис:\n{description}\n\n"
        text += f"🏷 Категорія: {product.category} / {product.subcategory}\n"
        text += f"📦 Наявність: {'В наявності' if product.stock == 'instock' else 'Немає в наявності'}"
        
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="📤 Опублікувати", callback_data="post_product")]
            ]
        )
        
        global current_product
        current_product = product
        
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
        if not current_product:
            await callback.answer("❌ Товар не знайдено, спробуйте ще раз", show_alert=True)
            return
            
        # Формируем текст поста
        text = f"📦 {current_product.name}\n\n"
        text += f"💰 Ціна: {current_product.retail_price} грн\n"
        
        description = format_description(current_product.description)
        
        text += f"📝 Опис:\n{description}\n\n"
        text += f"🏷 Категорія: {current_product.category} / {current_product.subcategory}\n"
        text += f"📦 Наявність: {'В наявності' if current_product.stock == 'instock' else 'Немає в наявності'}"
        
        # Проверяем и фильтруем URL изображений
        valid_images = []
        if current_product.images:
            for url in current_product.images[:10]:
                if url.startswith(('http://', 'https://')):
                    # Удаляем пробелы и кавычки
                    clean_url = url.strip(' "\'\t\n\r')
                    valid_images.append(clean_url)
        
        # Отправляем в канал
        if valid_images:
            try:
                media = []
                for image_url in valid_images:
                    media.append(types.InputMediaPhoto(
                        media=image_url,
                        caption=text if len(media) == 0 else None
                    ))
                await callback.bot.send_media_group(
                    chat_id=os.getenv('CHANNEL_ID'),
                    media=media
                )
            except Exception as img_error:
                logging.error(f"Ошибка при отправке изображений: {str(img_error)}")
                # Если не удалось отправить с изображениями, отправляем только текст
                await callback.bot.send_message(
                    chat_id=os.getenv('CHANNEL_ID'),
                    text=text
                )
        else:
            await callback.bot.send_message(
                chat_id=os.getenv('CHANNEL_ID'),
                text=text
            )
        
        await callback.answer("✅ Товар опублікований в каналі!")
        current_product = None
        
    except Exception as e:
        logging.error(f"Ошибка при публикации: {str(e)}")
        await callback.answer(f"❌ Помилка: {str(e)}", show_alert=True) 