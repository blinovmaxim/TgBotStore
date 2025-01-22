from aiogram import types

def get_admin_keyboard() -> types.ReplyKeyboardMarkup:
    """Основная клавиатура администратора"""
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [
                types.KeyboardButton(text="📊 Статистика"),
                types.KeyboardButton(text="⚙️ Налаштування")
            ],
            [
                types.KeyboardButton(text="🔄 Рестарт"),
                types.KeyboardButton(text="❌ Відміна")
            ]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_settings_keyboard() -> types.InlineKeyboardMarkup:
    """Клавиатура настроек"""
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="⏱ Інтервал постів",
                    callback_data="settings_post_interval"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🔄 Інтервал CSV",
                    callback_data="settings_csv_interval"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="📝 Формат постів",
                    callback_data="settings_post_format"
                )
            ]
        ]
    )
    return keyboard 