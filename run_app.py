import os
import sys
import time
import webbrowser
import threading
import uvicorn

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://127.0.0.1:8080")

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.join(root_dir, "backend")
    
    if os.path.isdir(backend_dir):
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        os.chdir(backend_dir)
    else:
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)

    # Launch browser automatically
    threading.Thread(target=open_browser, daemon=True).start()

    print("=" * 60)
    print(" LocalTube is running!")
    print(" Web Interface: http://127.0.0.1:8080")
    print(" Press Ctrl+C in this terminal window to stop.")
    print("=" * 60)

    uvicorn.run("main:app", host="0.0.0.0", port=8080, log_level="info")

if __name__ == "__main__":
    main()
