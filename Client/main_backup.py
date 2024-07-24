import os
import sys
import urllib.parse, requests, html, base64, uuid
import soundfile as sf
import sounddevice as sd
import asyncio
import aiohttp
import aiofiles
import websockets
import json
# 多线程
from threading import Thread
# 结束线程
import ctypes
import inspect


# PyQt6
# PyQt5 QWebEngineView has a big bug on Linux (does not show anything), so we are using PyQt6
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import *
from PyQt6.QtGui import *
from PyQt6.QtWebEngineWidgets import *

from mainWindow import *

class Config:
    config_files = {'settings': 'config/settings.json'}
    dicts = {'settings': {}}

    def __init__(self):
        try:
            with open(self.config_files['settings'], 'r', encoding='utf-8') as f:
                self.dicts['settings'] = json.load(f)
        except FileNotFoundError:
            print(f"Configuration file {self.config_files['settings']} not found.")
        except json.JSONDecodeError:
            print(f"Error decoding JSON from the file {self.config_files['settings']}.")


    def read(self, file, key):
        try:
            return self.dicts[file][key]
        except KeyError:
            print(f"Key '{key}' not found in the '{file}' configuration.")
            return None

    def read_settings(self):
        return self.dicts['settings']

class WebSocketClient:
    def __init__(self, url):
        self.url = url
        self.websocket = None

    async def connect(self):
        self.websocket = await websockets.connect(self.url)

    async def subscribe(self, room_id):
        await self.websocket.send(json.dumps({
            "cmd": 1,
            "data": {"roomId": room_id}
        }))
        print(f"Subscribed to room {room_id}")

    async def keep_alive(self):
        while True:
            await self.websocket.send(json.dumps({
                "cmd": 0,
                "data": {}
            }))
            await asyncio.sleep(10)

    async def receive_messages(self):
        async for message in self.websocket:
            data = json.loads(message)
            message = data['data']
            if message != {}:
                
                print(f"Received message: {data}")
                asyncio.create_task(gpt_main(message[4]))

    async def start(self, room_id):
        await self.connect()
        await self.subscribe(room_id)

        tasks = [
            self.keep_alive(),
            self.receive_messages()
        ]

        await asyncio.gather(*tasks)

    async def close(self):
        if self.websocket:
            await self.websocket.close()

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
        global save_count
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

                    # 创建任务写入pending文件
                    #asyncio.create_task(self.write_pending_files(queue_path, file_counter))

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}") 
     
class Get_Txt:
    def __init__(self, tts_downloader):
        self.tts_downloader = tts_downloader

        
    async def get_gpt_json(self, txt):
        global file_counter
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
                        mainWindow.label.setText(sentence)
                        # Update the label with the new sentence (assuming you have a label widget)
                        # mainWindow.label.setText(sentence)

                        punctuation = r"""?!,.;；！，。？……"""
                        if response_part.strip() in punctuation:
                            if current_sentence != "":
                                print("\n")
                                filename = f"{file_counter:05d}_{uuid.uuid1()}.wav"
                                task = asyncio.create_task(self.tts_downloader.tasks_queue.put((current_sentence, filename, queue_file, file_counter)))
                                self.tts_downloader.active_tasks.add(task)
                                task.add_done_callback(self.tts_downloader.active_tasks.discard)
                                file_counter += 1  # 增加计数器
                                current_sentence = ""
                        else:
                            current_sentence += response_part

        except aiohttp.ClientError as e:
            print(f"Aiohttp client error: {e}")
        except Exception as e:
            print(f"An error occurred: {e}")

        return sentence
    
async def gpt_main(ipt = "你好"):
    tts_downloader = TTSDownloader()
    obj = Get_Txt(tts_downloader)

    # 启动 TTS 服务
    asyncio.create_task(tts_downloader.tts_service())

    await obj.get_gpt_json(ipt)

    # 等待所有活跃任务完成
    if tts_downloader.active_tasks:
        await asyncio.wait(tts_downloader.active_tasks)
            
    def _async_raise(self, tid, exctype):
        """raises the exception, performs cleanup if needed"""
        if not inspect.isclass(exctype):
            exctype = type(exctype)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
        if res == 0:
            raise ValueError("invalid thread id")
        elif res != 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")
        
async def asy_main():
    client = WebSocketClient('ws://localhost:12450/api/chat')
    try:
        await client.start(room_id=32741316)  # 替换为实际的房间 ID
    finally:
        await client.close()
        
