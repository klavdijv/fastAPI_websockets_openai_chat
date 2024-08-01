import os
import dotenv

from typing import Dict, Any, List, Tuple
from openai import OpenAI, Stream
from openai.types.chat.chat_completion_chunk import ChatCompletionChunk
from ..base_handler import BaseHandler
from ..connection_manager import ConnectionManager
from ..weaviate_connection_manager import WeaviateConnectionManager, WeaviateCollection


dotenv.load_dotenv()


class ChunkProcessor:
    MODE_CONTENT: int = 1
    MODE_TOOL_CALL: int = 2
    MODE_UNKNOWN = 0
    def __init__(self):
        self.func_name: str = ''
        self.arguments: str = ''
        self.call_id: str = ''
        self.func_index: int = 0
        self.content: str = ''
        self.mode = self.MODE_UNKNOWN

    def process_chunk(self, chunk: ChatCompletionChunk) -> Dict[str, Any]|None:
        if chunk.choices[0].delta.content is not None:
            self.mode = self.MODE_CONTENT
            return self.process_content(chunk)
        elif chunk.choices[0].delta.tool_calls is not None:
            self.mode = self.MODE_TOOL_CALL
            return self.process_tool_calls(chunk)
        if self.mode == self.MODE_CONTENT:
            return {'message': '', 'end': True}
        if self.mode == self.MODE_TOOL_CALL and self.func_name:
            return {'function': self.func_name, 'arguments': self.arguments, 'id': self.call_id}
        return None

    def process_content(self, chunk: ChatCompletionChunk) -> Dict[str, Any]|None:
        message: str|None = chunk.choices[0].delta.content
        return {'message': message, 'end': False} if message is not None else None

    def process_tool_calls(self, chunk: ChatCompletionChunk) -> Dict[str, Any]|None:
        result: Dict[str, Any]|None = None
        tool_call = chunk.choices[0].delta.tool_calls[0]
        func_delta = chunk.choices[0].delta.tool_calls[0].function
        if tool_call.index != self.func_index:
            result = {'function': self.func_name, 'arguments': self.arguments, 'id': self.call_id}
            self.func_index = tool_call.index
            self.func_name = ''
            self.call_id = ''
            self.arguments = ''

        if tool_call.id is not None:
            self.call_id = tool_call.id
        if func_delta.name is not None:
            self.func_name = func_delta.name
        if func_delta.arguments:
            self.arguments += func_delta.arguments
        return result


class OpenAIChatHandler(BaseHandler):
    OPENAI_MODEL = 'gpt-4o-mini'
    def __init__(self, connection_manager: ConnectionManager):
        super().__init__(connection_manager)
        self.open_ai = OpenAI(api_key=os.environ['OPENAI_API_KEY'])

    def process_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        processor: ChunkProcessor = ChunkProcessor()
        messages: Dict[str, str] = json_data['messages']
        tools: List = json_data.get('tools')

        stream = self.open_ai.chat.completions.create(
            model=self.OPENAI_MODEL,
            messages=messages,
            tools=tools,
            stream=True
        )
        for chunk in stream:
            result: Dict[str, Any]|None = processor.process_chunk(chunk)
            if result is not None:
                yield result
        yield {'finished': True}
        #     message: str|None = chunk.choices[0].delta.content
        #     print(message)
        #     if message is not None:
        #         yield {'message': message, 'end': False}
        # yield {'message': '', 'end': True}

    def _process_text_stream(self, stream: Stream) -> Dict[str, Any]:
        pass

    def _process_tool_stream(self, stream: Stream) -> List[Tuple[str, Dict[str, str]]]:
        funcs = []
        args = []
        func_name = ''
        arguments = ''
        for chunk in stream:
            if chunk.choices[0].delta.tool_calls is not None:
                func_delta = chunk.choices[0].delta.tool_calls[0].function
                if func_delta.name is not None:
                    func_name = func_delta.name
                    funcs.append(func_name)
                    if arguments:
                        args.append(arguments)
                if func_delta.arguments:
                    arguments += func_delta.arguments
            else:
                args.append(arguments)
        return list(zip(funcs, args))

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

        for result in super().process_json(json_data):
            yield result
            if 'message' in result:
                response += result['message']

        if response:
            messages_to_save: List[Dict[str, str]] = messages[1:] + [{'role': 'assistant', 'content': response}]
            collection.save(messages_to_save)

    def _escape_name(self, name: str) -> str:
        name = name.strip()
        name = name.replace(',', '')
        name = name.replace(' ', '_')
        return name
