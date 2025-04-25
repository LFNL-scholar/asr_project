"""
语音识别(Automatic Speech Recognition, ASR)模块
使用FunASR模型进行语音识别，支持中文语音识别。
"""

import time
import io
import sys
import opuslib_next
from typing import Optional, Tuple, List
from config.logger import setup_logging

from funasr import AutoModel
from funasr.utils.postprocess_utils import rich_transcription_postprocess

TAG = __name__
logger = setup_logging()


class CaptureOutput:
    """
    用于捕获标准输出的上下文管理器
    
    主要用于捕获模型初始化时的输出信息，用于日志记录。
    """
    
    def __enter__(self):
        """进入上下文，开始捕获标准输出"""
        self._output = io.StringIO()
        self._original_stdout = sys.stdout
        sys.stdout = self._output

    def __exit__(self, exc_type, exc_value, traceback):
        """
        退出上下文，恢复标准输出并记录捕获的信息
        
        参数:
            exc_type: 异常类型（如果有）
            exc_value: 异常值（如果有）
            traceback: 异常回溯（如果有）
        """
        sys.stdout = self._original_stdout
        self.output = self._output.getvalue()
        self._output.close()

        if self.output:
            logger.bind(tag=TAG).success(f"ASR module initialized successfully | {self.output.strip()}")


class ASRProvider:
    """
    语音识别服务提供者
    
    使用FunASR模型进行语音识别，支持:
    - Opus音频解码
    - 实时语音识别
    - 中文语音识别
    - 文本后处理
    """
    
    def __init__(self):
        """
        初始化ASR服务
        - 设置模型目录
        - 加载预训练模型
        - 配置模型参数
        """
        self.model_dir = "models/SenseVoiceSmall"
   
        with CaptureOutput():
            self.model = AutoModel(
                model=self.model_dir,
                vad_kwargs={"max_single_segment_time": 30000},  # 最大单段语音时长30秒
                disable_update=True,
                hub="hf"
                # device="cuda:0",  # 启用GPU加速
            )

    def decode_opus_to_pcm(self, opus_data: List[bytes]) -> bytes:
        """
        将Opus音频数据解码为PCM格式
        
        参数:
            opus_data: List[bytes] - Opus编码的音频数据列表
            
        返回:
            bytes - 解码后的PCM音频数据
            
        说明:
            - 使用16kHz采样率和单声道
            - 每帧960个采样点（60ms）
        """
        decoder = opuslib_next.Decoder(16000, 1)  # 16kHz, 单声道
        pcm_data = []

        for opus_packet in opus_data:
            try:
                pcm_frame = decoder.decode(opus_packet, 960)  # 960 samples = 60ms
                pcm_data.append(pcm_frame)
            except opuslib_next.OpusError as e:
                logger.bind(tag=TAG).error(f"Opus解码错误: {e}", exc_info=True)

        return b"".join(pcm_data)

    async def speech_to_text(self, opus_data: List[bytes], session_id: str) -> str:
        """
        语音转文本的主处理逻辑
        
        处理流程:
        1. 将Opus音频解码为PCM格式
        2. 使用ASR模型进行语音识别
        3. 对识别结果进行后处理
        
        参数:
            opus_data: List[bytes] - Opus编码的音频数据列表
            session_id: str - 会话标识符
            
        返回:
            str - 识别出的文本，如果识别失败则返回空字符串
        """
        try:
            # 解码Opus为PCM
            start_time = time.time()
            pcm_data = self.decode_opus_to_pcm(opus_data)
            logger.bind(tag=TAG).debug(f"Opus解码耗时: {time.time() - start_time:.3f}s | 数据长度: {len(pcm_data)}字节")

            # 语音识别
            start_time = time.time()
            
            # 直接将PCM数据传递给模型
            result = self.model.generate(
                input=pcm_data,  # 直接传入PCM数据
                cache={},
                language="auto",
                use_itn=True,  # 启用数字文本规范化
                batch_size_s=60,
                data_type="sound"  # 指定输入类型为原始音频数据
            )
            
            # 对识别结果进行后处理
            text = rich_transcription_postprocess(result[0]["text"])
            logger.bind(tag=TAG).debug(f"语音识别耗时: {time.time() - start_time:.3f}s | 结果: {text}")

            return text

        except Exception as e:
            logger.bind(tag=TAG).error(f"语音识别失败: {e}", exc_info=True)
            return ""