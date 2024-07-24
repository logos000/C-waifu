import asyncio
import aiohttp
import os
from uuid import uuid1
import soundfile as sf
import sounddevice as sd
import json

settings = {
    'gpt': 'http://127.0.0.1:11434/api/generate',
    'tts': 'http://127.0.0.1:9880'
}
wav_folder = './audio_files'

class TTSDownloader:
    def __init__(self, play_sound_service):
        self.play_sound_service = play_sound_service
        self.tasks_queue = asyncio.Queue()  # 使用异步队列
        self.active_tasks = set()  # 用于保存所有活跃的任务

    async def tts_service(self):
        while True:
            task = await self.tasks_queue.get()  # 获取队列中的任务
            task_coro = self.get_tts_wav(task)
            task_future = asyncio.create_task(task_coro)  # 创建任务
            self.active_tasks.add(task_future)  # 添加到活跃任务集合中
            task_future.add_done_callback(self.active_tasks.discard)  # 任务完成后从集合中移除

    async def get_tts_wav(self, txt, language='zh'):
        status = ':: Now waiting TTS...'
        print(status)

        try:
            data_ref = {
                "text": txt,
                "text_language": language,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(settings['tts'], json=data_ref) as r:
                    wav_path = os.path.join(wav_folder, f"{uuid1()}.wav")
                    os.makedirs(wav_folder, exist_ok=True)
                    with open(wav_path, 'wb') as f:
                        while True:
                            wav_data = await r.content.read()  # read response content as bytes
                            if not wav_data:
                                break

                            f.write(wav_data)

                    # 将生成的音频文件路径添加到播放列表
                    await self.play_sound_service.play_queue.put(wav_path)

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

class PlaySoundService:
    def __init__(self):
        self.play_queue = asyncio.Queue()  # 使用异步队列
        self.is_playing = False

    async def play_service(self):
        while True:
            wav_file = await self.play_queue.get()  # 获取队列中的音频文件路径
            await self.playsound(wav_file)

    async def playsound(self, wav_file):
        if not os.path.isfile(wav_file):
            print(f"{wav_file} does not exist")
            return

        self.is_playing = True

        try:
            data, samplerate = sf.read(wav_file)  # Read the WAV file

            if data.ndim > 1:
                # If the audio has multiple channels, take the first channel
                data = data[:, 0]

            sd.play(data, samplerate)  # Play the audio

            # Wait for the audio to finish playing
            await asyncio.sleep(data.shape[0] / samplerate)
            sd.wait()  # 等待播放完成

        except FileNotFoundError:
            print(f"File not found: {wav_file}")
        except Exception as e:
            print(f"An error occurred while playing {wav_file}: {e}")

        finally:
            self.is_playing = False

class YourClass:
    def __init__(self, tts_downloader):
        self.tts_downloader = tts_downloader

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
                                task = asyncio.create_task(self.tts_downloader.tasks_queue.put(current_sentence))
                                self.tts_downloader.active_tasks.add(task)
                                task.add_done_callback(self.tts_downloader.active_tasks.discard)
                                current_sentence = ""
                        else:
                            current_sentence += response_part

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        return sentence

async def main():
    play_sound_service = PlaySoundService()
    tts_downloader = TTSDownloader(play_sound_service)
    obj = YourClass(tts_downloader)

    # 启动 TTS 服务和播放服务
    asyncio.create_task(tts_downloader.tts_service())
    asyncio.create_task(play_sound_service.play_service())

    ipt = "Hello, World!"
    await obj.get_gpt_json(ipt)

    # 等待所有活跃任务完成
    if tts_downloader.active_tasks:
        await asyncio.wait(tts_downloader.active_tasks)

if __name__ == "__main__":
    asyncio.run(main())
