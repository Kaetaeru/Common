"""수업 녹음기 — 녹음 버튼을 누르고, 정지하면 내 시간표 기준 이름으로 과목별 폴더에 저장한다.

실행: run_windows.bat 더블클릭 (또는 python app.py)
"""
import ctypes
import math
import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk
from pathlib import Path

import timetable as tt
from recorder import Recorder, input_devices, keep_awake

BASE = Path.home() / 'Documents' / '수업 녹음'
FONT = 'Malgun Gothic'
METER_W, METER_H = 380, 14
GREEN, RED, MUTED = '#2e9e5b', '#d64545', '#6b6b6b'


def now():
    return datetime.now(tt.JST)


class App:
    def __init__(self, root):
        self.root = root
        root.title('수업 녹음기')
        root.resizable(False, False)
        try:
            self.tt = tt.Timetable.load()
            load_error = ''
        except Exception as e:  # 시간표가 없어도 녹음은 된다 (수업 외 이름)
            self.tt = None
            load_error = f'시간표(data.js)를 못 읽어 "녹음 날짜 시각" 이름으로 저장해요: {e}'

        self.rec = Recorder()
        self.started = None
        self.temp = None
        self.saved = None
        self.shown = 0.0
        self.red_until = 0.0

        pad = {'padx': 16, 'sticky': 'w'}
        self.status_var = tk.StringVar()
        tk.Label(root, textvariable=self.status_var, font=(FONT, 11, 'bold')).grid(row=0, pady=(14, 6), **pad)

        tk.Label(root, text='저장될 이름', font=(FONT, 9), fg=MUTED).grid(row=1, **pad)
        self.preview_var = tk.StringVar()
        tk.Label(root, textvariable=self.preview_var, font=(FONT, 11), wraplength=METER_W, justify='left').grid(row=2, pady=(0, 10), **pad)

        self.meter = tk.Canvas(root, width=METER_W, height=METER_H, bg='#e3e3e3', highlightthickness=0)
        self.meter.grid(row=3, padx=16)
        self.bar = self.meter.create_rectangle(0, 0, 0, METER_H, fill=GREEN, width=0)
        tk.Label(root, text='현재 음량', font=(FONT, 9), fg=MUTED).grid(row=4, pady=(2, 8), **pad)

        row = tk.Frame(root)
        row.grid(row=5, padx=16, pady=4, sticky='we')
        self.button = tk.Button(row, text='● 녹음', font=(FONT, 14, 'bold'), width=10, command=self.toggle)
        self.button.pack(side='left')
        self.elapsed_var = tk.StringVar(value='00:00:00')
        tk.Label(row, textvariable=self.elapsed_var, font=('Consolas', 22)).pack(side='right')

        mic = tk.Frame(root)
        mic.grid(row=6, padx=16, pady=(10, 4), sticky='we')
        tk.Label(mic, text='마이크', font=(FONT, 9)).pack(side='left')
        self.devices = [(None, 'Windows 기본 마이크')] + input_devices()
        self.mic = ttk.Combobox(mic, state='readonly', width=40, values=[n for _, n in self.devices])
        self.mic.current(0)
        self.mic.bind('<<ComboboxSelected>>', lambda e: self.open_mic())
        self.mic.pack(side='right')

        self.saved_frame = tk.Frame(root)
        self.name_var = tk.StringVar()
        tk.Label(self.saved_frame, text='저장됨 (이름을 고칠 수 있어요)', font=(FONT, 9), fg=MUTED).pack(anchor='w')
        tk.Entry(self.saved_frame, textvariable=self.name_var, font=(FONT, 10), width=46).pack(fill='x', pady=2)
        buttons = tk.Frame(self.saved_frame)
        buttons.pack(anchor='e')
        tk.Button(buttons, text='이름 바꾸기', command=self.rename).pack(side='left', padx=4)
        tk.Button(buttons, text='폴더 열기', command=self.open_folder).pack(side='left')

        self.warn_var = tk.StringVar(value=load_error)
        tk.Label(root, textvariable=self.warn_var, font=(FONT, 9), fg=RED, wraplength=METER_W, justify='left').grid(row=8, pady=(4, 12), **pad)

        root.protocol('WM_DELETE_WINDOW', self.on_close)
        self.open_mic()
        self.tick_names()
        self.tick_meter()
        self.tick_clock()

    # ---------- 마이크 ----------
    def open_mic(self):
        device = self.devices[self.mic.current()][0]
        try:
            self.rec.open(device)
            self.button.config(state='normal')
            if self.warn_var.get().startswith('마이크'):
                self.warn_var.set('')
        except Exception as e:
            self.button.config(state='disabled')
            self.warn_var.set(f'마이크를 열 수 없어요. 마이크 연결과 Windows 개인정보 설정(마이크 접근)을 확인하세요: {e}')

    # ---------- 주기 갱신 ----------
    def refresh_names(self):
        t = now()
        self.status_var.set(self.tt.status(t) if self.tt else '시간표 없음')
        if not self.rec.recording:
            m = self.tt.preview(t) if self.tt else None
            self.preview_var.set('예상 · ' + tt.file_name(m, t)[0])

    def tick_names(self):
        self.refresh_names()
        self.root.after(30_000, self.tick_names)

    def tick_meter(self):
        level = self.rec.take_level()
        frac = 0.0 if level <= 0 else max(0.0, min(1.0, (20 * math.log10(level) + 60) / 60))  # -60dB ~ 0dB
        self.shown = max(frac, self.shown - 0.04)  # 천천히 내려온다
        t = now().timestamp()
        if level >= 0.98:
            self.red_until = t + 1
        self.meter.coords(self.bar, 0, 0, int(METER_W * self.shown), METER_H)
        self.meter.itemconfig(self.bar, fill=RED if t < self.red_until else GREEN)
        self.root.after(50, self.tick_meter)

    def tick_clock(self):
        if self.rec.recording:
            s = int((now() - self.started).total_seconds())
            self.elapsed_var.set(f'{s // 3600:02}:{s % 3600 // 60:02}:{s % 60:02}')
            if self.rec.write_error is not None:
                self.stop(f'파일 쓰기 오류로 녹음을 멈췄어요: {self.rec.write_error}.')
            elif not self.rec.alive():
                self.stop('마이크 연결이 끊겨 녹음을 멈췄어요.')
        self.root.after(1000, self.tick_clock)

    # ---------- 녹음 ----------
    def toggle(self):
        if self.rec.recording:
            self.stop()
        else:
            self.start()

    def start(self):
        try:
            BASE.mkdir(parents=True, exist_ok=True)
            self.started = now()
            self.temp = tt.unique_path(BASE, f'녹음 중 {self.started:%Y-%m-%d %H-%M-%S}.mp3')
            self.rec.start(self.temp)
        except Exception as e:
            self.warn_var.set(f'녹음을 시작할 수 없어요: {e}')
            return
        keep_awake(True)
        self.preview_var.set(self.preview_var.get().replace('예상 · ', '녹음 중 · 예상 ', 1))
        self.saved_frame.grid_remove()
        self.button.config(text='■ 정지')
        self.mic.config(state='disabled')
        self.elapsed_var.set('00:00:00')

    def stop(self, reason=None):
        self.rec.stop()
        keep_awake(False)
        m = self.tt.match(self.started, now()) if self.tt else None
        name, folder_name = tt.file_name(m, self.started)
        folder = BASE / folder_name if folder_name else BASE
        try:
            folder.mkdir(parents=True, exist_ok=True)
            final = tt.unique_path(folder, name)
            os.replace(self.temp, final)
        except OSError as e:
            final = self.temp
            self.warn_var.set(f'이름을 바꾸지 못해 임시 이름으로 저장했어요: {e}')
        self.saved = final
        self.name_var.set(final.stem)
        self.saved_frame.grid(row=7, padx=16, pady=(8, 0), sticky='we')
        self.button.config(text='● 녹음')
        self.mic.config(state='readonly')
        self.refresh_names()
        if reason:
            messagebox.showwarning('수업 녹음기', f'{reason}\n그때까지 녹음은 저장했어요:\n{final}')
            self.open_mic()

    def rename(self):
        new = tt.safe(self.name_var.get())
        if not self.saved or not new:
            return
        if new.lower().endswith('.mp3'):
            new = new[:-4]
        target = self.saved.with_name(new + '.mp3')
        if target == self.saved:
            return
        if target.exists():
            self.warn_var.set('같은 이름의 파일이 이미 있어요.')
            return
        try:
            os.replace(self.saved, target)
            self.saved = target
            self.name_var.set(target.stem)
            self.warn_var.set('')
        except OSError as e:
            self.warn_var.set(f'이름을 바꾸지 못했어요: {e}')

    def open_folder(self):
        folder = self.saved.parent if self.saved else BASE
        folder.mkdir(parents=True, exist_ok=True)
        os.startfile(folder)

    def on_close(self):
        if self.rec.recording:
            self.stop()
        self.rec.close()
        self.root.destroy()


def main():
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 고해상도 화면에서 글자가 흐리지 않게
        except Exception:
            pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()
