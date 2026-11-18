"""
CappyAutoPost - Configuration & Settings
"""
import os
import sys
from pathlib import Path

# Base directories:
# APP_DIR: Writable folder where CappyAutoPost.exe sits (stores db, logs, .cache)
# BUNDLE_DIR: Folder where PyInstaller bundles static assets (ui/web)
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
else:
    APP_DIR = Path(__file__).resolve().parent.parent
    BUNDLE_DIR = APP_DIR

BASE_DIR = APP_DIR
DB_PATH = APP_DIR / "cappy_autopost.db"
ASSETS_DIR = APP_DIR / "assets"
LOGS_DIR = APP_DIR / "logs"

# Ensure runtime directories exist
LOGS_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

# Default Automation Settings
DEFAULT_SETTINGS = {
    "min_delay_between_posts": 180,  # 3 minutes
    "max_delay_between_posts": 420,  # 7 minutes
    "typing_speed_min_ms": 25,
    "typing_speed_max_ms": 85,
    "max_posts_per_account_daily": 20,
    "cooldown_on_warning_minutes": 30,
    "headless_browser": False,
    "user_agent_desktop": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "mbasic_user_agent": (
        "Mozilla/5.0 (Linux; Android 10; SM-G981B) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36"
    )
}
