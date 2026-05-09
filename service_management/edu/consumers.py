import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.layers import get_channel_layer
import logging

logger = logging.getLogger(__name__)

class SchoolConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = 'edu_dashboard'
        
        await self.accept()
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        logger.info(f"WebSocket connected: {self.channel_name}")
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        logger.info(f"WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data):
        pass
    
    async def live_update(self, event):
        await self.send(text_data=json.dumps(event['data']))