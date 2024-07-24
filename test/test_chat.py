import asyncio
import websockets
import json

async def subscribe(ws):
    # 订阅直播间
    await ws.send(json.dumps({
        "cmd": 1,
        "data": {"roomId": 32741316}
    }))
    print("Subscribed to room")

async def keep_alive(ws):
    while True:
        await ws.send(json.dumps({
            "cmd": 0,
            "data": {}
        }))
        await asyncio.sleep(10)

async def receive_messages(ws):
    async for message in ws:
        data = json.loads(message)
        print(f"Received message: {data}")

async def main():
    async with websockets.connect('ws://localhost:12450/api/chat') as ws:
        await subscribe(ws)

        # 启动两个任务，一个用于保持连接，一个用于接收消息
        keep_alive_task = asyncio.create_task(keep_alive(ws))
        receive_messages_task = asyncio.create_task(receive_messages(ws))

        # 等待两个任务完成（实际上是永久运行，除非异常发生）
        await asyncio.gather(keep_alive_task, receive_messages_task)

# 运行主程序
asyncio.run(main())
