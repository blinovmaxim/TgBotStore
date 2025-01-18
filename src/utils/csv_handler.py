import csv
from dataclasses import dataclass
from typing import List
import html
import re
import os
import logging

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
    cleanr = re.compile('<.*?>')
    text = re.sub(cleanr, '', raw_html)
    return html.unescape(text).replace('\n\n', '\n').strip()

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
    images = []
    
    # Определяем разделитель
    for delimiter in ['","', ',', ';']:
        if delimiter in images_raw:
            images = [url.strip(' "\'') for url in images_raw.split(delimiter)]
            break
    else:
        images = [images_raw]
        
    return [url for url in images if url.startswith(('http://', 'https://'))]

def read_products(filename: str = None) -> List[Product]:
    try:
        if not filename:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            filename = os.getenv('CSV_FILE', os.path.join(base_dir, 'ExportWebskladCSV.csv'))
            
        if not os.path.exists(filename):
            logging.error(f"Файл {filename} не знайдено")
            return []
            
        products = []
        skipped_empty = 0
        skipped_no_name = 0
        skipped_no_price = 0
        error_count = 0
        
        with open(filename, 'r', encoding='utf-8-sig') as file:
            total_lines = sum(1 for line in file)
            file.seek(0)
            
            reader = csv.DictReader(file, delimiter=',')
            headers = reader.fieldnames
            logging.info(f"Заголовки CSV: {headers}")
            
            for row in reader:
                try:
                    # Проверяем валидность строки
                    if not row or not any(row.values()):
                        skipped_empty += 1
                        continue
                        
                    name = row.get('Название товара', '').strip(' "\'')
                    if not name:
                        skipped_no_name += 1
                        continue
                        
                    # Проверяем цену более тщательно
                    price_str = row.get('Рекомендовання розничная цена', '').strip(' "\'')
                    if not price_str:
                        skipped_no_price += 1
                        continue
                        
                    try:
                        retail_price = float(price_str.replace(',', '.').replace(' ', ''))
                        if retail_price <= 0:
                            skipped_no_price += 1
                            continue
                    except ValueError:
                        skipped_no_price += 1
                        continue
                        
                    product = Product(
                        name=name,
                        article=row.get('Артикул', '').strip(' "\''),
                        description=clean_html(row.get('Описание товара', '').strip(' "\'')),
                        drop_price=parse_price(row.get('Дроп цена для партнера')),
                        retail_price=retail_price,
                        stock=parse_stock(row.get('Наличие')),
                        images=parse_images(row.get('Изображения')),
                        category=row.get('Категории товара', '').strip(' "\''),
                        subcategory=row.get('Подкатегории', '').strip(' "\'')
                    )
                    
                    products.append(product)
                        
                except Exception as e:
                    error_count += 1
                    logging.error(f"Помилка при обробці рядка: {str(e)}")
                    continue
                    
        logging.info(f"Всього рядків у файлі: {total_lines}")
        logging.info(f"Пропущено пустих рядків: {skipped_empty}")
        logging.info(f"Пропущено без назви: {skipped_no_name}")
        logging.info(f"Пропущено без ціни: {skipped_no_price}")
        logging.info(f"Помилок обробки: {error_count}")
        logging.info(f"Успішно оброблено товарів: {len(products)}")
        logging.info(f"Товарів в наявності: {len([p for p in products if p.stock == 'instock'])}")
        
        return products
        
    except Exception as e:
        logging.error(f"Помилка при читанні файлу {filename}: {str(e)}")
        return [] 