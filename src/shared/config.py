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
    CSV_PATH = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "src",
        "data",
        "ExportWebskladCSV.csv"
    )
    UPDATE_INTERVAL = 3600  # 1 час
    
    # Интервалы постинг
    POST_INTERVAL = 600  # 10 минут между постами
    
    @classmethod
    def init_directories(cls):
        """Инициализация необходимых директорий"""
        # Получаем абсолютный путь к директории src/data
        root_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "src"
        )
        data_dir = os.path.join(root_dir, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            logging.info(f"Создана директория: {data_dir}")
        
        # Инициализируем logs директорию
        logs_dir = os.path.join(root_dir, "logs")
        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)
            logging.info(f"Создана директория: {logs_dir}")
        
        # Проверяем CSV файл
        csv_path = os.path.join(data_dir, "ExportWebskladCSV.csv")
        if os.path.exists(csv_path):
            logging.info(f"CSV файл найден: {csv_path}")
        else:
            logging.warning(f"CSV файл не найден: {csv_path}")

    def setup_logging(cls, bot_type: str = 'main'):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(f'{bot_type}_bot.log'),
                logging.StreamHandler()
            ]
        ) 

    def __init__(self):
        logging.info(f"Путь к файлу CSV: {self.CSV_PATH}")
        if os.path.exists(self.CSV_PATH):
            logging.info("Файл существует")
        else:
            logging.info("Файл не найден") 

    @classmethod
    def validate_config(cls):
        required_vars = {
            'ADMIN_BOT_TOKEN': cls.ADMIN_BOT_TOKEN,
            'CLIENT_BOT_TOKEN': cls.CLIENT_BOT_TOKEN,
            'CHANNEL_ID': cls.CHANNEL_ID,
            'ADMIN_IDS': cls.ADMIN_IDS,
        }
        
        missing = [k for k, v in required_vars.items() if not v]
        if missing:
            raise ValueError(f"Отсутствуют обязательные переменные: {', '.join(missing)}") 