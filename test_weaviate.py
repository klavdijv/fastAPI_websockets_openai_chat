import os
import dotenv

import weaviate
from weaviate.classes.config import Configure, Property, DataType


dotenv.load_dotenv()


def create_schema(client: weaviate.WeaviateClient):
    properties = [
        Property(name='actor', data_type=DataType.TEXT, index_searchable=True),
        Property(name='role', data_type=DataType.TEXT),
        Property(name='content', data_type=DataType.TEXT)
    ]

    vect_config = Configure.Vectorizer.text2vec_openai(
        base_url='http://localhost:1234/v1',
        model='nomic-ai/nomic-embed-text-v1.5-GGUF'
    )
    gen_config = Configure.Generative.openai(base_url='http://localhost:1234/v1')
    client.collections.delete('Conversation')
    client.collections.create(
        'Conversation',
        vectorizer_config=Configure.Vectorizer.text2vec_openai('ada'),
        generative_config=Configure.Generative.openai('gpt-3.5-turbo'),
        properties=properties
    )


if __name__ == '__main__':
    # client = weaviate.connect_to_embedded(
    #     version='1.25.4',
    #     headers={'X-OpenAI-Api-Key': os.environ['OPENAI_API_KEY']},
    # )
    client = weaviate.connect_to_local()
    try:
        create_schema(client)
    finally:
        client.close()
