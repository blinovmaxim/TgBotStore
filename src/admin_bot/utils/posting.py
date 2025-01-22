from aiogram import Bot, types
from shared.config import Config
from shared.utils.csv_handler import read_products, Product
from shared.utils.price_tracker import PriceTracker
from admin_bot.utils.text_utils import format_description
import asyncio
import logging
import random

async def auto_posting(bot: Bot):
    """Автоматическая публикация товаров"""
    while True:
        try:
            products = read_products()
            available_products = [p for p in products if p.stock == 'instock']
            
            if available_products:
                product = random.choice(available_products)
                
                # Проверяем изменение цены
                price_tracker = PriceTracker()
                price_diff = price_tracker.check_price_change(product.article, product.retail_price)
                
                # Формируем текст поста
                text = f"📦 {product.name}\n\n"
                
                # Показываем скидку только если разница больше 100 грн
                if price_diff and price_diff >= 100:
                    text += f"🔥 ЗНИЖКА! Стара ціна: {product.retail_price + price_diff} грн\n"
                    text += f"💰 Нова ціна: {product.retail_price} грн\n"
                    text += f"📉 Економія: {price_diff} грн!\n\n"
                else:
                    text += f"💰 Ціна: {product.retail_price} грн\n\n"
                
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
                            chat_id=Config.CHANNEL_ID,
                            photo=valid_images[0],
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode='HTML'
                        )
                        
                        # Если есть дополнительные фото, отправляем их группой
                        if len(valid_images) > 1:
                            media = [types.InputMediaPhoto(media=url) for url in valid_images[1:]]
                            await bot.send_media_group(
                                chat_id=Config.CHANNEL_ID,
                                media=media
                            )
                            
                    except Exception as img_error:
                        logging.error(f"Ошибка при отправке изображений: {str(img_error)}")
                        await bot.send_message(
                            chat_id=Config.CHANNEL_ID,
                            text=text,
                            reply_markup=keyboard
                        )
                else:
                    await bot.send_message(
                        chat_id=Config.CHANNEL_ID,
                        text=text,
                        reply_markup=keyboard
                    )
                
                logging.info(f"Автопостинг: опубликован товар {product.name}")
                
        except Exception as e:
            logging.error(f"Ошибка автопостинга: {str(e)}")
        #ставим время( частоту ) постов  - 10 минут
        await asyncio.sleep(Config.POST_INTERVAL)

async def check_and_delete_outdated_posts(bot: Bot):
    """Проверка и удаление устаревших постов"""
    while True:
        try:
            products = read_products()
            available_products = {p.article: p for p in products if p.stock == 'instock'}
            
            # Получаем последние сообщения из канала
            messages = await bot.get_updates(
                offset=-100,  # Получаем последние 100 сообщений
                allowed_updates=['channel_post']
            )
            
            for update in messages:
                if update.channel_post:
                    message = update.channel_post
                    try:
                        text = message.text or message.caption
                        if text:
                            for article in available_products.keys():
                                if article in text and article not in available_products:
                                    try:
                                        await bot.delete_message(
                                            chat_id=Config.CHANNEL_ID,
                                            message_id=message.message_id
                                        )
                                        logging.info(f"Удален пост с товаром {article}")
                                    except Exception as del_error:
                                        logging.error(f"Ошибка удаления: {str(del_error)}")
                    except Exception as e:
                        logging.error(f"Ошибка обработки сообщения: {str(e)}")
                    
        except Exception as e:
            logging.error(f"Ошибка проверки постов: {str(e)}")
        await asyncio.sleep(Config.UPDATE_INTERVAL)