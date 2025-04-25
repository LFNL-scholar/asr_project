"""
语音处理主模块，负责协调VAD（语音活动检测）和ASR（语音识别）功能。
此模块作为语音处理的中心控制器，管理音频数据的流转和处理。
"""

import sys
from pathlib import Path
from typing import List, Optional
import asyncio

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from config.logger import setup_logging
from app.fun_asr import ASRProvider
from app.vad import create_instance as create_vad

class Connection:
    """
    连接对象，用于存储VAD检测相关的状态
    
    属性:
        client_audio_buffer (bytes): 音频数据缓冲区，存储待处理的PCM音频数据
        client_have_voice (bool): 标记是否检测到语音活动
        client_have_voice_last_time (float): 上次检测到语音的时间戳（毫秒）
        client_voice_stop (bool): 标记是否检测到语音停止
    """
    def __init__(self):
        self.client_audio_buffer = b""  # 音频缓冲区
        self.client_have_voice = False  # 是否检测到声音
        self.client_have_voice_last_time = 0  # 上次检测到声音的时间戳
        self.client_voice_stop = False  # 是否停止说话

class MainHandle:
    """
    语音处理主类，协调VAD和ASR功能
    
    该类负责:
    1. 初始化和管理VAD和ASR组件
    2. 处理音频数据流
    3. 执行语音活动检测
    4. 调用语音识别服务
    """
    
    def __init__(self):
        """
        初始化语音处理组件
        - 设置日志记录器
        - 初始化ASR（语音识别）模块
        - 初始化VAD（语音活动检测）模块
        - 创建连接状态对象
        """
        self.logger = setup_logging().bind(tag=self.__class__.__name__)
        self.logger.info("初始化语音处理模块...")
        
        # 初始化ASR和VAD
        self.asr = ASRProvider()
        self.vad = create_vad()
        self.conn = Connection()
        
        # 存储有效的音频数据
        self.valid_audio_frames = []

    async def process_audio(self, audio_frames: List[bytes]) -> Optional[str]:
        """
        处理录制的音频数据，应用VAD并进行ASR识别
        
        处理流程:
        1. 重置处理状态
        2. 对每一帧音频进行VAD处理
        3. 收集有效的语音帧
        4. 执行语音识别
        
        参数:
            audio_frames: List[bytes] - Opus编码的音频帧列表
            
        返回:
            Optional[str] - 识别出的文本，如果没有检测到有效语音则返回None
        """
        self.logger.info(f"开始处理 {len(audio_frames)} 个音频帧")
        
        # 重置状态
        self.conn = Connection()
        self.valid_audio_frames = []
        
        # 对每一帧进行VAD处理
        for frame in audio_frames:
            is_speech = self.vad.is_vad(self.conn, frame)
            if is_speech or self.conn.client_have_voice:
                self.valid_audio_frames.append(frame)
        
        # 如果没有检测到语音，返回None
        if not self.valid_audio_frames:
            self.logger.info("未检测到有效语音")
            return None
        
        # 执行ASR识别
        text = await self.asr.speech_to_text(self.valid_audio_frames, "session_id")
        
        self.logger.info(f"识别文本：{text}")
        return text