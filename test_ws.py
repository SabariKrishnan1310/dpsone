import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8001/ws/edu/dashboard/"
    async with websockets.connect(uri) as websocket:
        print("Connected")
        # send ping
        await websocket.send(json.dumps({"type": "ping"}))
        print("Waiting for response...")
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print("Received:", response)
        except asyncio.TimeoutError:
            print("No response received for ping")
        
        # Now wait for a live update while we trigger a tap
        print("Waiting for live update...")
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            print("Received Update:", response)
        except asyncio.TimeoutError:
            print("No update received")

asyncio.run(test_ws())
