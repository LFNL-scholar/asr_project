import os
import signal
import sys

import dashscope
import pyaudio
from dashscope.audio.asr import *

mic = None
stream = None
target_language = 'zh'  # 修改为中文

def init_dashscope_api_key():
    if 'DASHSCOPE_API_KEY' in os.environ:
        dashscope.api_key = os.environ['DASHSCOPE_API_KEY']
    else:
        dashscope.api_key = '<your-dashscope-api-key>'

class Callback(TranslationRecognizerCallback):
    def on_open(self) -> None:
        global mic
        global stream
        print('翻译识别器已开启')
        mic = pyaudio.PyAudio()
        stream = mic.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=16000,
                          input=True)

    def on_close(self) -> None:
        global mic
        global stream
        print('翻译识别器已关闭')
        stream.stop_stream()
        stream.close()
        mic.terminate()
        stream = None
        mic = None

    def on_complete(self) -> None:
        print('翻译完成')

    def on_error(self, message) -> None:
        print('翻译识别器错误 - 任务ID: ', message.request_id)
        print('错误信息: ', message.message)
        if 'stream' in globals() and stream.active:
            stream.stop()
            stream.close()
        sys.exit(1)

    def on_event(
        self,
        request_id,
        transcription_result: TranscriptionResult,
        translation_result: TranslationResult,
        usage,
    ) -> None:
        if translation_result is not None:
            translation = translation_result.get_translation(target_language)
            print('翻译为中文: {}'.format(translation.text))
            if translation.stash is not None:
                print('翻译缓存: {}'.format(
                    translation_result.get_translation('zh').stash.text,
                ))
            if translation.is_sentence_end:
                print('请求ID: ', request_id)
                print('使用量: ', usage)

def signal_handler(sig, frame):
    print('检测到Ctrl+C，停止翻译...')
    translator.stop()
    print('翻译已停止')
    print('[统计] 请求ID: {}, 首包延迟(ms): {}, 末包延迟(ms): {}'.format(
        translator.get_last_request_id(),
        translator.get_first_package_delay(),
        translator.get_last_package_delay(),
    ))
    sys.exit(0)

if __name__ == '__main__':
    init_dashscope_api_key()
    print('初始化中...')

    callback = Callback()

    translator = TranslationRecognizerRealtime(
        model='gummy-realtime-v1',
        format='pcm',
        sample_rate=16000,
        transcription_enabled=False,
        translation_enabled=True,
        translation_target_languages=[target_language],
        callback=callback,
    )

    translator.start()

    signal.signal(signal.SIGINT, signal_handler)
    print("按'Ctrl+C'停止录音和翻译...")

    while True:
        if stream:
            data = stream.read(3200, exception_on_overflow=False)
            translator.send_audio_frame(data)
        else:
            break

    translator.stop()