# updater/updater.py
import os, sys, json, tempfile, subprocess, zipfile, urllib.request, urllib.error, time
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread
from PyQt5.QtWidgets import QApplication
from UI import logui

GITHUB_REPO = "daoqi/MintNTE"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def _get_root_dir():
    if getattr(sys, 'frozen', False):
        return Path(os.path.dirname(sys.executable))
    else:
        return Path(__file__).resolve().parent.parent

def _get_local_version_path():
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "version.txt"
    else:
        return Path(__file__).resolve().parent.parent / "version.txt"

def read_local_version():
    path = _get_local_version_path()
    if not path.exists():
        return "0.0.0"
    raw = path.read_bytes()
    if raw.startswith(b'\xff\xfe'):
        text = raw[2:].decode('utf-16-le')
    elif raw.startswith(b'\xfe\xff'):
        text = raw[2:].decode('utf-16-be')
    elif raw.startswith(b'\xef\xbb\xbf'):
        text = raw[3:].decode('utf-8')
    else:
        try:
            text = raw.decode('utf-8')
        except:
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

class CheckUpdateThread(QThread):
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

class Updater(QObject):
    checkResult = pyqtSignal(int, str)
    progress = pyqtSignal(int)
    status = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._check_thread = None

    def cancel(self):
        if self._check_thread and self._check_thread.isRunning():
            self._check_thread.cancel()

    def get_local_version(self):
        return read_local_version()

    def check_for_update(self):
        if self._check_thread and self._check_thread.isRunning():
            return
        self._check_thread = CheckUpdateThread(self)
        self._check_thread.result.connect(self.checkResult)
        self._check_thread.start()

    def perform_update(self):
        """主线程同步下载更新，避免子线程信号崩溃"""
        self.status.emit("正在获取远程版本信息...")
        QApplication.processEvents()
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "MintNTE"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            self.status.emit(f"获取版本信息失败: {e}")
            self.progress.emit(0)
            return

        assets = data.get("assets", [])
        zip_asset = next((a for a in assets if a["name"].endswith(".zip")), None)
        if not zip_asset:
            self.status.emit("未找到更新压缩包")
            self.progress.emit(0)
            return

        download_url = zip_asset["browser_download_url"]
        self.status.emit("正在下载更新包...")
        QApplication.processEvents()
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, "update.zip")
        try:
            req = urllib.request.Request(download_url, headers={"User-Agent": "MintNTE"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(zip_path, "wb") as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(int(downloaded / total * 100))
                        QApplication.processEvents()
            self.progress.emit(100)
        except Exception as e:
            self.status.emit(f"下载失败: {e}")
            self.progress.emit(0)
            return

        self.status.emit("正在解压...")
        QApplication.processEvents()
        extract_dir = os.path.join(tmp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
        except Exception as e:
            self.status.emit(f"解压失败: {e}")
            self.progress.emit(0)
            return

        items = os.listdir(extract_dir)
        if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
            extract_dir = os.path.join(extract_dir, items[0])

        app_root = str(_get_root_dir())

        ps1_path = os.path.join(tempfile.gettempdir(), "mint_update.ps1")
        with open(ps1_path, "w", encoding="utf-8-sig") as f:
            f.write(f'''Write-Host "Waiting for MintNTE to exit..."
while (Get-Process -Name "MintNTE" -ErrorAction SilentlyContinue) {{
    Start-Sleep -Seconds 1
}}
$sourceDir = "{extract_dir}"
$destDir = "{app_root}"
Write-Host "Updating files..."
robocopy $sourceDir $destDir /E /MOVE /NP /NFL /NDL /NJH /NJS
Write-Host "Update complete. Starting..."
Start-Process -FilePath (Join-Path $destDir "MintNTE.exe")
Remove-Item -LiteralPath $MyInvocation.MyCommand.Path -Force
''')

        subprocess.Popen(
            f'powershell.exe -ExecutionPolicy Bypass -WindowStyle Hidden -File "{ps1_path}"',
            shell=True,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        )
        self.status.emit("即将退出以完成更新...")
        QApplication.processEvents()
        QApplication.quit()

    def skip_this_version(self, version):
        save_skip_version(version)

    def clear_skip(self):
        path = _get_root_dir() / "skip_version.txt"
        if path.exists():
            path.unlink()