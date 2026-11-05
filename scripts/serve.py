"""Double-click launch_dashboard.cmd, or run python scripts/serve.py."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import webbrowser

root=Path(__file__).resolve().parents[1]/'docs'
url='http://127.0.0.1:8765'
try:
    server=ThreadingHTTPServer(('127.0.0.1',8765),partial(SimpleHTTPRequestHandler,directory=str(root)))
except OSError:
    raise SystemExit('Port 8765 is in use. Stop the previous preview or use the README command with another port.')
print('Dashboard: '+url+'\nKeep this window open. Press Ctrl+C to stop.',flush=True)
threading.Timer(0.8,lambda:webbrowser.open(url)).start()
try: server.serve_forever()
except KeyboardInterrupt: pass
finally: server.server_close()
