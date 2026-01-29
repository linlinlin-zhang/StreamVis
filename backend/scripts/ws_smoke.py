import asyncio
import json

import websockets


async def main() -> None:
    uri = "ws://localhost:8000/ws/chat"
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({"content": "请画个图，展示X的趋势。定义X为净利润。Q1 X=120，Q2 X=130，Q3 X=90"}))
        await asyncio.sleep(0.05)
        await ws.send(json.dumps({"content": "再画个图：新增一个节点并连接前一个"}))
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=1.2)
            except TimeoutError:
                break
            print(msg)


asyncio.run(main())
