from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi
import ssl

load_dotenv()

# MongoDB Configuration
client = MongoClient(
    os.getenv('MONGODB_URI', 'mongodb://localhost:27017'),
    tlsCAFile=certifi.where(),
    ssl=True,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=5000,
    socketTimeoutMS=5000
)

db = client[os.getenv('MONGODB_DB', 'splitbill')]

def get_db():
    return db 