import asyncio
import os
import soundfile as sf
import sounddevice as sd
import aiofiles

queue_file = 'play_queue.txt'

class PlaySoundService:
    def __init__(self):
        self.is_playing = False
        self.played_files = set()  # 使用集合来记录已播放的文件

    async def play_service(self):
        while True:
            wav_file = await self.get_next_file()  # 获取下一个音频文件路径
            if wav_file:
                await self.playsound(wav_file)
            else:
                await asyncio.sleep(0.01)  # 如果没有文件，等待一秒钟

    async def get_next_file(self):
        try:
            async with aiofiles.open(queue_file, 'r') as qf:
                lines = await qf.readlines()

            for line in lines:
                wav_file = line.strip()
                if wav_file not in self.played_files:
                    self.played_files.add(wav_file)
                    return wav_file

            return None
        except FileNotFoundError:
            return None

    async def playsound(self, wav_file):
        if not os.path.isfile(wav_file):
            print(f"{wav_file} does not exist")
            return
        print(wav_file)
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

async def main():
    play_sound_service = PlaySoundService()
    await play_sound_service.play_service()

if __name__ == "__main__":
    asyncio.run(main())
