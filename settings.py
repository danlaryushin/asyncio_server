import os

import dotenv

dotenv.load_dotenv('.env')

LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'server.log'
USER = os.getenv('USER')
PASSWORD = os.getenv('PASSWORD')
DB = os.getenv('DB')
HOST = os.getenv('HOST')
PORT = os.getenv('PORT')
