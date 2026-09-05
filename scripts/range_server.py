"""Minimal static HTTP server with Range support that logs every request.

Serves data/out on localhost:8765.  Each request is appended to
results/http_requests.log as  <epoch>\t<method>\t<path>\t<range>\t<status>\t<bytes>
so the benchmark can count how many round-trips a single read costs.
Python's built-in http.server lacks Range, which /vsicurl and fsspec need.
"""
import os, re, sys, time, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVE = ROOT / "data/out"
LOG = ROOT / "results/http_requests.log"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
_lock = threading.Lock()
_logf = None   # opened once: re-opening the file per request cost ~40 ms on Windows and serialised parallel fetches

class H(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    disable_nagle_algorithm = True   # TCP_NODELAY: without it Windows loopback adds ~40 ms per response (Nagle + delayed ACK)
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(SERVE), **k)
    def log_message(self, *a):  # silence stderr
        pass
    def _log(self, status, nbytes):
        rng = self.headers.get("Range", "-")
        with _lock:
            _logf.write(f"{time.time():.6f}\t{self.command}\t{self.path}\t{rng}\t{status}\t{nbytes}\n"); _logf.flush()
    def do_HEAD(self):
        p = Path(self.translate_path(self.path))
        if p.is_file():
            self.send_response(200); self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(p.stat().st_size))
            self.send_header("Content-Type", "application/octet-stream"); self.end_headers()
            self._log(200, 0)
        elif p.is_dir():
            self.send_response(200); self.send_header("Content-Length", "0"); self.end_headers(); self._log(200, 0)
        else:
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); self._log(404, 0)
    def do_GET(self):
        p = Path(self.translate_path(self.path.split("?")[0]))
        if p.is_dir():           # directory listing (fsspec may ls)
            n = super().do_GET(); self._log(200, -1); return n
        if not p.is_file():
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); self._log(404, 0); return
        size = p.stat().st_size
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        status = 200
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                s, e = m.groups()
                if s == "" and e:      # suffix range
                    start = max(0, size - int(e))
                else:
                    start = int(s or 0); end = int(e) if e else size - 1
                end = min(end, size - 1)
                if start > end or start >= size:
                    self.send_response(416); self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0"); self.end_headers(); self._log(416, 0); return
                status = 206
        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        self._log(status, length)
        with p.open("rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                buf = f.read(min(1 << 20, remaining))
                if not buf: break
                self.wfile.write(buf); remaining -= len(buf)

if __name__ == "__main__":
    LOG.parent.mkdir(exist_ok=True)
    _logf = LOG.open("a")
    print(f"serving {SERVE} on http://localhost:{PORT}  log -> {LOG}", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
