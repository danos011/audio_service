# client.py
import asyncio
import websockets
import os

from dotenv import load_dotenv

try:
    load_dotenv()
except Exception as e:
    print("Энвы не считались!")


async def run():
    uri = os.environ.get("WS_URL", "ws://localhost:8000/api/audio/ws")
    print('uri', uri)
    async with websockets.connect(uri, max_size=None) as ws:
        async def sender():
            for i in range(1000):
                await ws.send(os.urandom(4096))
                await asyncio.sleep(0.01)
            await ws.send("flush")

        async def receiver():
            try:
                while True:
                    msg = await ws.recv()
                    print(msg)
            except websockets.ConnectionClosed:
                return

        await asyncio.gather(sender(), receiver())


asyncio.run(run())
