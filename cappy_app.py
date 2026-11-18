"""
CappyAutoPost - Main Application Entrypoint
Version: 2.0.0
Author: Google Deepmind Antigravity Pair Programming
Zero Backdoor • Anti-Ban • SQLite Database • Undetected ChromeDriver
"""
import os
import sys
import subprocess
from pathlib import Path

from config.settings import BASE_DIR, BUNDLE_DIR

# Add project root and bundle dir to sys.path
sys.path.insert(0, str(BASE_DIR))
if str(BUNDLE_DIR) != str(BASE_DIR):
    sys.path.insert(0, str(BUNDLE_DIR))

# Auto-bootstrap: Seamlessly switch to project .venv if executed from global python (dev mode only)
if not getattr(sys, "frozen", False):
    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists() and Path(sys.executable).resolve() != venv_python.resolve():
        sys.exit(subprocess.call([str(venv_python)] + sys.argv))

import logging
import webview
from database import init_db
from ui.api import WebviewAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CappyApp")

def main():
    logger.info("Initializing CappyAutoPost database...")
    init_db()

    if "--dry-run" in sys.argv:
        logger.info("CappyAutoPost initialized in dry-run mode successfully!")
        return

    html_path = BUNDLE_DIR / "ui" / "web" / "index.html"
    if not html_path.exists():
        logger.error(f"UI file not found: {html_path}")
        sys.exit(1)

    api = WebviewAPI()

    window = webview.create_window(
        title="CappyAutoPost v2.0 - Hệ Thống Tự Động Hóa Facebook Đa Tài Khoản",
        url=str(html_path.resolve()),
        js_api=api,
        width=1240,
        height=800,
        min_size=(1040, 680),
        background_color="#18120e"
    )

    api.set_window(window)

    logger.info("Launching CappyAutoPost Desktop Application...")
    webview.start(debug=False)

if __name__ == "__main__":
    main()
