import aiohttp
import asyncio
import json
import os
import uuid

# Assuming settings dictionary is defined somewhere in your project
# settings = {'gpt': 'your_gpt_url', 'tts': 'your_tts_url'}
# wav_folder = 'your_wav_folder_path'
wav_folder = './audio_files'
settings = {
    'gpt': "http://127.0.0.1:11434/api/generate",
    'tts': 'http://127.0.0.1:9880',
}
class GPTClient:
    def __init__(self):
        self.audio_queue = []

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
                            yield sentence  # Return the latest sentence
                            print(':: Done')
                            return

                        sentence += response_part
                        yield sentence  # Return the latest sentence
                        punctuation = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~！“#￥%’（）*+，-。、：；《=》？@【、】……——·{|}~"""
                        if response_part.strip() in punctuation:
                            if current_sentence != "":
                                print("\n")
                                task = asyncio.create_task(self.get_tts_wav(current_sentence))
                                current_sentence = ""
                        else:
                            current_sentence += response_part

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

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
                    if r.status != 200:
                        raise aiohttp.ClientResponseError(status=r.status, message=r.reason)

                    wav_path = os.path.join(wav_folder, f"{uuid.uuid1()}.wav")
                    os.makedirs(wav_folder, exist_ok=True)

                    with open(wav_path, 'wb') as f:
                        while True:
                            wav_data = await r.content.read(1024)  # Adjust chunk size as needed
                            if not wav_data:
                                break
                            f.write(wav_data)

                    self.audio_queue.append(wav_path)
                    print(f"Downloaded TTS audio to: {wav_path}")

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

    async def manage_audio_queue(self):
        while True:
            if self.audio_queue:
                wav_file = self.audio_queue.pop(0)
                print(f"Playing sound from {wav_file}")
                # Here you can call a method to play the audio file
                # For example:
                # await self.playsound(wav_file)
            await asyncio.sleep(1)  # Adjust as needed

    # Placeholder method for playing audio (not implemented in this example)
    async def playsound(self, wav_file):
        print(f"Simulating playback of {wav_file}")

async def main():
    client = GPTClient()
    text_to_process = "Start conversation with GPT"
    async for sentence in client.get_gpt_json(text_to_process):
        # Process each sentence as needed
        pass

if __name__ == "__main__":
    asyncio.run(main())