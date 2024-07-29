import os
import dotenv

from typing import Dict, Any
from openai import OpenAI
from ..base_handler import BaseHandler
from ..connection_manager import ConnectionManager
from ..weaviate_connection_manager import WeaviateConnectionManager, WeaviateCollection


dotenv.load_dotenv()


class OpenAIChatHandler(BaseHandler):
    OPENAI_MODEL = 'gpt-4o-mini'
    def __init__(self, connection_manager: ConnectionManager):
        super().__init__(connection_manager)
        self.open_ai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    def process_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        messages: Dict[str, str] = json_data['messages']
        stream = self.open_ai.chat.completions.create(
            model=self.OPENAI_MODEL,
            messages=messages,
            stream=True
        )
        for chunk in stream:
            message: str|None = chunk.choices[0].delta.content
            print(message)
            if message is not None:
                yield {'message': message, 'end': False}
        yield {'message': '', 'end': True}


class OpenAIChatMemoryHandler(OpenAIChatHandler):
    def __init__(self, connection_manager: ConnectionManager, weaviate_manager: WeaviateConnectionManager):
        super().__init__(connection_manager)
        self.weaviate_manager: WeaviateConnectionManager = weaviate_manager

    def process_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        character_name: str = self._escape_name(json_data['character_name'])
        messages: Dict[str, str] = json_data['messages']
        collection: WeaviateCollection = self.weaviate_manager.get_collection(f'chat_hist_{character_name}')
        context_messages: List(Dict[str, str]) = collection.get_messages(query=messages[-1]['content'])
        json_data['messages'] = [messages[0]] + context_messages + messages[1:]
        response: str = ''

        for message in super().process_json(json_data):
            yield message
            response += message['message']

        messages_to_save: List[Dict[str, str]] = messages[1:] + [{'role': 'assistant', 'content': response}]
        collection.save(messages_to_save)

    def _escape_name(self, name: str) -> str:
        name = name.strip()
        name = name.replace(',', '')
        name = name.replace(' ', '_')
        return name
