from typing import Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from utils.connection_manager import ConnectionManager
from utils.base_handler import BaseHandler
from utils.handlers.generic_handler import GenericHandler
from utils.handlers.openai_chat_handler import OpenAIChatHandler

app = FastAPI()

manager: ConnectionManager = ConnectionManager()
handlers: Dict[str, BaseHandler] = {'generic': GenericHandler(manager),
                                    'openai_chat': OpenAIChatHandler(manager)}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            json_data: Dict[str, Any] = await websocket.receive_json()
            try:
                for response in get_handler(json_data).process_json(json_data):
                    await websocket.send_json(response)
            except KeyError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)


def get_handler(json_data: Dict[str, Any]) -> BaseHandler:
    handler_name: str | None = json_data.get('handler', None)
    if handler_name is None:
        raise KeyError('No handler specified')
    handler: BaseHandler | None = handlers.get(handler_name)
    if handler is None:
        raise KeyError(f'Unknown handler type: {handler_name}')
    return handler
