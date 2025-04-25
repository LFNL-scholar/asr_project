"""
语音助手主程序
集成唤醒词检测、语音识别和命令处理功能。
支持优雅退出（Ctrl+C）。
"""

import asyncio
import time
import signal
import sys
from app.wake_word_detection import WakeWordDetector
from app.handle import MainHandle
from app.audio_record import AudioRecorder
from config.logger import setup_logging

class VoiceAssistant:
    """
    语音助手主类
    
    集成功能:
    - 唤醒词检测
    - 语音识别
    - 音频录制
    - 命令处理
    """
    
    def __init__(self):
        """初始化语音助手组件"""
        self.logger = setup_logging().bind(tag=self.__class__.__name__)
        self.wake_word_detector = WakeWordDetector()
        self.main_handle = MainHandle()
        self.audio_recorder = AudioRecorder()
        self.is_listening = False
        self.is_running = True
        self._main_task = None
        self._loop = None
        
    async def process_voice(self):
        """处理语音识别流程"""
        self.logger.info("开始录音并进行语音识别...")
        audio_frames = []
        
        # 开始录音
        self.audio_recorder.start_recording()
        start_time = time.time()
        
        while self.is_running:  # 添加运行状态检查
            frame = self.audio_recorder.get_latest_audio()
            if frame:
                audio_frames.append(frame)
                
                # 使用VAD检测是否说话结束
                is_speech = self.main_handle.vad.is_vad(self.main_handle.conn, frame)
                if not is_speech and self.main_handle.conn.client_have_voice:
                    # 如果之前检测到语音，现在没有声音，检查是否超过静默阈值
                    if time.time() - self.main_handle.conn.client_have_voice_last_time/1000 > 0.7:
                        break
            
            # 设置最大录音时间为30秒
            if time.time() - start_time > 30:
                break
                
        self.audio_recorder.stop_recording()
        
        # 进行语音识别
        if audio_frames:
            text = await self.main_handle.process_audio(audio_frames)
            if text:
                self.logger.info(f"识别结果: {text}")
                return text
        return None

    def cleanup(self):
        """清理资源"""
        self.logger.info("正在清理资源...")
        self.is_running = False
        
        # 停止录音
        if self.audio_recorder.is_recording:
            self.audio_recorder.stop_recording()
            
        # 清理唤醒词检测器
        self.wake_word_detector.cleanup()
        
        # 取消主任务
        if self._main_task and not self._main_task.done():
            self._main_task.cancel()
        
        self.logger.info("资源清理完成")

    async def run(self):
        """运行主循环"""
        self.logger.info("语音助手启动...")
        self._loop = asyncio.get_running_loop()
        
        try:
            while self.is_running:
                # 等待唤醒词
                self.logger.info("等待唤醒词... (按 Ctrl+C 退出)")
                try:
                    await self.wake_word_detector.start_listening()
                except asyncio.CancelledError:
                    break
                
                if not self.is_running:  # 检查是否应该退出
                    break
                
                # 检测到唤醒词后，进行语音识别
                self.logger.info("检测到唤醒词！开始语音识别...")
                result = await self.process_voice()
                
                # 处理识别结果
                if result:
                    self.logger.info(f"处理命令: {result}")
                
                # 重置状态，准备下一轮检测
                self.main_handle.conn.client_have_voice = False
                self.main_handle.conn.client_voice_stop = False
                self.main_handle.conn.client_audio_buffer = b""
                
        except asyncio.CancelledError:
            self.logger.info("收到退出信号")
        finally:
            self.cleanup()

    def stop(self):
        """停止助手"""
        if self._loop:
            self.logger.info("正在停止语音助手...")
            self.is_running = False
            self._loop.call_soon_threadsafe(self._main_task.cancel)

def signal_handler(assistant):
    """信号处理函数"""
    def _handler(signum, frame):
        print("\n正在退出...")
        assistant.stop()
    return _handler

if __name__ == "__main__":
    assistant = VoiceAssistant()
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler(assistant))
    signal.signal(signal.SIGTERM, signal_handler(assistant))
    
    try:
        loop = asyncio.get_event_loop()
        assistant._main_task = loop.create_task(assistant.run())
        loop.run_until_complete(assistant._main_task)
    except KeyboardInterrupt:
        if assistant._loop:
            assistant._loop.call_soon_threadsafe(assistant.stop)
    finally:
        print("\n程序已退出")