class Utils:

        
    def url_text_encode(self, text):
        text = urllib.parse.quote(text, 'utf-8')
        reserved_replace = [['!', '%21'], ['#', '%23'], ['$', '%24'], ['&', '%26'], ['\'', '%27'], ['(', '%28'],
                            [')', '%29'], ['*', '%2A'], ['+', '%2B'], [',', '%2C'], ['/', '%2F'], [':', '%3A'],
                            [';', '%3B'], ['=', '%3D'], ['?', '%3F'], ['@', '%40'], ['[', '%5B'], [']', '%5D']]
        for i in reserved_replace:
            text = text.replace(i[0], i[1])
        return text

    def base64_decode(self, text):
        text = base64.urlsafe_b64decode(text.encode('UTF-8')).decode('UTF-8')
        # print(text)
        return text

    def test_connection(self, url):
        try:
            r = requests.get(url=url)
            return 'OK'
            # return r.status_code
        except Exception as e:
            return e.args


            
    def stop_thread(self, thread):
        self._async_raise(thread.ident, SystemExit)

            

class Ui_MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(Ui_MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.current_wav_path = ''

    def setupUi(self, MainWindow):
        super(Ui_MainWindow, self).setupUi(MainWindow)

        # QWebEngienView -> self.widget
        webview = QWebEngineView(self.widget)
        l2d_url = settings['l2d']
        webview.load(QUrl(l2d_url))  # 加载Live2D页面
        # self.setCentralWidget(self.browser)
        webview.resize(800, 380)
        webview.show()

        # QLabel -> self.widget_2
        label = QLabel(self.widget_2)
        pixmap = QPixmap(settings['waifu-pic'])
        label.setPixmap(pixmap)
        label.setToolTip('Click to replay voice')  # 设置悬停提示

        # 单击触发绑定的槽函数
        self.pushButton.clicked.connect(self.button_clicked)

        self.setFixedSize(MainWindow.width(), MainWindow.height())  # 禁止最大化和调整窗口大小
        self.label.setWordWrap(True)  # Label自动换行
        self.textEdit.setFocus()  # 输入文本框获取焦点

        self.tabWidget.setTabText(0, settings['waifu-name'])

        # 服务器连接状况
        status = ":: GPT Server | {} | {}".format(settings['gpt'], util.test_connection(settings['gpt'])) + '\n' + \
                 ":: TTS Server | {} | {}".format(settings['tts'], util.test_connection(settings['tts'])) + '\n' + \
                 ":: Live2D Server | {} | {}".format(settings['l2d'], util.test_connection(settings['l2d'])) + '\n'
        print(status)
        self.label.setText(status)

    def button_clicked(self):
        sender = self.sender()
        name = sender.objectName()
        # print(name)

        if name == 'pushButton':  # 发送请求按钮被点击
            if self.textEdit.toPlainText() == '':
                return
            self.pushButton.setDisabled(True)
            self.pushButton.setText('Please wait')
            self.label.setText('')
            thread_01 = Thread(target=self.do)
            thread_01.start()


    def do(self):  # 请求
        ipt = self.textEdit.toPlainText()
        def show_text():
            if settings['show-both-zh-jp'] is True:
                self.label.setText(opt['zh'] + '\n\n' + opt['jp'])
            else:
                self.label.setText(opt['zh'])

        status = ':: Now waiting GPT...'
        print(status)
        self.setWindowTitle("CyberWaifu {}".format(status))
        opt = {}
        opt['zh'] = ""
        try:
            asyncio.create_task(gpt_main(ipt))
            
        except Exception as e:
            print(e.args)

        self.pushButton.setText('Send')
        self.pushButton.setDisabled(False)
        return

    def get_current_wav_path(self):
        return self.current_wav_path


class QLabel(QtWidgets.QLabel):
    """
    重写QLabel的事件函数
    Ref. https://blog.csdn.net/qq_41203622/article/details/109285700
    """
    def mouseReleaseEvent(self, QMouseEvent):  # 重播音频按钮被点击
        wav_path = mainWindow.get_current_wav_path()
        print('replay ' + wav_path)
        util.playsound(wav_path)





if __name__ == '__main__':
    global conf, util, settings, mainWindow
    conf = Config()
    util = Utils()
    settings = conf.read_settings()

    global wav_folder, queue_file, file_counter, save_count
    wav_folder = '.cache'
    queue_file = './play_queue.txt'
    file_counter = 1  # 初始化计数器从1开始
    save_count = 0
    # 创建缓存文件夹
    try:
        os.mkdir(wav_folder)
    except Exception as e:
        print(".cache file already exist")

    # 清理缓存
    print(":: Cleaning cache...")
    for i in os.listdir(wav_folder):
        print(i)
        try:
            os.remove(os.path.join(wav_folder, i))
        except Exception as e:
            print(e.args)
            
    if os.path.exists(queue_file):
        os.remove(queue_file)
    with open(queue_file, 'w') as f:
        pass  # 创建一个空的 play_queue.txt 文件
        
    # 运行主程序
    
    app = QApplication(sys.argv)
    mainWindow = Ui_MainWindow()
    
    global thread_01
    asyncio.run(asy_main())
    mainWindow.show()

    sys.exit(app.exec())
