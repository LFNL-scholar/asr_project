"""
语音活动检测(Voice Activity Detection, VAD)模块
使用Silero VAD模型进行语音活动检测，支持实时音频流处理。
"""

from abc import ABC, abstractmethod
from config.logger import setup_logging
import opuslib_next
import time
import numpy as np
import torch

TAG = __name__
logger = setup_logging()

class VAD(ABC):
    """
    语音活动检测的抽象基类
    
    定义了VAD检测器的基本接口，允许实现不同的VAD算法。
    """
    
    @abstractmethod
    def is_vad(self, conn, data):
        """
        检测音频数据中的语音活动
        
        参数:
            conn: Connection - 存储VAD状态的连接对象
            data: bytes - 待检测的音频数据
            
        返回:
            bool - 是否检测到语音活动
        """
        pass

class SileroVAD(VAD):
    """
    基于Silero模型的VAD实现
    
    特点:
    - 使用预训练的Silero VAD模型
    - 支持实时音频流处理
    - 提供可配置的语音检测阈值
    - 支持静默检测
    """
    
    def __init__(self):
        """
        初始化Silero VAD模型和相关参数
        - 加载预训练模型
        - 初始化Opus解码器
        - 设置检测阈值
        """
        logger.bind(tag=TAG).success("VAD module initialized successfully")
        
        # 加载Silero VAD模型
        self.model, self.utils = torch.hub.load(repo_or_dir="models/snakers4_silero-vad",
                                                source='local',
                                                model='silero_vad',
                                                force_reload=False)
        (get_speech_timestamps, _, _, _, _) = self.utils

        # 初始化解码器和阈值参数
        self.decoder = opuslib_next.Decoder(16000, 1)  # 16kHz采样率，单声道
        self.vad_threshold = 0.5  # 语音检测阈值
        self.silence_threshold_ms = 700  # 静默检测阈值（毫秒）

    def is_vad(self, conn, opus_packet):
        """
        检测音频数据中的语音活动
        
        处理流程:
        1. 解码Opus音频数据
        2. 将音频数据添加到缓冲区
        3. 按固定大小的窗口处理音频
        4. 使用模型进行语音活动检测
        5. 更新语音状态
        
        参数:
            conn: Connection - 存储VAD状态的连接对象
            opus_packet: bytes - Opus编码的音频数据包
            
        返回:
            bool - 当前音频帧是否包含语音
        """
        try:
            # 解码Opus数据为PCM
            pcm_frame = self.decoder.decode(opus_packet, 960)
            conn.client_audio_buffer += pcm_frame  # 将新数据加入缓冲区

            # 处理缓冲区中的完整帧（每次处理512采样点）
            client_have_voice = False
            while len(conn.client_audio_buffer) >= 512 * 2:
                # 提取前512个采样点（1024字节）
                chunk = conn.client_audio_buffer[:512 * 2]
                conn.client_audio_buffer = conn.client_audio_buffer[512 * 2:]

                # 转换为模型需要的张量格式
                audio_int16 = np.frombuffer(chunk, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_float32)

                # 检测语音活动
                speech_prob = self.model(audio_tensor, 16000).item()
                client_have_voice = speech_prob >= self.vad_threshold

                # 处理语音状态转换
                if conn.client_have_voice and not client_have_voice:
                    # 如果之前有声音，但本次没有声音，检查是否超过静默阈值
                    stop_duration = time.time() * 1000 - conn.client_have_voice_last_time
                    if stop_duration >= self.silence_threshold_ms:
                        conn.client_voice_stop = True
                if client_have_voice:
                    conn.client_have_voice = True
                    conn.client_have_voice_last_time = time.time() * 1000

            return client_have_voice
            
        except opuslib_next.OpusError as e:
            logger.bind(tag=TAG).info(f"解码错误: {e}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理音频数据时出错: {e}")
        return False

def create_instance() -> VAD:
    """
    创建VAD实例的工厂函数
    
    返回:
        VAD - 新创建的VAD实例
    """
    return SileroVAD()

