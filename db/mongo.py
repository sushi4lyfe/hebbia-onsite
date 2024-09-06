import os
from pymongo import MongoClient
from pymongo.collection import Collection

class MongoDB:
    client: MongoClient = None

    @staticmethod
    def initialize():
        MongoDB.client = MongoClient("mongodb+srv://jessicashu127:QnE3ZURogJZzYvEN@hebbia.acsex.mongodb.net/?retryWrites=true&w=majority&appName=hebbia&tls=true&tlsVersion=TLS1_2")
    
    @staticmethod
    def get_collection(database_name: str, collection_name: str) -> Collection:
        db = MongoDB.client[database_name]
        return db[collection_name]
    