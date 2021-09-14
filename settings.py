from datetime import datetime
from tinydb import TinyDB

AWS_SERVER_PUBLIC_KEY = ''  # AWS PUBLIC KEY
AWS_SERVER_SECRET_KEY = ''  # AWS SECRET KEY
TOKEN = ''  # TELEGRAM TOKEN
DATE_FORMAT = '%d/%m/%y'
EPOC = datetime(1970, 1, 1)
PHOTO_DB_PATH = 'photo_details.json'
PHOTOS_DB_TABLE = TinyDB(PHOTO_DB_PATH)
PHOTO_TABLE = PHOTOS_DB_TABLE.table('photos')