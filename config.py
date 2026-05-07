from pathlib import Path

CONFIG_DIR = Path(__file__).parent.resolve()
TITLE_LOGO_PATH = CONFIG_DIR / "Image" / "logo" / "titlelogo.ico"

APP_NAME = "MintNTE"

def get_version():
    version_file = CONFIG_DIR / "version.txt"
    if version_file.exists():
        return version_file.read_text(encoding='utf-8').strip()
    return "1.0.0"

VERSION = get_version()

REPO_OWNER = "daoqi"
REPO_NAME = "MintNTE"