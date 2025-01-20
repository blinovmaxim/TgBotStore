import aiohttp
import logging
import os
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class LpCrmAPI:
    def __init__(self):
        self.api_key = os.getenv('LP_CRM_API_KEY')
        self.domain = os.getenv('LP_CRM_DOMAIN', 'openpike.lp-crm.biz')
        self.base_url = f'http://{self.domain}/api/addNewOrder.html'
        
    async def create_order(self, product_data: Dict) -> Optional[Dict]:
        """Создание заказа в CRM"""
        if not self.api_key:
            logging.error("API ключ LP-CRM не настроен")
            return None
            
        try:
            params = {
                'key': self.api_key,
                'product_name': product_data.get('product_name'),
                'product_price': product_data.get('product_price'),
                'phone': product_data.get('phone'),
                'client_name': product_data.get('client_name'),
                'nova_poshta_office': product_data.get('nova_poshta_office'),
                'source': 'TG'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, data=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        logging.info(f"Заказ успешно создан в CRM: {result}")
                        return result
                    logging.error(f"Ошибка API LP-CRM: {response.status}")
                    return None
                    
        except Exception as e:
            logging.error(f"Ошибка при создании заказа в CRM: {str(e)}")
            return None 