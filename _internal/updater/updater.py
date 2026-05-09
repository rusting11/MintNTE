# updater/updater.py
import os, sys, hashlib, urllib.request, urllib.error, json, tempfile, subprocess
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication
from UI import logui

GITHUB_REPO = "daoqi/MintNTE"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# ---------- 路径辅助函数 ----------
def _get_root_dir():
    """程序根目录（打包后为exe所在目录，开发环境为项目根目录）"""
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable))
    else:
        return Path(__file__).resolve().parent.parent

def _get_local_version_path():
    """获取版本文件路径，打包后强制使用 sys._MEIPASS"""
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "version.txt"
    else:
        return Path(__file__).resolve().parent.parent / "version.txt"

def read_local_version():
    path = _get_local_version_path()
    if not path.exists():
        return "0.0.0"
    raw = path.read_bytes()
    # 移除 BOM
    if raw.startswith(b'\xff\xfe'):
        text = raw[2:].decode('utf-16-le')
    elif raw.startswith(b'\xfe\xff'):
        text = raw[2:].decode('utf-16-be')
    elif raw.startswith(b'\xef\xbb\xbf'):
        text = raw[3:].decode('utf-8')
    else:
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            text = raw.decode('utf-16-le')
    return text.strip()

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
    result = pyqtSignal(int, str)   # status: 1=有更新, 0=无更新, -1=错误

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

# ---------- 下载并更新线程 ----------
class DownloadUpdateThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool)

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

        # 找到 .exe 资源
        assets = data.get("assets", [])
        exe_asset = next((a for a in assets if a["name"].endswith(".exe")), None)
        if not exe_asset:
            self.status.emit("未找到 .exe 更新文件")
            self.finished.emit(False)
            return

        download_url = exe_asset["browser_download_url"]
        self.status.emit("正在下载新版本...")
        tmp_dir = tempfile.mkdtemp()
        exe_path = os.path.join(tmp_dir, "MintNTE.exe")

        if not self._download_file(download_url, exe_path):
            if not self._cancel:
                self.status.emit("下载失败")
            self.finished.emit(False)
            return

        # 目标路径
        app_root = str(_get_root_dir())
        target_exe = os.path.join(app_root, "MintNTE.exe")

        # 生成 PowerShell 更新脚本（支持中文路径、无乱码）
        ps1_path = os.path.join(tempfile.gettempdir(), "mint_update.ps1")
        with open(ps1_path, "w", encoding="utf-8-sig") as f:
            f.write(f'''Write-Host "Waiting for MintNTE to exit..."
while (Get-Process -Name "MintNTE" -ErrorAction SilentlyContinue) {{
    Start-Sleep -Seconds 1
}}
$source = "{exe_path}"
$dest = "{target_exe}"
if (-not (Test-Path $source)) {{
    Write-Host "ERROR: Downloaded exe not found!"
    Read-Host "Press Enter"
    exit 1
}}
Copy-Item -Path $source -Destination $dest -Force
Write-Host "Update complete, starting..."
Start-Process -FilePath $dest
Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force
''')

        # 启动脚本，脱离当前进程
        subprocess.Popen(
            f'powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps1_path}"',
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
        except:
            return False

# ---------- Updater 主控 ----------
class Updater(QObject):
    checkResult = pyqtSignal(int, str)
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