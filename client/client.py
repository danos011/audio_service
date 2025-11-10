# client.py
import asyncio
import websockets
import os

from dotenv import load_dotenv



async def run():
    uri = "ws://localhost:8000/api/audio/ws"
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
