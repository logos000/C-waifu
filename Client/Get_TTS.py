import asyncio, aiohttp, aiofiles
import os, json
class Get_TTS:
    def __init__(self, max_concurrent_tasks=3):
        self.tasks_queue = asyncio.Queue()  # 使用异步队列
        self.active_tasks = set()  # 用于保存所有活跃的任务
        self.pending_files = {}  # 用于保存等待写入的文件名
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)  # 限制同时运行的任务数量

    async def tts_service(self):
        while True:
            task = await self.tasks_queue.get()  # 获取队列中的任务
            txt, filename, queue_path, file_counter = task
            task_coro = self.get_tts_wav(txt, filename, queue_path, file_counter)
            task_future = asyncio.create_task(task_coro)  # 创建任务
            self.active_tasks.add(task_future)  # 添加到活跃任务集合中
            task_future.add_done_callback(self.active_tasks.discard)  # 任务完成后从集合中移除

    async def get_tts_wav(self, txt, filename, queue_path, file_counter, language='zh'):
        global save_count
        status = ':: Now waiting TTS...'
        if txt != "嗯……":
            print(status)

        try:
            async with self.semaphore:  # 使用信号量限制并发
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
    
                        while True:
                            # 检查之前的所有文件是否已经保存
                            if save_count == file_counter - 1:
                                break
                            await asyncio.sleep(0.01)  # 等待1秒后再检查
    
                        # 写入当前文件
                        wav_path = self.pending_files[file_counter]
    
                        async with aiofiles.open(queue_path, 'a') as qf:
                            await qf.write(wav_path + '\n')
                        save_count += 1

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}") 

async def add_tts_wav(self, txt, filename, queue_path, language='zh'):
        global save_count
        status = ':: Now waiting TTS...'
        print(status)

        try:
            async with self.semaphore:  # 使用信号量限制并发
                data_ref = {
                    "text": txt,
                    "text_language": language,
                }
    
                async with aiohttp.ClientSession() as session:
                    async with session.post(settings['tts'], json=data_ref) as r:
                        wav_path = os.path.join(wav_folder, filename)
                        # 将生成的音频文件路径保存到pending_files中，等待写入
                        os.makedirs(wav_folder, exist_ok=True)
                        with open(wav_path, 'wb') as f:
                            while True:
                                wav_data = await r.content.read()  # read response content as bytes
                                if not wav_data:
                                    break
                                f.write(wav_data)
    
                        # 写入当前文件
    
                        async with aiofiles.open(queue_path, 'a') as qf:
                            await qf.write(wav_path + '\n')

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}") 

with open('config/settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)

wav_folder = '.cache'
queue_file = './play_queue.txt'
save_count = 0