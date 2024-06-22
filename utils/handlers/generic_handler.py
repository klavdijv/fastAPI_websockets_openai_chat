from typing import Dict, Any

from fastapi import WebSocket

from ..base_handler import BaseHandler


class GenericHandler(BaseHandler):
    def process_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        del json_data['handler']
        return {'generic': True, 'data': json_data}
