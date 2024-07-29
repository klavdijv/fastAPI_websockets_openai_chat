import os
import weaviate
import dotenv

from typing import Dict, List
from weaviate.classes.config import Configure, Property, DataType


dotenv.load_dotenv()

class WeaviateConnectionManager:
    def __init__(self):
        self.client = weaviate.connect_to_local(
            headers={'X-OpenAI-Api-Key': os.environ['OPENAI_API_KEY']}
        )
        self.collections: Dict[str, weaviate.collections.Collection] = {}

    def __del__(self):
        self.client.close()

    def _get_collection(self, collection_name: str) -> weaviate.collections.Collection:
        if not self.client.collections.exists(collection_name):
            self.create_collection(collection_name)
        return self.client.collections.get(collection_name)

    def create_collection(self, collection_name: str):
        self.client.collections.create(
            name=collection_name,
            vectorizer_config=Configure.Vectorizer.text2vec_openai(),
            properties=[
                Property(name='role', data_type=DataType.TEXT),
                Property(name='content', data_type=DataType.TEXT),
            ]
        )

    def delete_collection(self, collection_name: str):
        self.client.collections.delete(collection_name)

    def get_collection(self, collection_name: str):
        return WeaviateCollection(self, collection_name)


class WeaviateCollection:
    def __init__(self, connection_manager: WeaviateConnectionManager,  collection_name: str):
        self.collection: weaviate.collections.Collection = connection_manager._get_collection(collection_name)

    def get_recent(self, limit: int=10) -> List[Dict[str, str]]:
        res = self.collection.query.fetch_objects(limit=limit)
        return [obj.properties for obj in res.objects]

    def get_nearest(self, query: str, limit: int=10) -> List[Dict[str, str]]:
        res = self.collection.query.near_text(query=query, limit=limit)
        return [obj.properties for obj in res.objects]

    def get_messages(self, query: str, recent_limit: int=10, nearest_limit: int=10) -> List[Dict[str, str]]:
        res: List[Dict[str, str]] = self.get_nearest(query, nearest_limit)
        res_content: List[str] = [r['content'] for r in res]

        for recent_message in self.get_recent(recent_limit):
            if recent_message['content'] not in res_content:
                res.append(recent_message)

        return res

    def save(self, messages: List[Dict[str, str]]):
        self.collection.data.insert_many(messages)
