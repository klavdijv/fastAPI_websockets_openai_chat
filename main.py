from typing import  Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from utils.connection_manager import ConnectionManager
from utils.base_handler import BaseHandler
from utils.handlers.generic_handler import GenericHandler

app = FastAPI()

manager: ConnectionManager = ConnectionManager()
handlers: Dict[str, BaseHandler] = {'generic': GenericHandler(manager)}

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            json_data: Dict[str, Any] = await websocket.receive_json()
            await websocket.send_json(handlers[json_data['handler']].process_json(json_data))
    except WebSocketDisconnect:
        manager.disconnect(websocket)
