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
        self.pending_files = {}  # 用于保存等待写入的文件名

    async def tts_service(self):
        while True:
            task = await self.tasks_queue.get()  # 获取队列中的任务
            txt, filename, queue_path, file_counter = task
            task_coro = self.get_tts_wav(txt, filename, queue_path, file_counter)
            task_future = asyncio.create_task(task_coro)  # 创建任务
            self.active_tasks.add(task_future)  # 添加到活跃任务集合中
            task_future.add_done_callback(self.active_tasks.discard)  # 任务完成后从集合中移除

    async def get_tts_wav(self, txt, filename, queue_path, file_counter, language='zh'):
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
                    # 将生成的音频文件路径保存到pending_files中，等待写入
                    self.pending_files[file_counter] = wav_path
                    os.makedirs(wav_folder, exist_ok=True)
                    with open(wav_path, 'wb') as f:
                        while True:
                            wav_data = await r.content.read()  # read response content as bytes
                            if not wav_data:
                                break
                            f.write(wav_data)

                    global save_count
                    while True:
                        # 检查之前的所有文件是否已经保存
                        if save_count == file_counter - 1:
                            break
                        await asyncio.sleep(.1)  # 等待1秒后再检查

                    # 写入当前文件
                    wav_path = self.pending_files[file_counter]

                    async with aiofiles.open(queue_path, 'a') as qf:
                        await qf.write(wav_path + '\n')
                    save_count += 1

                    # 创建任务写入pending文件
                    #asyncio.create_task(self.write_pending_files(queue_path, file_counter))

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

#    async def write_pending_files(self, queue_path, current_counter):
#        global save_count
#        while True:
#            # 检查之前的所有文件是否已经保存
#            if save_count == current_counter - 1:
#                break
#            await asyncio.sleep(.1)  # 等待1秒后再检查
#
#        # 写入当前文件
#        wav_path = self.pending_files[current_counter]
#
#        async with aiofiles.open(queue_path, 'a') as qf:
#            await qf.write(wav_path + '\n')
#        save_count += 1
                
class YourClass:
    def __init__(self, tts_downloader):
        self.tts_downloader = tts_downloader
        self.file_counter = 1  # 初始化计数器从1开始

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
                                filename = f"{self.file_counter:05d}_{uuid1()}.wav"
                                task = asyncio.create_task(self.tts_downloader.tasks_queue.put((current_sentence, filename, queue_file, self.file_counter)))
                                self.tts_downloader.active_tasks.add(task)
                                task.add_done_callback(self.tts_downloader.active_tasks.discard)
                                self.file_counter += 1  # 增加计数器
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
    global save_count
    save_count = 0
    # 启动 TTS 服务
    asyncio.create_task(tts_downloader.tts_service())

    ipt = "你是谁"
    await obj.get_gpt_json(ipt)

    # 等待所有活跃任务完成
    if tts_downloader.active_tasks:
        await asyncio.wait(tts_downloader.active_tasks)

if __name__ == "__main__":
    asyncio.run(main())
