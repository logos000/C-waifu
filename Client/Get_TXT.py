import json, uuid
import asyncio, aiohttp, aiofiles
from Get_TTS import *
class gpt_TXT:
    def __init__(self, tts_downloader):
        self.tts_downloader = tts_downloader

        
    async def get_gpt_json(self, messages):
        global file_counter
        flag = True
        url = settings['gpt']
        punctuation = r"""?!,.;；！，。？……"""
        current_sentence = ""
        message = {}
        output = ""
        gpt_data = {
            "model": "cielo",
            "messages": messages,
            "stream": True
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=gpt_data) as response:
                response.raise_for_status()
                output = "" 
                async for line in response.content:
                    body = json.loads(line)
                    if "error" in body:
                        raise Exception(body["error"])
                    
                    if body.get("done") is False:
                        message = body.get("message", "")
                        content = message.get("content", "")
                        output += content
                        # the response streams one token at a time, print that as we receive it
                        print(content, end="", flush=True)
                                                  
                        if (content.strip() in punctuation) and (len(current_sentence) > 6):
                            print("\n")
                            filename = f"{file_counter:05d}_{uuid.uuid1()}.wav"
                            task = asyncio.create_task(self.tts_downloader.tasks_queue.put((current_sentence, filename, queue_file, file_counter)))
                            self.tts_downloader.active_tasks.add(task)
                            task.add_done_callback(self.tts_downloader.active_tasks.discard)
                            file_counter += 1  # 增加计数器
                            current_sentence = ""
                            
                        else:
                            current_sentence += content 
                            if flag and (len(current_sentence) > 6):  #防止第一句话过长，缩短反应时间
                                filename = f"{file_counter:05d}_{uuid.uuid1()}.wav"
                                task = asyncio.create_task(self.tts_downloader.tasks_queue.put(("嗯……", filename, queue_file, file_counter)))
                                self.tts_downloader.active_tasks.add(task)
                                task.add_done_callback(self.tts_downloader.active_tasks.discard)
                                file_counter += 1  # 增加计数器
                                flag = False    
                    if body.get("done", False):
                        message["content"] = output
                        return message
                    

    
async def gpt_main(ipt = "你好"):
    tts_downloader = Get_TTS()
    obj = gpt_TXT(tts_downloader)

    # 启动 TTS 服务
    asyncio.create_task(tts_downloader.tts_service())
    ans = await obj.get_gpt_json(ipt)

    # 等待所有活跃任务完成
    if tts_downloader.active_tasks:
        await asyncio.wait(tts_downloader.active_tasks)
    return ans

with open('config/settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)
file_counter = 1  # 初始化计数器从1开始  
queue_file = './play_queue.txt'
messages = [] 
