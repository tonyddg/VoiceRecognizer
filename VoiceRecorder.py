from collections.abc import Buffer
import queue
import time
from typing import Union
import wave
import numpy as np
import sounddevice as sd
from pathlib import Path
from dataclasses import dataclass

import logging
logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)

def _audio_rms(
    audio_frame
):
    '''计算语音块的音量'''
    samples = np.frombuffer(audio_frame, dtype=np.int16)
    if samples.size == 0:
        return 0
    mean_square = np.mean(samples.astype(np.float32) ** 2)
    if np.isnan(mean_square) or mean_square < 1e-5:
        return 0
    return float(np.sqrt(mean_square))

def _get_audio_collect_callback(q: queue.Queue):
    '''创建语音收集 callback'''
    def callback(indata, frames, time_info, status):
        if status:
            logger.error("音频流出错: %s", status)
        q.put(bytes(indata))
    return callback

def _save_wav_int16(
    audio_np: np.ndarray, 
    samplerate: int, 
    path: str, 
    channels: int = 1
):
    # audio_np: int16 一维数组（C-contiguous）
    if audio_np.dtype != np.int16:
        audio_np = audio_np.astype(np.int16, copy=False)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)            # int16 = 2 bytes
        wf.setframerate(samplerate)
        wf.writeframes(audio_np.tobytes())

# 语音处理参数参考自 https://github.com/dehaozhou/Dehao-Zhou/blob/main/%E5%88%A9%E7%94%A8%E5%A4%9A%E6%A8%A1%E6%80%81%E6%A8%A1%E5%9E%8BQwen2.5-VL%E7%90%86%E8%A7%A3%E4%BA%BA%E7%B1%BB%E6%84%8F%E5%9B%BE%EF%BC%8C%E8%BF%9B%E8%A1%8C%E4%BA%A4%E4%BA%92%E5%BC%8F%E6%8A%93%E5%8F%96/vlm_process.py
@dataclass
class VoiceRecorder:
    samplerate: int = 16000
    channels: int = 1
    
    frame_duration: float = 0.2
    frame_samples: int = int(frame_duration * samplerate)
    
    silence_threshold: int = 100
    silence_max_duration: float = 1.0
    # 最长记录长度
    max_record_time: float = 60

    def record_numpy(
        self
    ):
        # 音频缓存队列
        q = queue.Queue()
        last_voice_time = time.perf_counter()
        record_start_time = time.perf_counter()

        is_speaking = False
        audio_buffer = []

        with sd.RawInputStream(
            samplerate = self.samplerate, 
            blocksize = self.frame_samples,
            dtype = 'int16', 
            channels = self.channels, 
            callback = _get_audio_collect_callback(q)
        ):
            while True:
                frame = q.get()
                volume = _audio_rms(frame)
                current_time = time.perf_counter()
                logger.debug("当前音量: %s", volume)

                # 音量超过阈值开始录音
                if volume > self.silence_threshold:
                    if not is_speaking:
                        logger.info("检测到语音, 开始录音...")
                        is_speaking = True
                    audio_np = np.frombuffer(frame, dtype = np.int16)
                    audio_buffer.append(audio_np)
                    last_voice_time = current_time
                # 音量低于阈值一段时间停止录音
                elif (is_speaking and (current_time - last_voice_time > self.silence_max_duration)):
                    logger.info("语音终端, 录音完毕")
                    break

                # 当录音时间过长强制退出
                if current_time - record_start_time > self.max_record_time:
                    logger.info("录音超时, 强制退出")
                    break

        full_audio = np.concatenate(audio_buffer, axis=0)
        return np.asarray(full_audio)

    def record_wav(
        self,
        save_path: Union[str, Path]
    ):
        if isinstance(save_path, Path):
            save_path = save_path.as_posix()

        audio_arr = self.record_numpy()
        _save_wav_int16(
            audio_arr,
            self.samplerate,
            save_path,
            self.channels
        )

if __name__ == "__main__":

    # logger 设置
    ch = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s|%(levelname)s|%(name)s:%(lineno)d|%(funcName)s: %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.DEBUG)

    # 测试代码
    vr = VoiceRecorder()
    vr.record_wav("test.wav")
