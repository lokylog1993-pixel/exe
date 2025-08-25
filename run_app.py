
import os, threading, time, sys, pathlib

# Use a user-writable state dir by default
home = pathlib.Path.home()
default_state_dir = home / ".bitd_gm_ai"
default_state_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BITD_STATE_PATH", str(default_state_dir / "state.json"))

# Start FastAPI server in a background thread
def start_server():
    import uvicorn
    from app.server import app as fastapi_app
    config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=int(os.getenv("PORT", "8000")), log_level="info")
    server = uvicorn.Server(config)
    server.run()

def start_ui():
    # Launch gradio UI on 127.0.0.1:7860 without blocking
    from app.ui import demo
    try:
        demo.queue()  # allow concurrency
    except Exception:
        pass
    demo.launch(server_name="127.0.0.1", server_port=7860, prevent_thread_lock=True, show_error=True)

def wait_for(url, timeout=15.0):
    import time, urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def main():
    t1 = threading.Thread(target=start_server, daemon=True)
    t1.start()
    t2 = threading.Thread(target=start_ui, daemon=True)
    t2.start()

    url = "http://127.0.0.1:7860"
    # Wait for UI to be live, then open a native window
    ok = wait_for(url, timeout=20.0)
    try:
        import webview
    except Exception as e:
        print("pywebview не установлен. Откройте вручную:", url)
        print("Ошибка:", e)
        import webbrowser; webbrowser.open(url)
        t1.join(); t2.join()
        return

    window = webview.create_window("BitD GM AI", url, width=1200, height=800)
    webview.start(gui='edgechromium')  # blocks until closed

if __name__ == "__main__":
    main()
