import json
from channels.generic.websocket import AsyncWebsocketConsumer

class LiveAttendanceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that streams live attendance taps to connected clients.
    """

    async def connect(self):
        """
        Accept the connection and join the school's live attendance group.
        Expects URL: ws://.../ws/attendance/<school_id>/
        """
        self.school_id = self.scope['url_route']['kwargs']['school_id']
        self.group_name = f"school_{self.school_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        print(f"WebSocket connected: Live Attendance for school {self.school_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        print(f"WebSocket disconnected: school {self.school_id}")

    async def receive(self, text_data=None, bytes_data=None):
        pass

    async def tap_event(self, event):
        """
        Receives 'tap_event' from backend (tasks.py) and forwards to browser.
        """
        await self.send(text_data=json.dumps(event["message"]))
