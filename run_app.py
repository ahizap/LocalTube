import os
import sys
import time
import webbrowser
import threading

# Determine environment: frozen (PyInstaller executable) vs script/source
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, "backend")

if getattr(sys, 'frozen', False):
    # Running inside a PyInstaller frozen bundle
    app_dir = os.path.dirname(sys.executable)
    # Ensure working directory is the application root (where LocalTube.exe resides)
    # This guarantees the 'data' folder and cache are created alongside the executable.
    os.chdir(app_dir)
    base_dir = getattr(sys, '_MEIPASS', app_dir)
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    bundled_backend = os.path.join(base_dir, "backend")
    if os.path.isdir(bundled_backend) and bundled_backend not in sys.path:
        sys.path.insert(0, bundled_backend)
else:
    # Running from source
    if os.path.isdir(backend_dir) and backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    os.chdir(root_dir)

import uvicorn
from main import app


def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8080")


def main():
    # Launch browser automatically
    threading.Thread(target=open_browser, daemon=True).start()

    print("=" * 60)
    print(" LocalTube is running!")
    print(" Web Interface: http://127.0.0.1:8080")
    print(" Press Ctrl+C in this terminal window to stop.")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()
