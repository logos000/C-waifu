import asyncio
import os
import soundfile as sf
import sounddevice as sd
import aiofiles
from langchain_community.llms import Ollama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


queue_file = r"E:\AAProgramming\AAmy\funasr\samples\python\results\text_0_0.txt"

class Getmic:
    def __init__(self):
        self.is_playing = False
        self.played_files = set()  # 使用集合来记录已处理的语音文本

    async def listen_service(self):
        while True:
            txt_file = await self.get_next_file()  # 获取下一个语音文本
            if txt_file:
                await self.gen_llm(txt_file)
            else:
                await asyncio.sleep(0.01)  # 如果没有文件，等待一秒钟

    async def get_next_file(self):
        try:
            punctuation = r"""?!,.;；！，。？……[]"""
            async with aiofiles.open(queue_file, 'r', encoding='utf-8') as qf:
                lines = await qf.readlines()

            for line in lines:
                txt_file = line.strip()
                if any(char in punctuation for char in txt_file):
                    if txt_file not in self.played_files:
                        self.played_files.add(txt_file)
                    
                        parts = txt_file.split('\t')
                        text_pro = parts[1]
                        text_pro = text_pro.split('[')[0]
                        text_pro = text_pro.strip()
                        
                        print(text_pro)
                        return text_pro

            return None
        except FileNotFoundError:
            return None

    async def gen_llm(self, txt_file):
        output_parser = StrOutputParser()
        llm = Ollama(base_url='http://localhost:11434', model="cielo")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are world class technical documentation writer."),
            ("user", "{input}")
            ])
        
        chain = prompt | llm | output_parser
        
        print(chain.invoke({"input": "how can langsmith help with testing?"}))
        

async def main():
    listen_mic_service = Getmic()
    #await listen_mic_service.listen_service()
    await listen_mic_service.gen_llm("nihao")
if __name__ == "__main__":
    asyncio.run(main())
