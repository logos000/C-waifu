import json, websockets
import asyncio, aiohttp, aiofiles
import os, requests
import urllib.parse, base64
from Get_TXT import *


class Config:
    config_files = {'settings': 'config/settings.json'}
    dicts = {'settings': {}}

    def __init__(self):
        try:
            with open(self.config_files['settings'], 'r', encoding='utf-8') as f:
                self.dicts['settings'] = json.load(f)
        except FileNotFoundError:
            print(f"Configuration file {self.config_files['settings']} not found.")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from the file {self.config_files['settings']}.")


    def read(self, file, key):
        try:
            return self.dicts[file][key]
        except KeyError:
            print(f"Key '{key}' not found in the '{file}' configuration.")
            return None

    def read_settings(self):
        return self.dicts['settings']

class WebSocketClient:
    def __init__(self, url):
        self.url = url
        self.websocket = None

    async def connect(self):
        self.websocket = await websockets.connect(self.url)

    async def subscribe(self, room_id):
        await self.websocket.send(json.dumps({
            "cmd": 1,
            "data": {"roomId": room_id}
        }))
        print(f"Subscribed to room {room_id}")

    async def keep_alive(self):
        while True:
            await self.websocket.send(json.dumps({
                "cmd": 0,
                "data": {}
            }))
            await asyncio.sleep(10)

    async def receive_messages(self):           #处理接受的弹幕
        async for recieve in self.websocket:
            global messages
            data = json.loads(recieve)
            data_recieve = data['data']
            cmd_recieve = data['cmd']
            if data_recieve != {}:
                
                print(f"Received message: {data}")
                match cmd_recieve:
                    case 2:
                        user_input = data_recieve[4]
                        messages.append({"role": "user", "content": user_input})
                        message = await gpt_main(messages)
                        messages.append(message)
                        if len(messages) > max_length:
                            messages.pop(0)
                    case 3:
                        gift = data_recieve['giftName']
                        audience_id = data_recieve['authorName']
                        user_input = f"请说：谢谢{audience_id}送的{gift},爱你呀"
                        messages.append({"role": "user", "content": user_input})
                        message = await gpt_main(messages)
                        messages.append(message)
                        if len(messages) > max_length:
                            messages.pop(0)
                    case _:
                        pass
                        

    async def start(self, room_id):
        await self.connect()
        await self.subscribe(room_id)

        tasks = [
            self.keep_alive(),
            self.receive_messages()
        ]

        await asyncio.gather(*tasks)

    async def close(self):
        if self.websocket:
            await self.websocket.close()

       
async def asy_main():
    client = WebSocketClient('ws://localhost:12450/api/chat')
    try:
        await client.start(room_id="32741316")  # 替换为实际的房间 ID
    finally:
        await client.close()
    #DRU5IPLOD3PC1
    #global messages
#
    #while True:
    #    user_input = input("Enter a prompt: ")
    #    if not user_input:
    #        break
    #    print()
    #    messages.append({"role": "user", "content": user_input})
    #    message = await gpt_main(messages)
    #    messages.append(message)
    #    print("\n\n")

class Main_Window():
    def __init__(self, parent=None):
            # 创建缓存文件夹
        try:
            os.mkdir(wav_folder)
        except Exception as e:
            print(".cache file already exist")

        # 清理缓存
        print(":: Cleaning cache...")
        for i in os.listdir(wav_folder):
            print(i)
            try:
                os.remove(os.path.join(wav_folder, i))
            except Exception as e:
                print(e.args)

        if os.path.exists(queue_file):
            os.remove(queue_file)
        with open(queue_file, 'w') as f:
            pass  # 创建一个空的 play_queue.txt 文件
        
            # 检查服务器连接状况
        status = ":: GPT Server | {} | {}".format(settings['gpt'], util.test_connection(settings['gpt'])) + '\n' + \
                 ":: TTS Server | {} | {}".format(settings['tts'], util.test_connection(settings['tts'])) + '\n' 
        print(status)
        self.current_wav_path = ''

    def get_current_wav_path(self):
        return self.current_wav_path


        
class Utils:

        
    def url_text_encode(self, text):
        text = urllib.parse.quote(text, 'utf-8')
        reserved_replace = [['!', '%21'], ['#', '%23'], ['$', '%24'], ['&', '%26'], ['\'', '%27'], ['(', '%28'],
                            [')', '%29'], ['*', '%2A'], ['+', '%2B'], [',', '%2C'], ['/', '%2F'], [':', '%3A'],
                            [';', '%3B'], ['=', '%3D'], ['?', '%3F'], ['@', '%40'], ['[', '%5B'], [']', '%5D']]
        for i in reserved_replace:
            text = text.replace(i[0], i[1])
        return text

    def base64_decode(self, text):
        text = base64.urlsafe_b64decode(text.encode('UTF-8')).decode('UTF-8')
        # print(text)
        return text

    def test_connection(self, url):
        try:
            r = requests.get(url=url)
            return 'OK'
        
        except Exception as e:
            return e.args


            
    def stop_thread(self, thread):
        self._async_raise(thread.ident, SystemExit)
        
        
if __name__ == '__main__':
    
    #初始化各种参数，变量
    global conf, util
    conf = Config()
    util = Utils()
    wav_folder = '.cache'
    queue_file = './play_queue.txt'
    messages = []
    max_length = 20
    settings = conf.read_settings()
      
    # 运行主程序
    main = Main_Window()
    global thread_01
    asyncio.run(asy_main())


