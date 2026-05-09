from pathlib import Path

CONFIG_DIR = Path(__file__).parent.resolve()
TITLE_LOGO_PATH = CONFIG_DIR / "Image" / "logo" / "titlelogo.ico"

APP_NAME = "MintNTE"

def get_version():
    version_file = CONFIG_DIR / "version.txt"
    if not version_file.exists():
        return "1.0.0"
    raw = version_file.read_bytes()
    # 判断并剔除 BOM，然后解码
    if raw.startswith(b'\xff\xfe'):          # UTF-16 LE BOM
        text = raw[2:].decode('utf-16-le')
    elif raw.startswith(b'\xfe\xff'):        # UTF-16 BE BOM
        text = raw[2:].decode('utf-16-be')
    elif raw.startswith(b'\xef\xbb\xbf'):    # UTF-8 BOM
        text = raw[3:].decode('utf-8')
    else:
        # 纯 ASCII 或 UTF-8 无 BOM，直接尝试解码
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            # 最后尝试 UTF-16 LE（常见于记事本默认保存）
            text = raw.decode('utf-16-le')
    return text.strip()

VERSION = get_version()

REPO_OWNER = "daoqi"
REPO_NAME = "MintNTE"