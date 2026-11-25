"""Local editor and font exporter. python server.py [--port 8731] [--open]"""
import argparse
from functools import lru_cache
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import urlsplit
from urllib.request import urlopen
import webbrowser

from a.export_font import export_font
from optical import build_font, validated_points

ROOT = Path(__file__).resolve().parent
FONT = ROOT / 'font' / 'lab.ttf'
MICRO = Path.home() / 'Library/Fonts/microtechnicextendedrusby_bold.otf'
BUILD_LOCK = threading.Lock()


@lru_cache(maxsize=8)
def built(points, shape, font_mtime_ns):
    return build_font(FONT, points, dict(shape))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def binary(self, data, mime):
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/reference/micro':
            if MICRO.is_file():
                self.binary(MICRO.read_bytes(), 'font/otf')
            else:
                self.send_error(404)
        elif path == '/api/identity':
            self.binary(b'sp-type-lab-v1', 'text/plain')
        else:
            super().do_GET()

    def do_POST(self):
        if self.path not in ('/api/font', '/api/a-font'):
            return self.send_error(404)
        origin = self.headers.get('Origin')
        if origin and urlsplit(origin).netloc != self.headers.get('Host'):
            return self.send_error(403)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError('Некорректный размер профиля.')
            req = json.loads(self.rfile.read(size))
            if self.path == '/api/a-font':
                with BUILD_LOCK:
                    data = export_font(req['height'], req['thickness'])
                return self.binary(data, 'font/ttf')
            points = tuple(validated_points(req['points']))
            shape = tuple(sorted(req.get('shape', {}).items()))
            with BUILD_LOCK:
                data = built(points, shape, FONT.stat().st_mtime_ns)
            self.binary(data, 'font/ttf')
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            self.send_error(400, str(exc).encode('ascii','backslashreplace').decode())
        except FileNotFoundError:
            self.send_error(503, 'Font master is missing')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8731)
    parser.add_argument('--open', action='store_true')
    args = parser.parse_args()
    url = f'http://127.0.0.1:{args.port}/'
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError:
        if args.open and urlopen(url + 'api/identity', timeout=2).read() == b'sp-type-lab-v1':
            webbrowser.open(url)
            raise SystemExit(0)
        raise
    print(url, flush=True)
    if args.open:
        webbrowser.open(url)
    server.serve_forever()
