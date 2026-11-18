"""
CappyAutoPost - Undetected ChromeDriver Manager
Features:
- Anti-bot detection stealth configuration
- Dedicated temporary profile per session to prevent disk/RAM leaks
- Proxy injection support
- Safe automatic cleanup on exit
"""
import os
import time
import shutil
import tempfile
import random
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from config.settings import DEFAULT_SETTINGS, BASE_DIR

# Ensure undetected_chromedriver data path stays inside local cache
UC_CACHE_DIR = BASE_DIR / ".cache" / "undetected_chromedriver"
UC_CACHE_DIR.mkdir(parents=True, exist_ok=True)
uc.Patcher.data_path = str(UC_CACHE_DIR)

VIEWPORT_SIZES = [
    (1366, 768),
    (1440, 900),
    (1536, 864),
    (1600, 900),
    (1280, 800)
]

def safe_remove_tree(dir_path: str, max_retries: int = 6, delay: float = 0.35) -> bool:
    """Safely removes a directory tree on Windows handling file locks and read-only attributes."""
    if not dir_path or not os.path.exists(dir_path):
        return True

    import stat
    def on_rm_error(func, path, exc_info):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception:
            pass

    for _ in range(max_retries):
        try:
            shutil.rmtree(dir_path, onerror=on_rm_error)
            if not os.path.exists(dir_path):
                return True
        except Exception:
            pass
        time.sleep(delay)

    return not os.path.exists(dir_path)

class BrowserManager:
    def __init__(self, proxy_str: Optional[str] = None, headless: bool = True):
        self.proxy_str = proxy_str
        self.headless = headless
        self.driver = None
        self.user_data_dir = None

    def start(self) -> uc.Chrome:
        """Starts undetected-chromedriver with stealth and background settings."""
        self.user_data_dir = tempfile.mkdtemp(prefix="cappy_profile_")

        options = uc.ChromeOptions()
        options.add_argument(f"--user-data-dir={self.user_data_dir}")
        options.add_argument("--disable-notifications")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-default-apps")
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--password-store=basic")
        options.add_argument("--lang=vi-VN,vi,en-US,en")
        options.add_argument("--no-focus-on-map")
        options.add_argument("--disable-backgrounding-occluded-windows")

        # Headless & background mode (no window, no mouse takeover)
        if self.headless:
            options.add_argument("--headless=new")
            options.add_argument("--window-position=-32000,-32000")
            options.add_argument("--disable-gpu")
        
        # Proxy configuration
        if self.proxy_str and self.proxy_str.strip():
            raw_proxy = self.proxy_str.strip()
            # If standard ip:port
            if not raw_proxy.startswith("http://") and not raw_proxy.startswith("socks5://"):
                parts = raw_proxy.split(":")
                if len(parts) == 2:
                    options.add_argument(f"--proxy-server=http://{parts[0]}:{parts[1]}")
                elif len(parts) == 4:
                    # Chrome natively supports host:port via arg, auth via extension or url
                    options.add_argument(f"--proxy-server=http://{parts[0]}:{parts[1]}")
            else:
                options.add_argument(f"--proxy-server={raw_proxy}")

        # Randomize screen resolution
        width, height = random.choice(VIEWPORT_SIZES)
        options.add_argument(f"--window-size={width},{height}")

        # Start undetected driver
        self.driver = uc.Chrome(
            options=options,
            headless=self.headless,
            use_subprocess=True
        )

        try:
            self.driver.set_window_size(width, height)
        except Exception:
            pass

        return self.driver

    def close(self) -> None:
        """Safely terminates the browser process and purges temporary files."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

        if self.user_data_dir:
            safe_remove_tree(self.user_data_dir)
            self.user_data_dir = None

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
