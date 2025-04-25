# 语音助手系统

基于唤醒词的中文语音识别系统，支持实时语音识别和命令处理。

## 功能特点

- 离线唤醒词检测（基于 Picovoice Porcupine）
- 实时语音活动检测（VAD）
- 中文语音识别（基于 FunASR）
- 实时音频处理（Opus 编码）
- 优雅的退出机制

## 系统要求

- Python 3.9 或更高版本
- macOS/Linux/Windows
- 可用的麦克风设备

## 安装步骤

1. 克隆仓库：
```bash
git clone [repository_url]
cd asr_project
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 下载模型：
   - 在 `models` 目录下创建以下文件夹：
     - `SenseVoiceSmall`（用于 ASR）
     - `snakers4_silero-vad`（用于 VAD）

4. 配置唤醒词：
   - 在 Picovoice Console 获取访问密钥
   - 在 `app/wake_word_detection.py` 中更新 `access_key`

## 目录结构

```
asr_project/
├── app/
│   ├── audio_record.py    # 音频录制模块
│   ├── fun_asr.py        # 语音识别模块
│   ├── handle.py         # 主处理模块
│   ├── vad.py           # 语音活动检测
│   └── wake_word_detection.py  # 唤醒词检测
├── config/
│   └── logger.py        # 日志配置
├── models/              # 模型目录
├── main.py             # 主程序
└── requirements.txt    # 依赖列表
```

## 使用说明

1. 启动程序：
```bash
python main.py
```

2. 系统功能：
   - 等待唤醒词（默认："alexa" 或 "computer"）
   - 检测到唤醒词后自动开始录音
   - 自动检测语音结束并进行识别
   - 显示识别结果

3. 退出程序：
   - 按 Ctrl+C 优雅退出
   - 系统会自动清理资源

## 主要模块说明

### 1. 唤醒词检测
- 使用 Picovoice Porcupine 实现
- 支持自定义唤醒词
- 低功耗实时检测

### 2. 语音活动检测（VAD）
- 使用 Silero VAD 模型
- 实时检测语音活动
- 自动判断语音结束

### 3. 语音识别（ASR）
- 使用 FunASR 模型
- 支持中文识别
- 实时音频处理

### 4. 音频处理
- 支持实时音频录制
- Opus 音频编码
- 高效的音频帧处理

## 注意事项

1. 确保麦克风权限已授予
2. 检查模型文件是否正确放置
3. 确保 Picovoice 访问密钥有效
4. 保持网络连接（用于首次下载模型）

## 常见问题

1. 麦克风未检测到
   - 检查系统音频设置
   - 确认麦克风权限

2. 唤醒词无响应
   - 检查访问密钥是否正确
   - 确认麦克风工作正常

3. 语音识别不准确
   - 检查环境噪音
   - 确保语音清晰

## 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 贡献指南

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0
- 实现基础功能
- 支持唤醒词检测
- 添加语音识别
- 实现 VAD 功能