import pyaudio
import opuslib
import keyboard
import threading
import time
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
from config.logger import setup_logging

TAG = __name__
logger = setup_logging()

# 音频参数
SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_LENGTH_MS = 60
CHUNK = int(SAMPLE_RATE * FRAME_LENGTH_MS / 1000)
FORMAT = pyaudio.paInt16
OPUS_APPLICATION = opuslib.APPLICATION_VOIP

# 全局变量
is_recording = False
audio_frames = []
opus_encoder = None
pa = None
stream = None
has_microphone = False  # 新增：麦克风检测标志

def check_microphone():
    """检查系统是否有可用的麦克风设备"""
    global has_microphone
    p = pyaudio.PyAudio()
    try:
        # 获取默认输入设备信息
        default_input = p.get_default_input_device_info()
        if default_input['maxInputChannels'] > 0:
            has_microphone = True
            logger.bind(tag="TAG").info("✅ 找到可用的麦克风设备")
        else:
            logger.bind(tag="TAG").info("⚠️ 未找到可用的麦克风设备")
    except:
        logger.bind(tag="TAG").info("⚠️ 未找到可用的麦克风设备")
    finally:
        p.terminate()

def init_opus_encoder():
    """初始化Opus编码器"""
    try:
        encoder = opuslib.Encoder(SAMPLE_RATE, CHANNELS, OPUS_APPLICATION)
        return encoder
    except Exception as e:
        logger.bind(tag="TAG").info(f"❌ 初始化Opus编码器失败: {e}")
        return None

def callback(in_data, frame_count, time_info, status):
    """音频流回调函数"""
    global is_recording, opus_encoder, audio_frames
    if is_recording and opus_encoder:
        try:
            opus_data = opus_encoder.encode(in_data, frame_count)
            audio_frames.append(opus_data)
        except Exception as e:
            logger.bind(tag="TAG").info(f"❌ 音频编码出错: {e}")
    return (in_data, pyaudio.paContinue)

def start_recording():
    """开始录音"""
    global is_recording, stream, pa, opus_encoder, has_microphone
    
    if not has_microphone:
        logger.bind(tag="TAG").info("⚠️ 无法录音：没有可用的麦克风设备")
        return
        
    if not is_recording:
        try:
            is_recording = True
            audio_frames.clear()
            opus_encoder = init_opus_encoder()
            if not opus_encoder:
                return
                
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK,
                stream_callback=callback
            )
            stream.start_stream()
            logger.bind(tag="TAG").info("🎤 录音开始... (16kHz, 60ms/帧)")
        except Exception as e:
            logger.bind(tag="TAG").info(f"❌ 录音启动失败: {e}")
            stop_recording()

def stop_recording():
    """停止录音"""
    global is_recording, stream, pa
    if is_recording:
        is_recording = False
        try:
            if stream:
                stream.stop_stream()
                stream.close()
            if pa:
                pa.terminate()
            logger.bind(tag="TAG").info(f"⏹️ 录音停止. 已保存 {len(audio_frames)} 个Opus数据块")
        except Exception as e:
            logger.bind(tag="TAG").info(f"❌ 停止录音时出错: {e}")

def monitor_space_key():
    """监听空格键状态"""
    while True:
        try:
            if keyboard.is_pressed('space'):
                if not is_recording:
                    start_recording()
            else:
                if is_recording:
                    stop_recording()
            time.sleep(0.01)
        except Exception as e:
            logger.bind(tag="TAG").info(f"❌ 按键监听出错: {e}")
            break

if __name__ == "__main__":
    # 启动前先检查麦克风
    check_microphone()
    
    if has_microphone:
        logger.bind(tag="TAG").info("🔄 按住空格键开始录音，松开停止...")
        key_monitor_thread = threading.Thread(target=monitor_space_key)
        key_monitor_thread.daemon = True
        key_monitor_thread.start()
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 程序退出")
    else:
        print("❌ 没有可用的麦克风设备，程序退出")