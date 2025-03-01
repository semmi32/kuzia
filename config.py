import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# Получаем значения из переменных окружения или используем значения по умолчанию
API_ID = int(os.getenv('API_ID', 12345678))  # Замените на ваш API_ID
API_HASH = os.getenv('API_HASH', 'ваш_api_hash')  # Замените на ваш API_HASH
ALLOWED_USER_ID = int(os.getenv('ALLOWED_USER_ID', 1234567890))  # Замените на ваш ID