import pymongo
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()


class AtlasClient ():

   def __init__ (self, altas_uri=os.environ.get("ATLAS_URI"), dbname='test'):
       self.mongodb_client = MongoClient(altas_uri)
       self.database = self.mongodb_client[dbname]

   def ping(self):
       self.mongodb_client.admin.command('ping')

   def get_collection(self, collection_name):
       collection = self.database[collection_name]
       return collection

   def find(self, collection_name, filter = {}, limit=0):
       collection = self.database[collection_name]
       items = list(collection.find(filter=filter, limit=limit))
       return items
   
   def update(self, collection_name, filter, update):
       collection = self.database[collection_name]
       collection.update_one(filter, update)
       return True
   
   def insert(self, collection_name, data):
       collection = self.database[collection_name]
       id = collection.insert_one(data).inserted_id
       return id
