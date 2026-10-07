"""Local configuration page shown by Galaxy when the integration is connected."""
import html
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import config

CSS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "website", "css", "main.css")

_REDIRECT = b'<script>window.location="/end";</script>'
_HEAD = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
)

_DONE_PAGE = _HEAD + """<style>{css}</style><title>Configuration saved</title></head><body><div class="backdrop"></div><main class="shell"><section class="success-card"><div class="success-icon">&#10003;</div><div class="eyebrow">NES INTEGRATION</div><h1>Configuration saved</h1><p>You can close this window and return to GOG Galaxy.</p></section></main></body></html>"""

_INDEX_PAGE = _HEAD + """<title>NES Integration · GOG Galaxy</title><style>{css}</style></head><body><div class="backdrop"></div><main class="shell">
<header class="topbar"><div class="brand"><div class="brand-mark">NES</div><div><div class="brand-title">NES Integration</div><div class="brand-subtitle">GOG Galaxy · Mesen</div></div></div><div class="pill"><span class="status-dot"></span>Local library</div></header>
<section class="hero-card"><div class="hero-art"><div class="pad"><div class="dpad"></div><span class="pad-pill sel"></span><span class="pad-pill sta"></span><span class="btn b"></span><span class="btn a"></span></div><div class="console-word">NES</div></div><div class="hero-copy"><div class="eyebrow">GALAXY PLUGIN</div><h1>Your NES library, one click away.</h1><p>Connect your ROM folder and the Mesen executable. Every NES and Famicom file Mesen can open is imported into GOG Galaxy and launched directly from your library.</p></div></section>
<form class="config-form" method="POST" action="/setconfig">
<section class="card"><div class="section-heading"><div><div class="eyebrow">01 · PATHS</div><h2>Library & emulator</h2></div><span class="section-badge">Required</span></div><div class="field-grid"><label class="field full"><span>Games location <em>Required</em></span><input name="romspath" value="{roms}" placeholder="Path to the game ROMs" required></label><label class="field full"><span>Mesen location <em>Required</em></span><input name="emupath" value="{emu}" placeholder="Path to the emulator executable" required></label></div><div class="hint"><span class="hint-icon">i</span><span>Supported files: .NES, .FDS, .QD, .UNF, .UNIF, .STUDYBOX, .NSF, .NSFE, .ZIP and .7Z. Subfolders are scanned automatically.</span></div></section>
<section class="card"><div class="section-heading"><div><div class="eyebrow">02 · DETECTION</div><h2>Automatic identification</h2></div><span class="section-badge accent">Automatic</span></div><div class="feature-row"><div class="feature-icon">ID</div><div><strong>Identified by the ROM itself</strong><small>Each game is recognised by its contents (CRC32), so renaming or moving a file never creates a duplicate or loses playtime. Games inside .ZIP files are recognised too.</small></div></div><div class="feature-row"><div class="feature-icon">◎</div><div><strong>Official names</strong><small>Names come from GOG's public game database and are remembered on this PC. Without a connection the file names are used.</small></div></div></section>
<section class="card"><div class="section-heading"><div><div class="eyebrow">03 · MESEN</div><h2>Launch options</h2></div><span class="section-badge">Optional</span></div><label class="toggle"><input type="checkbox" name="fullscreen" value="1" {fullscreen}><span class="toggle-track"></span><span><strong>Fullscreen</strong><small>Launch Mesen in fullscreen using its native command-line switch. Press F11 to exit fullscreen.</small></span></label></section>
<div class="actions"><div class="footer-note"><span class="status-dot"></span>Configuration is stored locally for this plugin.</div><button type="submit"><span>Save configuration</span><span class="button-arrow">→</span></button></div>
</form></main></body></html>"""


def _css():
    try:
        with open(CSS_FILE, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def _render(template, **values):
    # str.replace instead of str.format: the CSS and the page contain literal braces.
    page = template
    for key, value in dict(values, css=_css()).items():
        page = page.replace("{" + key + "}", value)
    return page


def save_form(params):
    """Store the submitted form; every other config.ini setting (launch_args, extensions...) is kept."""
    parser = config.load_config()
    parser["Paths"]["roms_path"] = config.clean_path(params.get("romspath", [""])[0])
    parser["Paths"]["emu_path"] = config.clean_path(params.get("emupath", [""])[0])
    parser["EmuSettings"]["emu_fullscreen"] = "True" if "fullscreen" in params else "False"
    config.save_config(parser)


class AuthenticationHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def _send(self, body, content_type="text/html; charset=utf-8", status=200):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/css/main.css":
            self._send(_css(), "text/css; charset=utf-8")
        elif url.path == "/setconfig":
            save_form(parse_qs(url.query))
            self._send(_REDIRECT)
        elif url.path == "/end":
            self._send(_render(_DONE_PAGE))
        elif url.path in ("", "/", "/index.html"):
            parser = config.load_config()
            self._send(_render(
                _INDEX_PAGE,
                roms=html.escape(parser.get("Paths", "roms_path", fallback="")),
                emu=html.escape(parser.get("Paths", "emu_path", fallback="")),
                fullscreen="checked" if parser.getboolean("EmuSettings", "emu_fullscreen", fallback=False) else "",
            ))
        else:
            self.send_error(404)

    def do_POST(self):
        if urlparse(self.path).path != "/setconfig":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(max(0, min(length, 64 * 1024)))
        save_form(parse_qs(raw.decode("utf-8", "replace")))
        self._send(_REDIRECT)


class AuthenticationServer(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.httpd = HTTPServer(("localhost", 0), AuthenticationHandler)
        self.port = self.httpd.server_port

    def run(self):
        self.httpd.serve_forever()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()
