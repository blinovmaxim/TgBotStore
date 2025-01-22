import csv
from dataclasses import dataclass
from typing import List
import html
import re
import os
import logging
from functools import lru_cache
from shared.config import Config

@dataclass
class Product:
    name: str
    article: str
    description: str
    drop_price: float
    retail_price: float
    stock: str
    images: List[str]
    category: str
    subcategory: str

def clean_html(raw_html: str) -> str:
    """Очищает HTML-теги и форматирует текст"""
    try:
        # Очищаем HTML
        cleanr = re.compile('<.*?>')
        text = re.sub(cleanr, '', raw_html)
        text = html.unescape(text).strip()
        
        # Форматируем текст
        text = re.sub(r'\s+', ' ', text)  # Убираем лишние пробелы
        text = text.replace('\n\n', '\n').strip()
        
        return text
        
    except Exception as e:
        logging.error(f"Ошибка при обработке описания: {str(e)}")
        return raw_html

def parse_price(price_str: str) -> float:
    """Парсит строку цены в число"""
    try:
        if not price_str:
            return 0
        return float(price_str.strip(' "\'').replace(',', '.').replace(' ', '') or '0')
    except (ValueError, TypeError):
        return 0

def parse_stock(stock_value: str) -> str:
    """Определяет наличие товара"""
    stock_value = str(stock_value).lower().strip(' "\'')
    
    # Числовые значения
    if stock_value.isdigit():
        return 'instock' if int(stock_value) > 0 else 'outstock'
        
    # Текстовые значения
    instock_values = ['instock', 'в наличии', '+', 'да', 'true', '1', 'yes', 'є', 'есть']
    if any(x in stock_value for x in instock_values):
        return 'instock'
        
    # Проверка диапазонов (>, ≥)
    if any(x in stock_value for x in ['>', '≥']) and any(c.isdigit() for c in stock_value):
        return 'instock'
        
    return 'outstock'

def parse_images(images_raw: str) -> List[str]:
    """Парсит строку с изображениями"""
    if not images_raw:
        return []
        
    images_raw = images_raw.strip(' "\'')
    
    # Проверяем разные разделители
    delimiters = [',', ';', '|']
    for delimiter in delimiters:
        if delimiter in images_raw:
            return [url.strip() for url in images_raw.split(delimiter) if url.strip()]
            
    # Если разделителей нет, возвращаем как одну ссылку
    return [images_raw] if images_raw else []

def calculate_retail_price(drop_price: float, retail_price: float) -> float:
    """Рассчитывает розничную цену на основе правил"""
    price_difference = retail_price - drop_price
    
    if price_difference < 500:
        return round(drop_price + 500)  # Округляем до целого числа
    else:
        return round(retail_price + 200)  # Округляем до целого числа

@lru_cache(maxsize=1)
def read_products(filename: str = None) -> List[Product]:
    try:
        filename = filename or Config.CSV_PATH
        if not os.path.exists(filename):
            logging.error(f"Файл {filename} не найден")
            return []
 
        products = []
        encodings = ['utf-8', 'windows-1251']
        
        for encoding in encodings:
            try:
                with open(filename, 'r', encoding=encoding, errors='ignore') as file:
                    reader = csv.DictReader(file, delimiter=',')
                    
                    if not reader.fieldnames or 'Название товара' not in reader.fieldnames:
                        continue
                        
                    for row in reader:
                        # Безопасное получение значений с проверкой на None
                        name = (row.get('Название товара') or '').strip()
                        if not name:  # Пропускаем товары без названия
                            continue
                            
                        category = (row.get('Категории товара') or '').strip()
                        if category and 'электронки' in category.lower():
                            continue
                            
                        drop_price = parse_price(row.get('Дроп цена для партнера'))
                        retail_price = parse_price(row.get('Рекомендовання розничная цена'))
                        calculated_price = calculate_retail_price(drop_price, retail_price)

                        product = Product(
                            name=name,
                            article=(row.get('Артикул') or '').strip(),
                            description=clean_html(row.get('Описание товара') or ''),
                            drop_price=drop_price,
                            retail_price=calculated_price,
                            stock=parse_stock(row.get('Наличие') or ''),
                            images=parse_images(row.get('Изображения') or ''),
                            category=category,
                            subcategory=(row.get('Подкатегории') or '').strip()
                        )
                        products.append(product)
                    
                    if products:  # Возвращаем только если есть товары
                        logging.info(f"Файл успешно прочитан с кодировкой {encoding}, загружено {len(products)} товаров")
                        return products
                    
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logging.error(f"Ошибка при чтении файла с кодировкой {encoding}: {str(e)}")
                continue
                
        logging.error("Не удалось прочитать файл ни с одной из доступных кодировок")
        return []
        
    except Exception as e:
        logging.error(f"Критическая ошибка при чтении файла: {str(e)}")
        return [] 