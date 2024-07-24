import asyncio
import aiohttp
import os
from uuid import uuid1
import soundfile as sf
import json
import aiofiles

settings = {
    'gpt': 'http://127.0.0.1:11434/api/generate',
    'tts': 'http://127.0.0.1:9880'
}
wav_folder = 'audio_files'
queue_file = 'play_queue.txt'

class TTSDownloader:
    def __init__(self):
        self.tasks_queue = asyncio.Queue()  # 使用异步队列
        self.active_tasks = set()  # 用于保存所有活跃的任务

    async def tts_service(self):
        while True:
            task = await self.tasks_queue.get()  # 获取队列中的任务
            txt, filename = task
            task_coro = self.get_tts_wav(txt, filename)
            task_future = asyncio.create_task(task_coro)  # 创建任务
            self.active_tasks.add(task_future)  # 添加到活跃任务集合中
            task_future.add_done_callback(self.active_tasks.discard)  # 任务完成后从集合中移除

    async def get_tts_wav(self, txt, filename, language='zh'):
        status = ':: Now waiting TTS...'
        print(status)

        try:
            data_ref = {
                "text": txt,
                "text_language": language,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(settings['tts'], json=data_ref) as r:
                    wav_path = os.path.join(wav_folder, filename)
                    os.makedirs(wav_folder, exist_ok=True)
                    with open(wav_path, 'wb') as f:
                        while True:
                            wav_data = await r.content.read()  # read response content as bytes
                            if not wav_data:
                                break
                            f.write(wav_data)

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

class YourClass:
    def __init__(self, tts_downloader):
        self.tts_downloader = tts_downloader
        self.file_counter = 0  # 初始化计数器

    async def get_gpt_json(self, txt):
        url = settings['gpt']
        current_sentence = ""
        sentence = ""
        context = ""
        data = {
            "model": "cielo",
            "prompt": txt,
            "stream": True
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    response.raise_for_status()

                    async for line in response.content:
                        body = json.loads(line)
                        response_part = body.get('response', '')
                        print(response_part, end='', flush=True)

                        if 'error' in body:
                            raise Exception(body['error'])

                        if body.get('done', False):
                            context = body['context']
                            print(':: Done')
                            return sentence

                        sentence += response_part

                        punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~！“#￥%’（）*+，-。、：；《=》？@【、】……——·{|}~"""
                        if response_part.strip() in punctuation:
                            if current_sentence != "":
                                print("\n")
                                filename = f"{self.file_counter:05d}_{uuid1()}.ogg"
                                task = asyncio.create_task(self.tts_downloader.tasks_queue.put((current_sentence, filename)))
                                self.tts_downloader.active_tasks.add(task)
                                task.add_done_callback(self.tts_downloader.active_tasks.discard)
                                self.file_counter += 1  # 增加计数器

                                # 将生成的音频文件路径写入播放队列文件
                                wav_path = os.path.join(wav_folder, filename)
                                async with aiofiles.open(queue_file, 'a') as qf:
                                    await qf.write(wav_path + '\n')

                                current_sentence = ""
                        else:
                            current_sentence += response_part

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        return sentence

async def initialize():
    # 清空 audio_files 文件夹
    if os.path.exists(wav_folder):
        for file in os.listdir(wav_folder):
            file_path = os.path.join(wav_folder, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
    else:
        os.makedirs(wav_folder)

    # 重新生成 play_queue.txt 文件
    if os.path.exists(queue_file):
        os.remove(queue_file)
    with open(queue_file, 'w') as f:
        pass  # 创建一个空的 play_queue.txt 文件

async def main():
    await initialize()  # 初始化
    tts_downloader = TTSDownloader()
    obj = YourClass(tts_downloader)

    # 启动 TTS 服务
    asyncio.create_task(tts_downloader.tts_service())

    ipt = "你好"
    await obj.get_gpt_json(ipt)

    # 等待所有活跃任务完成
    if tts_downloader.active_tasks:
        await asyncio.wait(tts_downloader.active_tasks)

if __name__ == "__main__":
    asyncio.run(main())
