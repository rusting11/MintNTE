# updater/updater.py
import os, sys, hashlib, urllib.request, urllib.error, json, tempfile, zipfile, shutil, time, subprocess, re
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication
from UI import logui

GITHUB_REPO = "daoqi/MintNTE"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# ---------- 文件路径辅助 ----------
def _get_root_dir():
    """获取程序根目录（PyInstaller打包后为exe所在目录，开发环境为项目根目录）"""
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable))
    else:
        return Path(__file__).resolve().parent.parent

def read_local_version():
    path = _get_root_dir() / "version.txt"
    if not path.exists():
        return "0.0.0"
    try:
        return path.read_text(encoding='utf-8').strip()
    except:
        return "0.0.0"

def read_skip_version():
    path = _get_root_dir() / "skip_version.txt"
    if path.exists():
        return path.read_text(encoding='utf-8').strip()
    return ""

def save_skip_version(version):
    (_get_root_dir() / "skip_version.txt").write_text(version)

def parse_version(v):
    try:
        return tuple(map(int, v.split('.')))
    except:
        return (0, 0, 0)


# ---------- 检查更新线程 ----------
class CheckUpdateThread(QThread):
    # status: 1=有更新, 0=无更新或已跳过, -1=错误; info=版本号或错误信息
    result = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel = False

    def cancel(self):
        self._cancel = True
        self.wait(2000)

    def run(self):
        if self._cancel: return
        local = read_local_version()
        skip_ver = read_skip_version()
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "MintNTE"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            remote_tag = data.get("tag_name", "0.0.0").lstrip("v")
            if remote_tag == skip_ver:
                self.result.emit(0, remote_tag)
                return
            needs_update = parse_version(remote_tag) > parse_version(local)
            self.result.emit(1 if needs_update else 0, remote_tag)
        except Exception as e:
            logui.error(f"检查更新失败: {e}")
            self.result.emit(-1, str(e))


# ---------- 下载并应用更新线程 ----------
class DownloadUpdateThread(QThread):
    progress = pyqtSignal(int)       # 下载进度 0-100
    status = pyqtSignal(str)         # 状态文字
    finished = pyqtSignal(bool)      # True=下载并触发更新成功（退出程序前）

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel = False

    def cancel(self):
        self._cancel = True
        self.wait(2000)

    def run(self):
        self.status.emit("正在获取远程版本信息...")
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "MintNTE"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            self.status.emit(f"获取版本信息失败: {e}")
            self.finished.emit(False)
            return

        assets = data.get("assets", [])
        zip_asset = next((a for a in assets if a["name"].endswith(".zip")), None)
        if not zip_asset:
            self.status.emit("未找到 .zip 更新包")
            self.finished.emit(False)
            return

        download_url = zip_asset["browser_download_url"]
        # 提取 Release 描述中的 SHA256
        body = data.get("body", "")
        expected_sha = None
        match = re.search(r'(?i)sha256[:\s]+([a-fA-F0-9]{64})', body)
        if match:
            expected_sha = match.group(1).lower()

        self.status.emit("正在下载更新包...")
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, "update.zip")
        if not self._download_file(download_url, zip_path):
            if not self._cancel:
                self.status.emit("下载失败")
                self.finished.emit(False)
            return

        if expected_sha:
            self.status.emit("正在校验文件...")
            actual = self._sha256_file(zip_path)
            if actual != expected_sha:
                self.status.emit("SHA256 校验失败，文件损坏")
                self.finished.emit(False)
                return

        self.status.emit("正在解压...")
        extract_dir = os.path.join(tmp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
        except Exception as e:
            self.status.emit(f"解压失败: {e}")
            self.finished.emit(False)
            return

        # 若压缩包内只有一个文件夹，进入该文件夹
        items = os.listdir(extract_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            extract_dir = os.path.join(extract_dir, items[0])

        app_root = str(_get_root_dir())

        # 生成临时批处理，等待主程序退出后替换文件并启动新版本
        bat_path = os.path.join(tempfile.gettempdir(), "mint_update.bat")
        with open(bat_path, "w", encoding="gbk") as f:
            f.write(f'''@echo off
chcp 65001 >nul
echo 正在等待 MintNTE 退出...
:waitloop
timeout /t 1 /nobreak >nul
tasklist /FI "IMAGENAME eq MintNTE.exe" 2>NUL | find /I "MintNTE.exe" >NUL
if not errorlevel 1 goto waitloop

echo 正在替换文件...
xcopy "{extract_dir}\\*" "{app_root}\\" /E /Y /Q >nul
if errorlevel 1 (
    echo 文件替换失败，请手动覆盖更新。
    pause
    exit /b 1
)

echo 更新完成，正在启动新版本...
start "" "{app_root}\\MintNTE.exe"
del "%~f0" & exit
''')

        # 启动批处理（与当前进程脱离）
        subprocess.Popen(
            f'cmd /c start "" "{bat_path}"',
            shell=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )

        self.status.emit("即将退出以完成更新...")
        self.finished.emit(True)

    def _download_file(self, url, dest):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MintNTE"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(dest, "wb") as f:
                    while True:
                        if self._cancel:
                            return False
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(int(downloaded / total * 100))
            self.progress.emit(100)
            return True
        except Exception:
            return False

    @staticmethod
    def _sha256_file(filepath):
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(8192):
                sha.update(chunk)
        return sha.hexdigest()


# ---------- Updater 主控 ----------
class Updater(QObject):
    checkResult = pyqtSignal(int, str)   # -1=错误, 0=无更新, 1=有更新
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_thread = None
        self._download_thread = None

    def cancel(self):
        if self._check_thread and self._check_thread.isRunning():
            self._check_thread.cancel()
        if self._download_thread and self._download_thread.isRunning():
            self._download_thread.cancel()

    def get_local_version(self):
        return read_local_version()

    def check_for_update(self):
        if self._check_thread and self._check_thread.isRunning():
            return
        self._check_thread = CheckUpdateThread(self)
        self._check_thread.result.connect(self.checkResult)
        self._check_thread.start()

    def perform_update(self):
        if self._download_thread and self._download_thread.isRunning():
            self.status.emit("正在更新中，请稍候...")
            return
        self._download_thread = DownloadUpdateThread(self)
        self._download_thread.progress.connect(self.progress)
        self._download_thread.status.connect(self.status)
        self._download_thread.finished.connect(self._on_download_end)
        self._download_thread.start()

    def _on_download_end(self, success):
        if success:
            # 下载完成，批处理已运行，退出主程序
            QApplication.quit()
        else:
            self.status.emit("更新失败，请重试或手动下载")
            self.progress.emit(0)

    def skip_this_version(self, version):
        save_skip_version(version)

    def clear_skip(self):
        path = _get_root_dir() / "skip_version.txt"
        if path.exists():
            path.unlink()