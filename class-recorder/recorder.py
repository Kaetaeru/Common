"""마이크 입력 스트림, 음량 계산, MP3 쓰기.

입력 스트림은 창이 열려 있는 동안 계속 열어 두고(음량 막대용), 녹음 중에만 블록을 쓰기 스레드로 넘긴다.
"""
import ctypes
import queue
import sys
import threading
import time

import numpy as np
import sounddevice as sd
import soundfile as sf

MP3_LEVEL = 0.9    # libsndfile MP3 고정 비트레이트에서 약 56kbps (실측)
FLUSH_EVERY = 60   # 초. 비정상 종료돼도 이때까지 녹음은 남는다


def input_devices():
    """기본 호스트 API(보통 MME)의 입력 장치 [(index, name)]. 같은 마이크가 드라이버별로 중복되지 않게."""
    api = sd.default.hostapi
    return [(i, d['name']) for i, d in enumerate(sd.query_devices())
            if d['max_input_channels'] > 0 and d['hostapi'] == api
            and 'Mapper' not in d['name'] and '매퍼' not in d['name']]  # 사운드 매퍼 = 'Windows 기본 마이크'와 같다


def keep_awake(on):
    """녹음 중 Windows 잠자기 모드를 막는다. 호출한 스레드에 걸리므로 창(메인) 스레드에서 부른다."""
    if sys.platform == 'win32':
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


class Recorder:
    def __init__(self):
        self.stream = None
        self.rate = 0
        self._peak = 0.0
        self._q = None
        self._thread = None
        self._frames = 0
        self.write_error = None

    @property
    def recording(self):
        return self._q is not None

    def open(self, device=None):
        self.close()
        self.rate = int(sd.query_devices(device, 'input')['default_samplerate'])
        self.stream = sd.InputStream(device=device, channels=1, samplerate=self.rate,
                                     dtype='float32', callback=self._callback)
        self.stream.start()

    def close(self):
        if self.stream:
            self.stream.close()
            self.stream = None

    def alive(self):
        return bool(self.stream and self.stream.active)

    def _callback(self, data, frames, time_info, status):
        self._peak = max(self._peak, float(np.abs(data).max()))
        q = self._q
        if q is not None:
            q.put(data.copy())

    def take_level(self):
        """마지막으로 읽은 뒤의 피크(0~1)."""
        peak, self._peak = self._peak, 0.0
        return min(peak, 1.0)

    def start(self, path):
        f = sf.SoundFile(path, 'w', self.rate, 1, format='MP3',
                         bitrate_mode='CONSTANT', compression_level=MP3_LEVEL)
        self._frames = 0
        self.write_error = None
        self._q = queue.Queue()
        self._thread = threading.Thread(target=self._write, args=(f, self._q), daemon=True)
        self._thread.start()

    def _write(self, f, q):
        last_flush = time.monotonic()
        try:
            while (block := q.get()) is not None:
                f.write(block)
                self._frames += len(block)
                if time.monotonic() - last_flush > FLUSH_EVERY:
                    f.flush()
                    last_flush = time.monotonic()
        except Exception as e:  # 디스크 가득 참 등. 창에서 알린다
            self.write_error = e
        finally:
            f.close()

    def seconds(self):
        return self._frames / self.rate if self.rate else 0.0

    def stop(self):
        """녹음을 끝내고 파일을 닫는다. 녹음된 초를 돌려준다."""
        q, self._q = self._q, None
        if q is None:
            return 0.0
        q.put(None)
        self._thread.join()
        return self.seconds()
