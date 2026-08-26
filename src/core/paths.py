import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
LOGS_DIR = PROJECT_ROOT / "logs"
ASSETS_DIR = PROJECT_ROOT / "assets"
TRAY_ICON_FILE = ASSETS_DIR / "icons" / "tray.png"
CHAMPIONS_DIR = ASSETS_DIR / "champions"
SPELLS_DIR = ASSETS_DIR / "spells"
DATA_DIR = ASSETS_DIR / "data"
SUMMONER_DATA_FILE = DATA_DIR / "summoner.json"
CHAMPIONS_DATA_FILE = DATA_DIR / "champions.json"
DATA_VERSION_FILE = DATA_DIR / "version.txt"
RIOT_CERT_FILE = ASSETS_DIR / "certs" / "riotgames.pem"
