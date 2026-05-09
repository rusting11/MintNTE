# updater/updater.py
import os
import sys
import hashlib
import urllib.request
import urllib.error
import json
import tempfile
import zipfile
import shutil
import time
import subprocess
import re
import psutil
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread

GITHUB_REPO = "daoqi/MintNTE"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def _get_local_version_path():
    if getattr(sys, 'frozen', False):
        external = Path(os.path.dirname(sys.executable)) / "version.txt"
        if external.exists():
            return external
        return Path(sys._MEIPASS) / "version.txt"
    else:
        return Path(__file__).resolve().parent.parent / "version.txt"


def read_local_version():
    path = _get_local_version_path()
    if not path.exists():
        return "0.0.0"
    for encoding in ['utf-8', 'gbk', 'utf-16-le', 'utf-16-be']:
        try:
            return path.read_text(encoding=encoding).strip()
        except:
            continue
    return "0.0.0"


def parse_version(v_str):
    """将版本号字符串转换为元组，用于比较"""
    try:
        return tuple(map(int, v_str.split('.')))
    except:
        return (0, 0, 0)


class CheckUpdateThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel = False

    def cancel(self):
        self._cancel = True
        self.wait(2000)

    def run(self):
        if self._cancel:
            return
        local = read_local_version()
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            remote_tag = data.get("tag_name", "0.0.0").lstrip("v")
            # 只有远程版本大于本地版本时才需要更新
            needs_update = parse_version(remote_tag) > parse_version(local)
            if not self._cancel:
                self.finished.emit(needs_update, remote_tag)
        except Exception:
            if not self._cancel:
                self.finished.emit(False, "")


class DownloadUpdateThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cancel = False

    def cancel(self):
        self._cancel = True
        self.wait(2000)

    def run(self):
        self.status.emit("正在获取最新版本...")
        try:
            req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            if not self._cancel:
                self.status.emit(f"获取版本失败: {e}")
                self.finished.emit(False, "")
            return

        if self._cancel:
            return
        assets = data.get("assets", [])
        if not assets:
            self.status.emit("没有可下载的更新包")
            self.finished.emit(False, "")
            return

        zip_asset = next((a for a in assets if a["name"].endswith(".zip")), None)
        if not zip_asset:
            self.status.emit("未找到 .zip 更新包")
            self.finished.emit(False, "")
            return

        download_url = zip_asset["browser_download_url"]
        body = data.get("body", "")
        expected_sha256 = None
        match = re.search(r'(?i)sha256[:\s]+([a-fA-F0-9]{64})', body)
        if match:
            expected_sha256 = match.group(1).lower()

        self.status.emit("正在下载更新包...")
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, "update.zip")
        if not self._download_file(download_url, zip_path):
            if not self._cancel:
                self.status.emit("下载失败或已取消")
                self.finished.emit(False, "")
            return

        if expected_sha256:
            self.status.emit("正在校验文件...")
            self.progress.emit(0)
            actual_sha = self._sha256_file(zip_path)
            if actual_sha != expected_sha256:
                self.status.emit("SHA256 不匹配！")
                self.finished.emit(False, "")
                return
            self.status.emit("文件校验通过 ✓")

        self.status.emit("正在解压...")
        extract_dir = os.path.join(tmp_dir, "extracted")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)
        except Exception as e:
            self.status.emit(f"解压失败: {e}")
            self.finished.emit(False, "")
            return

        # 处理压缩包外层文件夹包裹
        items = os.listdir(extract_dir)
        if len(items) == 1:
            single_dir = os.path.join(extract_dir, items[0])
            if os.path.isdir(single_dir):
                extract_dir = single_dir

        if getattr(sys, 'frozen', False):
            app_root = os.path.dirname(sys.executable)
        else:
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        helper_temp_path = os.path.join(tempfile.gettempdir(), "mint_updater_helper.py")
        helper_code = f'''
import os, sys, time, shutil, logging, psutil, subprocess

LOG_PATH = r"{os.path.join(tempfile.gettempdir(), 'mint_updater.log')}"
logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format='%(asctime)s - %(message)s')

def force_remove(path):
    for _ in range(5):
        try:
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                if os.path.exists(path):
                    os.remove(path)
            return True
        except Exception as e:
            logging.warning(f"删除 {{path}} 失败: {{e}}")
            time.sleep(1)
    return False

def wait_old_exe_gone():
    for _ in range(20):
        try:
            running = any(p.name().lower() == "mintnte.exe" for p in psutil.process_iter(['name']))
            if not running:
                return True
        except:
            pass
        time.sleep(0.8)
    return False

def main():
    try:
        logging.info("更新脚本启动")
        wait_old_exe_gone()
        time.sleep(1)

        old_root = r"{app_root}"
        new_root = r"{extract_dir}"

        ignore_list = [
            "nte_bohe.log", "fortissimo.log", "debug_screenshot.png",
            "macro_config.json", ".git", "__pycache__", "PIP.txt", "tools"
        ]

        for item in os.listdir(new_root):
            if item in ignore_list:
                continue
            s = os.path.join(new_root, item)
            d = os.path.join(old_root, item)
            force_remove(d)
            for attempt in range(3):
                try:
                    if os.path.isdir(s):
                        shutil.copytree(s, d, dirs_exist_ok=True)
                    else:
                        shutil.copy2(s, d)
                    break
                except Exception as e:
                    logging.warning(f"复制 {{s}} 失败: {{e}}")
                    time.sleep(1.5)
                    force_remove(d)

        version_src = os.path.join(new_root, "version.txt")
        version_dst = os.path.join(old_root, "version.txt")
        if os.path.exists(version_src):
            force_remove(version_dst)
            shutil.copy2(version_src, version_dst)

        logging.info("文件替换完成，启动新程序")
        target_exe = os.path.join(old_root, "MintNTE.exe")
        if os.path.exists(target_exe):
            subprocess.Popen([target_exe], shell=True, close_fds=True)
        else:
            subprocess.Popen([sys.executable, os.path.join(old_root, "main.py")], shell=True)
        sys.exit(0)
    except Exception as e:
        logging.error(f"更新失败: {{e}}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''

        with open(helper_temp_path, "w", encoding="utf-8") as f:
            f.write(helper_code)

        creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        subprocess.Popen([sys.executable, helper_temp_path], creationflags=creation_flags, close_fds=True)

        time.sleep(1)
        self.status.emit("即将退出并更新...")
        self.finished.emit(True, "")

    def _download_file(self, url, dest):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
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
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()


class Updater(QObject):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

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
        self._check_thread = CheckUpdateThread(self)
        self._check_thread.finished.connect(self.finished)
        self._check_thread.start()

    def perform_update(self):
        self._download_thread = DownloadUpdateThread(self)
        self._download_thread.progress.connect(self.progress)
        self._download_thread.status.connect(self.status)
        self._download_thread.finished.connect(self._on_download_finished)
        self._download_thread.start()

    def _on_download_finished(self, success, version):
        if success:
            time.sleep(0.5)
            sys.exit(0)
        else:
            self.finished.emit(False, version)