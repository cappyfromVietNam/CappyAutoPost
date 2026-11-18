"""
CappyAutoPost - PyInstaller Packaging Script
Builds standalone clean executable for Windows.
Excludes all personal databases, tokens, cookies, logs, and cache.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build():
    mode = "--onedir" if "--onedir" in sys.argv else "--onefile"
    print("=" * 60)
    print(f"Building CappyAutoPost Windows Executable ({mode})...")
    print("Zero-leak guarantee: Only UI assets are bundled.")
    print("=" * 60)

    # Clean previous build artifacts
    for d in (BASE_DIR / "build", BASE_DIR / "dist"):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)

    cmd = [
        sys.executable,
        "-m", "PyInstaller",
        "--name=CappyAutoPost",
        "--noconfirm",
        "--clean",
        mode,
        "--windowed", # Hide black console window
        f"--add-data={BASE_DIR / 'ui' / 'web'};ui/web",
        "--hidden-import=webview",
        "--hidden-import=webview.platforms.winforms",
        "--hidden-import=webview.platforms.edgechromium",
        "--hidden-import=clr",
        "--hidden-import=clr_loader",
        "--hidden-import=pythonnet",
        "--hidden-import=sqlite3",
        "--hidden-import=undetected_chromedriver",
        "--hidden-import=selenium",
        "--hidden-import=selenium.webdriver.common.by",
        "--hidden-import=selenium.webdriver.support.ui",
        "--hidden-import=selenium.webdriver.support.expected_conditions",
        "--hidden-import=requests",
        "--hidden-import=urllib3",
        "--hidden-import=certifi",
        str(BASE_DIR / "cappy_app.py")
    ]

    print("Running command:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    if result.returncode == 0:
        if mode == "--onefile":
            exe_path = BASE_DIR / "dist" / "CappyAutoPost.exe"
            size_mb = exe_path.stat().st_size / (1024 * 1024) if exe_path.exists() else 0
            print(f"\n[OK] Build successful! Standalone executable: {exe_path} ({size_mb:.2f} MB)")
        else:
            exe_dir = BASE_DIR / "dist" / "CappyAutoPost"
            print(f"\n[OK] Build successful! Application directory: {exe_dir}")
    else:
        print(f"\n[FAIL] Build failed with exit code {result.returncode}")
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()
