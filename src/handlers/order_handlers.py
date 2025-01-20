from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.crm_handler import LpCrmAPI
import logging
import asyncio

router = Router()
crm_api = LpCrmAPI()

class OrderStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_np = State()

async def create_order_keyboard(product_id: str) -> types.InlineKeyboardMarkup:
    return types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text="🛍 Замовити", 
                callback_data=f"order_{product_id}"
            )]
        ]
    )

@router.callback_query(lambda c: c.data.startswith('order_'))
async def process_order(callback: types.CallbackQuery, state: FSMContext):
    product_id = callback.data.split('_')[1]
    await state.update_data(product_id=product_id)
    
    await callback.message.answer(
        "Для оформлення замовлення, будь ласка, введіть ваше ПІБ:"
    )
    await state.set_state(OrderStates.waiting_for_name)

@router.message(OrderStates.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    name = message.text
    if len(name.split()) < 2:
        await message.answer("❌ Будь ласка, введіть повне ПІБ (Прізвище та Ім'я обов'язково)")
        return
        
    await state.update_data(name=name)
    await message.answer("Введіть ваш номер телефону у форматі +380XXXXXXXXX:")
    await state.set_state(OrderStates.waiting_for_phone)

@router.message(OrderStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    phone = message.text
    # Проверяем формат телефона
    if not phone.replace('+', '').isdigit() or not (phone.startswith('+380') or phone.startswith('380')):
        await message.answer("❌ Некоректний формат номера.\nБудь ласка, введіть номер у форматі +380XXXXXXXXX")
        return
        
    await state.update_data(phone=phone)
    await message.answer("Введіть номер відділення або поштомату Нової Пошти:")
    await state.set_state(OrderStates.waiting_for_np)

@router.message(OrderStates.waiting_for_np)
async def process_np(message: types.Message, state: FSMContext):
    np_number = message.text
    data = await state.get_data()
    
    order_data = {
        'product_name': data.get('product_name'),
        'product_price': data.get('product_price'),
        'client_name': data['name'],
        'phone': data['phone'],
        'nova_poshta_office': np_number,
        'source': 'TG'
    }
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            result = await crm_api.create_order(order_data)
            if result:
                await message.answer("✅ Дякуємо за замовлення! Наш менеджер зв'яжеться з вами найближчим часом.")
                break
        except Exception as e:
            if attempt == max_retries - 1:
                logging.error(f"Ошибка при создании заказа (попытка {attempt + 1}): {str(e)}")
                await message.answer("❌ Вибачте, сталася помилка. Спробуйте пізніше або зв'яжіться з нами.")
            else:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
    
    await state.clear() 