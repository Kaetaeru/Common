"""수업 녹음기 exe 를 만들어 바탕화면에 복사한다.

실행: python build_exe.py
(빌드 전용 가상환경 .build-venv 를 만들어 PyInstaller 로 한 파일 exe 를 만든다.)
"""
import ctypes
import shutil
import subprocess
import sys
import venv
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
VENV = HERE / '.build-venv'
PY = VENV / 'Scripts' / 'python.exe'
NAME = '수업 녹음기'
DATA_JS = HERE.parent / 'docs' / 'my-timetable' / 'data.js'


def desktop():
    """바탕화면 경로 (OneDrive 로 옮겨진 경우 포함)."""
    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x0000, None, 0, buf)  # CSIDL_DESKTOP
    return Path(buf.value)


def make_icon(path):
    """빨간 녹음 점 아이콘."""
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, 248, 248), radius=56, fill=(30, 107, 82))
    d.ellipse((68, 68, 188, 188), fill=(235, 72, 60))
    img.save(path, sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])


def main():
    if not PY.exists():
        venv.create(VENV, with_pip=True)
    subprocess.run([PY, '-m', 'pip', 'install', '-q', '-r', HERE / 'requirements.txt', 'pyinstaller', 'pillow'], check=True)
    icon = HERE / 'build' / 'icon.ico'
    icon.parent.mkdir(exist_ok=True)
    subprocess.run([PY, '-c', f'import build_exe; build_exe.make_icon(r"{icon}")'], cwd=HERE, check=True)
    subprocess.run([PY, '-m', 'PyInstaller', '--noconfirm', '--onefile', '--windowed',
                    '--name', NAME, '--icon', icon, '--add-data', f'{DATA_JS};.', '--add-data', f'{icon};.', 'app.py'],
                   cwd=HERE, check=True)
    exe = HERE / 'dist' / f'{NAME}.exe'
    target = desktop() / exe.name
    shutil.copy2(exe, target)
    print(f'완료: {target}')


if __name__ == '__main__':
    sys.exit(main())
