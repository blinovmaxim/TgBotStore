import re

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