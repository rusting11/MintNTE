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
import subprocess
import threading
import re
from PyQt5.QtCore import QObject, pyqtSignal

GITHUB_REPO = "daoqi/NTE-ai"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
LOCAL_VERSION_FILE = "version.txt"

class Updater(QObject):
    progress = pyqtSignal(int)           # 下载进度 0-100
    status = pyqtSignal(str)            # 状态文字
    finished = pyqtSignal(bool, str)    # 是否需要更新, 远程版本或空

    def __init__(self):
        super().__init__()
        self._cancel = False
        self._thread = None

    def cancel(self):
        self._cancel = True

    def get_local_version(self):
        if not os.path.exists(LOCAL_VERSION_FILE):
            return "0.0.0"
        with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()

    def check_for_update(self):
        """后台检查是否有新版本"""
        def run():
            self.status.emit("正在检查更新...")
            local = self.get_local_version()
            try:
                req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                remote_tag = data.get("tag_name", "0.0.0").lstrip("v")
                needs_update = local != remote_tag
                self.finished.emit(needs_update, remote_tag)
            except Exception as e:
                self.status.emit(f"检查更新失败: {e}")
                self.finished.emit(False, "")
        threading.Thread(target=run, daemon=True).start()

    def perform_update(self):
        """下载、校验、解压并退出，由辅助脚本完成替换重启"""
        def run():
            self.status.emit("正在获取最新版本...")
            try:
                req = urllib.request.Request(API_URL, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
            except Exception as e:
                self.status.emit(f"获取版本失败: {e}")
                self.finished.emit(False, "")
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
            # 尝试从发布说明中提取 SHA256
            body = data.get("body", "")
            expected_sha256 = None
            match = re.search(r'(?i)sha256[:\s]+([a-fA-F0-9]{64})', body)
            if match:
                expected_sha256 = match.group(1).lower()

            # 下载
            self.status.emit("正在下载更新包...")
            tmp_dir = tempfile.mkdtemp()
            zip_path = os.path.join(tmp_dir, "update.zip")
            if not self._download_file(download_url, zip_path):
                self.status.emit("下载失败或已取消")
                self.finished.emit(False, "")
                return

            # 校验
            if expected_sha256:
                self.status.emit("正在校验文件...")
                self.progress.emit(0)
                actual_sha = self._sha256_file(zip_path)
                if actual_sha != expected_sha256:
                    self.status.emit(f"SHA256 不匹配！\n期望: {expected_sha256[:16]}...\n实际: {actual_sha[:16]}...")
                    self.finished.emit(False, "")
                    return
                self.status.emit("文件校验通过 ✓")

            # 解压
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

            # 生成辅助更新脚本
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # updater/ -> 项目根
            # 修正：实际项目根是 main.py 所在目录，假设 updater 就在项目根下
            # 考虑到 updater.py 在项目根/updater/下，os.path.dirname(os.path.dirname(__file__)) 是项目根
            app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            helper_path = os.path.join(tmp_dir, "updater_helper.py")
            helper_code = f'''
import os, sys, time, shutil

old_root = r"{app_root}"
new_root = r"{extract_dir}"
main_script = r"{os.path.join(app_root, 'main.py')}"

time.sleep(2)  # 等待主程序退出

# 复制文件，跳过用户数据和不应覆盖的目录
for item in os.listdir(new_root):
    s = os.path.join(new_root, item)
    d = os.path.join(old_root, item)
    if item in ["version.txt", "nte_bohe.log", "fortissimo.log", "debug_screenshot.png",
                "macro_config.json", ".git", "__pycache__", "PIP.txt", "tools", "core", "UI", "Module", "Image", ".idea"]:
        continue
    if os.path.isdir(s):
        if os.path.exists(d):
            shutil.rmtree(d)
        shutil.copytree(s, d)
    else:
        shutil.copy2(s, d)

# 更新版本号文件
version_src = os.path.join(new_root, "version.txt")
if os.path.exists(version_src):
    shutil.copy2(version_src, os.path.join(old_root, "version.txt"))

# 重启主程序
os.execl(sys.executable, sys.executable, main_script)
'''
            with open(helper_path, "w", encoding="utf-8") as f:
                f.write(helper_code)

            self.status.emit("即将退出并更新...")
            creation_flags = subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            subprocess.Popen([sys.executable, helper_path], creationflags=creation_flags)
            # 退出主程序
            sys.exit(0)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

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
                        chunk = resp.read(1024 * 8)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            pct = int(downloaded / total * 100)
                            self.progress.emit(pct)
                            self.status.emit(f"正在下载... {pct}%")
                self.progress.emit(100)
                return True
        except Exception as e:
            self.status.emit(f"下载出错: {e}")
            return False

    def _sha256_file(self, filepath):
        sha = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha.update(chunk)
        return sha.hexdigest()