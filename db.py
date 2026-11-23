import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("MONGO_DATABASE")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

# Verify the MongoDB connection
client.admin.command("ping")

db = client[DATABASE_NAME]

print(f"Connected to MongoDB database: {DATABASE_NAME}")
print("Collections:", db.list_collection_names())