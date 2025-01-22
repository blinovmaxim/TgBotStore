import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional
from shared.utils.csv_handler import read_products

class PriceTracker:
    def __init__(self, history_file: str = None):
        if history_file is None:
            history_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                "src",
                "data", 
                "price_history.json"
            )
        self.history_file = history_file
        self.price_history: Dict[str, float] = {}
        self.load_history()
    
    def load_history(self):
        """Загружает историю цен из файла"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.price_history = json.load(f)
            except Exception as e:
                logging.error(f"Ошибка при загрузке истории цен: {str(e)}")
                self.price_history = {}
    
    def save_history(self):
        """Сохраняет историю цен в файл"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.price_history, f)
        except Exception as e:
            logging.error(f"Ошибка при сохранении истории цен: {str(e)}")
    
    def check_price_change(self, article: str, current_price: float) -> Optional[float]:
        """Проверяет изменение цены и возвращает разницу"""
        if article in self.price_history:
            old_price = self.price_history[article]
            if current_price < old_price:
                return old_price - current_price
        self.price_history[article] = current_price
        self.save_history()
        return None
    
    def get_price_statistics(self) -> Dict:
        """Возвращает статистику изменения цен"""
        stats = {
            'increased': 0,  # количество повышений цен
            'decreased': 0,  # количество снижений цен
            'total_discount': 0,  # общая сумма скидок
            'avg_discount': 0  # средняя скидка
        }
        
        try:
            products = read_products()
            for product in products:
                if product.article in self.price_history:
                    old_price = self.price_history[product.article]
                    current_price = product.retail_price
                    
                    if current_price > old_price:
                        stats['increased'] += 1
                    elif current_price < old_price:
                        stats['decreased'] += 1
                        stats['total_discount'] += (old_price - current_price)
            
            if stats['decreased'] > 0:
                stats['avg_discount'] = stats['total_discount'] / stats['decreased']
                
        except Exception as e:
            logging.error(f"Ошибка при расчете статистики цен: {str(e)}")
            
        return stats 