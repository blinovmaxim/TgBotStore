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

    def get_calculated_price(self) -> float:
        """Возвращает расчетную розничную цену"""
        return calculate_retail_price(self.drop_price, self.retail_price)

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
    stats = {
        'total_rows': 0,
        'empty_names': 0,
        'electronics': 0,
        'parse_errors': 0,
        'successful': 0
    }
    
    try:
        filename = filename or Config.CSV_PATH
        if not os.path.exists(filename):
            logging.error(f"Файл {filename} не найден")
            return []

        # Сначала прочитаем весь файл и посмотрим его размер
        file_size = os.path.getsize(filename)
        logging.info(f"Размер файла: {file_size} байт")

        all_products = []
        encodings = ['utf-8', 'windows-1251']
        
        # Читаем файл со всеми кодировками
        for encoding in encodings:
            try:
                with open(filename, 'r', encoding=encoding, errors='ignore') as file:
                    # Читаем весь файл в память
                    content = file.read()
                    lines_count = len(content.splitlines())
                    logging.info(f"Всего строк в файле с кодировкой {encoding}: {lines_count}")
                    
                    # Читаем CSV из строк
                    reader = csv.DictReader(content.splitlines(), delimiter=',')
                    
                    if not reader.fieldnames or 'Название товара' not in reader.fieldnames:
                        continue
                        
                    products_count = 0
                    for row in reader:
                        stats['total_rows'] += 1
                        
                        name = (row.get('Название товара') or '').strip()
                        if not name:
                            stats['empty_names'] += 1
                            continue
                            
                        category = (row.get('Категории товара') or '').strip()
                        if category and 'электронки' in category.lower():
                            stats['electronics'] += 1
                            continue
                            
                        article = (row.get('Артикул') or '').strip()
                        
                        try:
                            product = Product(
                                name=name,
                                article=article,
                                description=clean_html(row.get('Описание товара') or ''),
                                drop_price=parse_price(row.get('Дроп цена для партнера')),
                                retail_price=parse_price(row.get('Рекомендовання розничная цена')),
                                stock=parse_stock(row.get('Наличие') or ''),
                                images=parse_images(row.get('Изображения') or ''),
                                category=category,
                                subcategory=(row.get('Подкатегории') or '').strip()
                            )
                            all_products.append(product)
                            products_count += 1
                            stats['successful'] += 1
                        except Exception as row_error:
                            stats['parse_errors'] += 1
                            logging.error(f"Ошибка при обработке строки: {str(row_error)}")
                            continue
                            
                    if products_count > 0:
                        logging.info(f"Прочитано {products_count} товаров с кодировкой {encoding}")
                    
            except UnicodeDecodeError:
                logging.error(f"Не удалось прочитать файл с кодировкой {encoding}")
                continue
            except Exception as e:
                logging.error(f"Ошибка при чтении файла с кодировкой {encoding}: {str(e)}")
                continue

        if all_products:
            available_count = len([p for p in all_products if p.stock == 'instock'])
            total_count = len(all_products)
            logging.info(f"Всего товаров в файле: {total_count}")
            logging.info(f"Товаров в наличии: {available_count}")
            logging.info(f"""
            Статистика импорта:
            Всего строк: {stats['total_rows']}
            Пропущено пустых названий: {stats['empty_names']}
            Пропущено электроники: {stats['electronics']}
            Ошибок парсинга: {stats['parse_errors']}
            Успешно импортировано: {stats['successful']}
            """)
            return all_products
        else:
            logging.error("Не удалось прочитать товары ни с одной из кодировок")
            return []

    except Exception as e:
        logging.error(f"Критическая ошибка при чтении файла: {str(e)}")
        return [] 