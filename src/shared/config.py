from dotenv import load_dotenv
import os
import logging

load_dotenv()

class Config:
    # Боты
    ADMIN_BOT_TOKEN = os.getenv('ADMIN_BOT_TOKEN')
    CLIENT_BOT_TOKEN = os.getenv('CLIENT_BOT_TOKEN')
    
    # Администраторы
    ADMIN_IDS = list(map(int, os.getenv('ADMIN_IDS', '').split(',')))
    
    # Канал
    CHANNEL_ID = os.getenv('CHANNEL_ID')
    
    # CRM
    CRM_API_KEY = os.getenv('LP_CRM_API_KEY')
    CRM_DOMAIN = os.getenv('LP_CRM_DOMAIN', 'openpike.lp-crm.biz')
    
    # CSV
    CSV_URL = "https://websklad.biz.ua/wp-content/uploads/ExportWebskladCSV.csv"
    CSV_PATH = "src/ExportWebskladCSV.csv"
    UPDATE_INTERVAL = 3600  # 1 час
    
    @classmethod
    def setup_logging(cls, bot_type: str = 'main'):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{bot_type}_bot.log'),
                logging.StreamHandler()
            ]
        ) 