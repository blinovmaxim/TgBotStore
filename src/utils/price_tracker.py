import json
import os
import logging
from datetime import datetime
from typing import Dict, Optional

class PriceTracker:
    def __init__(self, history_file: str = 'price_history.json'):
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