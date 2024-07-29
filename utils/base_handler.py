from typing import Dict, Any
from .connection_manager import ConnectionManager


class BaseHandler:
    def __init__(self, connection_manager: ConnectionManager):
         self.connection_manager = connection_manager

    def process_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        yield {}
