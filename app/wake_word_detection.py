"""
唤醒词检测模块
使用Picovoice Porcupine进行离线唤醒词检测，支持自定义唤醒词。
"""

import pvporcupine
import sounddevice as sd
import struct
import asyncio
import threading
import queue
from config.logger import setup_logging

class WakeWordDetector:
    """
    唤醒词检测器
    
    使用Picovoice Porcupine实现离线唤醒词检测，支持:
    - 实时音频流处理
    - 自定义唤醒词
    - 异步检测机制
    - 线程安全的事件通知
    """
    
    def __init__(self):
        """
        初始化唤醒词检测器
        - 设置日志记录器
        - 初始化状态变量
        - 创建事件队列
        """
        self.logger = setup_logging().bind(tag=self.__class__.__name__)
        self.access_key = "8Z5xkIoDopeBYoiFdqspGG/p9sLh34ONP5aFpWYiKuB9e8nkEEiDEQ=="  # TODO: 替换成您从 Picovoice Console 获取的访问密钥
        self.porcupine = None
        self.stream = None
        self.detected_event = None
        self.detection_queue = queue.Queue()
        
    def initialize(self):
        """
        初始化Porcupine唤醒词检测器
        - 创建Porcupine实例
        - 配置唤醒词
        """
        if not self.porcupine:
            self.porcupine = pvporcupine.create(
                access_key=self.access_key,
                keywords=["alexa", "computer"]  # 可配置的唤醒词列表
            )
            self.logger.info("唤醒词检测器初始化完成")
            
    def audio_callback(self, indata, frames, time, status):
        """
        处理音频输入的回调函数
        
        参数:
            indata: numpy.ndarray - 输入的音频数据
            frames: int - 音频帧数
            time: CData - 时间戳信息
            status: CallbackFlags - 回调状态标志
            
        功能:
        - 将音频数据转换为PCM格式
        - 使用Porcupine进行唤醒词检测
        - 检测到唤醒词时发送通知
        """
        if status:
            self.logger.warning(f"音频输入状态: {status}")
            return
            
        pcm = struct.unpack_from("h" * self.porcupine.frame_length, indata)
        result = self.porcupine.process(pcm)
        
        if result >= 0:
            self.logger.info(f"检测到唤醒词！关键词索引: {result}")
            self.detection_queue.put(True)
            
    async def start_listening(self):
        """
        开始监听唤醒词
        
        处理流程:
        1. 初始化检测器
        2. 创建事件对象
        3. 启动音频流
        4. 等待唤醒词检测
        5. 清理资源
        
        返回:
            None - 当检测到唤醒词时返回
        """
        self.initialize()
        self.detected_event = asyncio.Event()
        
        # 创建一个任务来检查检测队列
        async def check_detection():
            """
            异步检查检测队列
            - 持续监控队列中的检测事件
            - 检测到唤醒词时设置事件标志
            """
            while True:
                try:
                    if not self.detection_queue.empty():
                        self.detection_queue.get()
                        self.detected_event.set()
                        break
                    await asyncio.sleep(0.1)
                except Exception as e:
                    self.logger.error(f"检查检测队列时出错: {e}")
                    break
        
        with sd.RawInputStream(
            samplerate=self.porcupine.sample_rate,
            blocksize=self.porcupine.frame_length,
            dtype='int16',
            channels=1,
            callback=self.audio_callback
        ):
            self.logger.info("开始监听唤醒词...")
            detection_task = asyncio.create_task(check_detection())
            await self.detected_event.wait()
            detection_task.cancel()
            
    def cleanup(self):
        """
        清理资源
        - 释放Porcupine实例
        - 重置状态变量
        """
        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None
            
    def __del__(self):
        """析构函数，确保资源被正确释放"""
        self.cleanup()

if __name__ == "__main__":
    async def main():
        """
        主函数，用于测试唤醒词检测功能
        """
        detector = WakeWordDetector()
        try:
            while True:
                await detector.start_listening()
                print("检测到唤醒词！等待3秒后继续...")
                await asyncio.sleep(3)
        except KeyboardInterrupt:
            detector.cleanup()
            
    asyncio.run(main())
