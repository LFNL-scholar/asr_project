"""
音频录制模块
提供实时音频录制功能，支持Opus编码和实时音频帧获取。
"""

import pyaudio
import opuslib_next as opuslib
import keyboard
import threading
import time
import sys
from pathlib import Path
from typing import List, Optional
import queue

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from config.logger import setup_logging

class AudioRecorder:
    """
    音频录制器
    
    功能特点:
    - 支持实时音频录制
    - Opus音频编码
    - 实时音频帧获取
    - 线程安全的数据处理
    - 支持空格键控制录音
    """
    
    def __init__(self):
        """
        初始化音频录制器
        
        配置:
        - 音频参数（采样率、通道数、帧长等）
        - 编码器设置
        - 状态变量
        - 缓冲区
        """
        self.logger = setup_logging().bind(tag=self.__class__.__name__)
        
        # 音频参数
        self.SAMPLE_RATE = 16000  # 采样率16kHz
        self.CHANNELS = 1         # 单声道
        self.FRAME_LENGTH_MS = 60 # 帧长60ms
        self.CHUNK = int(self.SAMPLE_RATE * self.FRAME_LENGTH_MS / 1000)
        self.FORMAT = pyaudio.paInt16
        self.OPUS_APPLICATION = opuslib.APPLICATION_VOIP
        
        # 状态变量
        self.is_recording = False
        self.audio_frames: List[bytes] = []
        self.opus_encoder: Optional[opuslib.Encoder] = None
        self.pa: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None
        self.has_microphone = False
        self.frame_queue = queue.Queue()
        
        # 初始化检查
        self._check_microphone()

    def _check_microphone(self):
        """
        检查麦克风设备
        
        - 获取默认输入设备信息
        - 验证设备可用性
        - 更新麦克风状态
        """
        self.pa = pyaudio.PyAudio()
        try:
            default_input = self.pa.get_default_input_device_info()
            self.has_microphone = default_input['maxInputChannels'] > 0
            msg = "✅ 找到可用的麦克风设备" if self.has_microphone else "⚠️ 未找到可用的麦克风设备"
            self.logger.info(msg)
        except Exception as e:
            self.has_microphone = False
            self.logger.error(f"麦克风检测失败: {e}")
        finally:
            if self.pa:
                self.pa.terminate()
                self.pa = None

    def _init_opus_encoder(self) -> bool:
        """
        初始化Opus编码器
        
        返回:
            bool - 初始化是否成功
        """
        try:
            self.opus_encoder = opuslib.Encoder(
                self.SAMPLE_RATE, 
                self.CHANNELS, 
                self.OPUS_APPLICATION
            )
            return True
        except Exception as e:
            self.logger.error(f"Opus编码器初始化失败: {e}")
            return False

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """
        音频流回调函数
        
        参数:
            in_data: bytes - 输入的音频数据
            frame_count: int - 帧数
            time_info: dict - 时间信息
            status: int - 状态标志
            
        返回:
            tuple - (处理后的数据, 状态标志)
        """
        if self.is_recording and self.opus_encoder:
            try:
                opus_data = self.opus_encoder.encode(in_data, frame_count)
                self.audio_frames.append(opus_data)
                self.frame_queue.put(opus_data)
            except Exception as e:
                self.logger.error(f"音频编码出错: {e}")
        return (in_data, pyaudio.paContinue)

    def get_latest_audio(self) -> Optional[bytes]:
        """
        获取最新的音频帧
        
        返回:
            Optional[bytes] - 最新的Opus编码音频帧，如果队列为空则返回None
        """
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

    def start_recording(self) -> bool:
        """
        开始录音
        
        处理流程:
        1. 检查麦克风可用性
        2. 初始化编码器
        3. 配置并启动音频流
        4. 清理缓冲区
        
        返回:
            bool - 录音是否成功启动
        """
        if not self.has_microphone:
            self.logger.warning("无法录音：没有可用的麦克风设备")
            return False
            
        if self.is_recording:
            self.logger.warning("录音已在进行中")
            return True
            
        try:
            if not self._init_opus_encoder():
                return False
                
            self.pa = pyaudio.PyAudio()
            self.stream = self.pa.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                stream_callback=self._audio_callback
            )
            
            self.is_recording = True
            self.audio_frames.clear()
            while not self.frame_queue.empty():
                self.frame_queue.get_nowait()
            self.stream.start_stream()
            self.logger.info("🎤 录音开始 (16kHz, 60ms/帧)")
            return True
            
        except Exception as e:
            self.logger.error(f"录音启动失败: {e}")
            self.stop_recording()
            return False

    def stop_recording(self) -> List[bytes]:
        """
        停止录音
        
        处理流程:
        1. 停止音频流
        2. 关闭设备
        3. 清理资源
        
        返回:
            List[bytes] - 录制的音频帧列表
        """
        if not self.is_recording:
            return self.audio_frames.copy()
            
        self.is_recording = False
        try:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.pa:
                self.pa.terminate()
                
            self.logger.info(f"⏹️ 录音停止. 已保存 {len(self.audio_frames)} 个Opus数据块")
            return self.audio_frames.copy()
            
        except Exception as e:
            self.logger.error(f"停止录音时出错: {e}")
            return self.audio_frames.copy()
        finally:
            self.stream = None
            self.pa = None
            self.opus_encoder = None

    def record_on_space(self):
        """
        空格键控制录音的线程方法
        
        功能:
        - 监听空格键按下和释放
        - 控制录音的开始和停止
        - 处理录音状态转换
        """
        try:
            space_pressed = False
            while True:
                if keyboard.is_pressed('space'):
                    if not space_pressed:
                        space_pressed = True
                        if not self.is_recording:
                            self.start_recording()
                else:
                    if space_pressed:
                        space_pressed = False
                        if self.is_recording:
                            self.stop_recording()  # 数据会保留在self.audio_frames中
                            self.logger.info("录音结束，等待处理...")
                time.sleep(0.01)
        except Exception as e:
            self.logger.error(f"按键监听出错: {e}")

    def start_space_monitor(self):
        """
        启动空格键监听线程
        
        功能:
        - 创建并启动监听线程
        - 配置线程为守护线程
        
        返回:
            Thread - 创建的监听线程
        """
        if not self.has_microphone:
            self.logger.error("无法启动监听：没有可用的麦克风设备")
            return
            
        self.logger.info("🔄 按住空格键开始录音，松开停止...")
        monitor_thread = threading.Thread(
            target=self.record_on_space, 
            daemon=True
        )
        monitor_thread.start()
        return monitor_thread
