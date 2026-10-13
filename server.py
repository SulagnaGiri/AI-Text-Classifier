
import json
import os
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from classifier import classify_message

UI_DIR = Path(__file__).parent / "ui"
PORT = int(os.getenv("PORT", "8000"))  # e.g. PORT=5010 python server.py


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve files (index.html) from the ui/ folder.
        super().__init__(*args, directory=str(UI_DIR), **kwargs)

    def do_POST(self):
        if self.path != "/api/classify":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            result = classify_message(str(body.get("message", "")))
            self._send_json(200, result)
        except Exception as error:
            self._send_json(500, {"error": str(error)})

    def _send_json(self, status: int, data: dict):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


if __name__ == "__main__":
    # Threading server: one slow LLM call does not block other requests.
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Open http://localhost:{PORT}")
    server.serve_forever()
