from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# MongoDB Configuration
client = MongoClient(os.getenv('MONGODB_URI', 'mongodb://localhost:27017'))
db = client[os.getenv('MONGODB_DB', 'splitbill')]

def get_db():
    return db 