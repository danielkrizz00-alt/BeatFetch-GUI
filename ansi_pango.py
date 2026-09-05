"""
Tiny ANSI SGR -> Pango markup converter.

fastfetch/hyfetch both colorize their output with standard ANSI escape
codes (including 256-color and truecolor sequences). GTK Labels can't
render ANSI directly, but they understand Pango markup, so we translate
one to the other here. Unsupported/unknown sequences are dropped rather
than leaking into the visible text.
"""
import re
from gi.repository import GLib

ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")

# Standard 16-color ANSI palette (approx. GNOME/Adwaita-friendly tones)
BASE16 = [
    "#1e1e1e", "#e06c75", "#98c379", "#e5c07b",
    "#61afef", "#c678dd", "#56b6c2", "#dcdcdc",
    "#5c6370", "#e06c75", "#98c379", "#e5c07b",
    "#61afef", "#c678dd", "#56b6c2", "#ffffff",
]


def _xterm256_to_hex(n: int) -> str:
    if n < 16:
        return BASE16[n]
    if n < 232:
        n -= 16
        r = (n // 36) % 6
        g = (n // 6) % 6
        b = n % 6
        scale = lambda v: 0 if v == 0 else 55 + v * 40
        return "#%02x%02x%02x" % (scale(r), scale(g), scale(b))
    gray = 8 + (n - 232) * 10
    return "#%02x%02x%02x" % (gray, gray, gray)


def ansi_to_pango(text: str) -> str:
    """Convert a string containing ANSI escape codes into Pango markup."""
    out = []
    open_spans = 0
    pos = 0
    fg = None
    bold = False

    def flush_span_open():
        attrs = []
        if fg:
            attrs.append(f'foreground="{fg}"')
        if bold:
            attrs.append('font_weight="bold"')
        if attrs:
            out.append(f"<span {' '.join(attrs)}>")
            return True
        return False

    for m in ANSI_RE.finditer(text):
        out.append(GLib.markup_escape_text(text[pos:m.start()]))
        pos = m.end()
        codes = [c for c in m.group(1).split(";") if c != ""] or ["0"]

        i = 0
        changed = False
        while i < len(codes):
            code = int(codes[i])
            if code == 0:
                fg, bold = None, False
                changed = True
            elif code == 1:
                bold = True
                changed = True
            elif 30 <= code <= 37:
                fg = BASE16[code - 30]
                changed = True
            elif 90 <= code <= 97:
                fg = BASE16[8 + (code - 90)]
                changed = True
            elif code == 38 and i + 1 < len(codes):
                if codes[i + 1] == "5" and i + 2 < len(codes):
                    fg = _xterm256_to_hex(int(codes[i + 2]))
                    i += 2
                elif codes[i + 1] == "2" and i + 4 < len(codes):
                    r, g, b = codes[i + 2:i + 5]
                    fg = f"#{int(r):02x}{int(g):02x}{int(b):02x}"
                    i += 4
                changed = True
            elif code == 39:
                fg = None
                changed = True
            i += 1

        if changed:
            if open_spans:
                out.append("</span>")
                open_spans -= 1
            if flush_span_open():
                open_spans += 1

    out.append(GLib.markup_escape_text(text[pos:]))
    out.append("</span>" * open_spans)
    return "".join(out)


def strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)
