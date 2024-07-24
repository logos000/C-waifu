import asyncio
import os
import sounddevice as sd
import pyogg
import aiofiles

queue_file = 'play_queue.txt'
buffer_size = 4096  # 每次读取的字节数

class PlaySoundService:
    def __init__(self):
        self.is_playing = False

    async def play_service(self):
        while True:
            ogg_file = await self.get_next_file()
            if ogg_file:
                await self.playsound(ogg_file)
            else:
                await asyncio.sleep(1)

    async def get_next_file(self):
        try:
            async with aiofiles.open(queue_file, 'r') as qf:
                lines = await qf.readlines()

            if not lines:
                return None

            ogg_file = lines[0].strip()
            async with aiofiles.open(queue_file, 'w') as qf:
                await qf.writelines(lines[1:])

            return ogg_file
        except FileNotFoundError:
            return None

    async def playsound(self, ogg_file):
        if not os.path.isfile(ogg_file):
            print(f"{ogg_file} does not exist")
            return

        self.is_playing = True
        try:
            # 使用 pyogg 解码 OGG 文件
            vorbis_file = pyogg.VorbisFile(ogg_file)
            sample_rate = vorbis_file.frequency
            audio_data = vorbis_file.as_array()

            stream = sd.OutputStream(samplerate=sample_rate, channels=audio_data.shape[1])
            stream.start()
            
            chunk_size = buffer_size // audio_data.itemsize // audio_data.shape[1]
            for start_idx in range(0, len(audio_data), chunk_size):
                end_idx = start_idx + chunk_size
                stream.write(audio_data[start_idx:end_idx])

            stream.stop()
            stream.close()

        except Exception as e:
            print(f"An error occurred while playing {ogg_file}: {e}")

        finally:
            self.is_playing = False

async def main():
    play_sound_service = PlaySoundService()
    await play_sound_service.play_service()

if __name__ == "__main__":
    asyncio.run(main())
