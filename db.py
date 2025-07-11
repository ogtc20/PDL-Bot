import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.server_api import ServerApi
import sys

load_dotenv()
mongo_uri = os.getenv('MONGO_URI')

client = MongoClient(mongo_uri, server_api=ServerApi('1'))
db = client['pdl_bot']
matches = db['matches']
teams = db['teams']

try:
    client.admin.command('ping')
    print("You are connected to MongoDB!")
except Exception as e:
    print("Failed to connect to MongoDB:", e)
    sys.exit(1)