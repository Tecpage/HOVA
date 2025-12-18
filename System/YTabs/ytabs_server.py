import http.server, socketserver, sys, os
from urllib.parse import unquote

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def end_headers(self):
        # No-cache, damit Änderungen sofort sichtbar sind
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def translate_path(self, path):
        # Normalisiere URL-Path
        path = path.split("?",1)[0].split("#",1)[0]
        path = unquote(path)
        return super().translate_path(path)

def main():
    if len(sys.argv) < 3:
        print("usage: ytabs_server.py <port> <webdir>")
        sys.exit(2)
    port = int(sys.argv[1])
    webdir = sys.argv[2]
    if not os.path.isdir(webdir):
        print("webdir missing:", webdir)
        sys.exit(2)

    with socketserver.TCPServer(("127.0.0.1", port), lambda *a, **k: Handler(*a, directory=webdir, **k)) as httpd:
        httpd.allow_reuse_address = True
        print(f"YTabs listening on http://127.0.0.1:{port}/")
        httpd.serve_forever()

if __name__ == "__main__":
    main()
