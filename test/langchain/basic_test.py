# gpt_txt_module.py
import json
import uuid
import asyncio
import aiohttp
import aiofiles
from Get_TTS import *
from langchain_community.llms import Ollama
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.memory import ChatMessageHistory
from langchain.schema import HumanMessage, SystemMessage
import logging

class gpt_TXT:
    def __init__(self, tts_downloader):
        self.tts_downloader = tts_downloader
        self.tasks = []
        self.output_parser = StrOutputParser()
        self.llm = Ollama(base_url='http://localhost:11434', model="cielo")
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are world class technical documentation writer."),
            ("user", "{input}")
        ])
        self.chain = self.prompt | self.llm | self.output_parser
        self.chat_memory = ChatMessageHistory()
        self.file_counter = 1
        self.queue_file = './play_queue.txt'

    async def get_gpt_json(self, input_text):
        flag = True
        punctuation = r"""?!,.;；！，。？……"""
        current_sentence = ""
        message = {}
        output = ""

        async for chunk in self.chain.stream({"input": input_text}):
            content = chunk
            output += content
            print(content, end="", flush=True)

            if (content.strip() in punctuation) and (len(current_sentence) > 6):
                print("\n")
                filename = f"{self.file_counter:05d}_{uuid.uuid1()}.wav"
                task = asyncio.create_task(self.tts_downloader.tasks_queue.put((current_sentence, filename, self.queue_file, self.file_counter)))
                self.tts_downloader.active_tasks.add(task)
                task.add_done_callback(self.tts_downloader.active_tasks.discard)
                self.file_counter += 1
                current_sentence = ""
            else:
                current_sentence += content
                if flag and (len(current_sentence) > 6):
                    filename = f"{self.file_counter:05d}_{uuid.uuid1()}.wav"
                    task = asyncio.create_task(self.tts_downloader.tasks_queue.put(("嗯……", filename, self.queue_file, self.file_counter)))
                    self.tts_downloader.active_tasks.add(task)
                    task.add_done_callback(self.tts_downloader.active_tasks.discard)
                    self.file_counter += 1
                    flag = False

        message["content"] = output
        self.chat_memory.messages.append(HumanMessage(content=input_text))
        self.chat_memory.messages.append(SystemMessage(content=output))
        return message

    def add_task(self, input_text):
        self.tasks.append(self.get_gpt_json(input_text))

    async def process_tasks(self):
        results = await asyncio.gather(*self.tasks)
        if self.tts_downloader.active_tasks:
            await asyncio.wait(self.tts_downloader.active_tasks)
        return results

    def ask(self, text: str) -> str:
        if text == '':
            return ''
        message = HumanMessage(content=text)

        if self.llm.get_num_tokens_from_messages([message]) >= 256:
            raise ValueError('The text is too long!')

        if self.llm.get_num_tokens_from_messages([message]) + self.llm.get_num_tokens_from_messages(self.chat_memory.messages) >= 1536:
            self.summarize_memory()

        while self.llm.get_num_tokens_from_messages([message]) + self.llm.get_num_tokens_from_messages(self.chat_memory.messages) >= 1536:
            self.cut_memory()

        messages = [self.charactor_prompt]
        logging.info(f'开始！接收到信息: {text}')

        # 相关记忆
        relative_memory, relativeness = self.brain.extract_memory(text)
        is_full = False
        total_token = 0
        for i in range(len(relative_memory)):
            total_token += self.llm.get_num_tokens(relative_memory[i])
            if total_token >= 1024:
                is_full = True
        if is_full:
            relative_memory = relative_memory[:i]

        if len(relative_memory) > 0:
            memory_prompt = f'This following message is relative context for your response:\n\n{str(relative_memory)}'
            memory_message = SystemMessage(content=memory_prompt)
            messages.append(memory_message)

            mem_info = ''
            for i in range(len(relative_memory)):
                mem_info += f'{relative_memory[i]}[相关性: {relativeness[i]}]\n'
            logging.info(f'查询到相关记忆:\n' + mem_info)

        # 事实搜索
        if self.use_search:
            question, answer = self.search.think(text)
            if not answer == '':
                logging.info(f'进行搜索:\nQuestion: {question}\nAnswer:{answer}')
                fact_prompt = f'This following message is relative context searched in Google:\nQuestion:{question}\nAnswer:{answer}'
                fact_message = SystemMessage(content=fact_prompt)
                messages.append(fact_message)

        # 系统信息
        if len(self.chat_memory.messages) >= 2:
            duration = message_period_to_now(self.chat_memory.messages[-2])
            if duration > 1.0:
                system_message = SystemMessage(content=f'Passed {duration} hours since last conversation. You should simulate what you are doing during this period or make corresponding chat responses based on changes in time.')
                messages.append(system_message)
                logging.debug(f'引入系统信息: {system_message.content}')

        # 发送消息
        self.chat_memory.messages.append(message)
        self.history.messages.append(message)
        messages.extend(self.chat_memory.messages)
        while self.llm.get_num_tokens_from_messages(messages) > 4096:
            self.cut_memory()
        logging.debug(f'LLM query')
        reply = self.add_task(messages)

        history = []
        for message in self.chat_memory.messages:
            if isinstance(message, HumanMessage):
                history.append(f'用户: {message.content}')
            else:
                history.append(f'Waifu: {message.content}')
        info = '\n'.join(history)
        logging.debug(f'上下文记忆:\n{info}')

        if self.llm.get_num_tokens_from_messages(self.chat_memory.messages) >= 2048:
            self.summarize_memory()

        logging.info('结束回复')
        return reply

    def summarize_memory(self):
        # Add logic to summarize memory here
        pass

    def cut_memory(self):
        # Add logic to cut memory here
        pass

    def message_period_to_now(self, message):
        # Add logic to calculate the period from the message to now
        pass

    def brain(self, messages):
        # Add logic to simulate brain processing
        pass

# 配置文件读取放到模块中
with open('config/settings.json', 'r', encoding='utf-8') as f:
    settings = json.load(f)
