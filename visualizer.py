"""Visualizer panel: launches `cava` in raw ASCII output mode and draws
the bars with Cairo, so it reacts to whatever is actually playing on
the system's audio output (matches the terminal cava-in-tmux look)."""
import os
import shutil
import subprocess
import tempfile
import threading

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk

CAVA = shutil.which("cava")
BARS = 48
MAX_HEIGHT = 100  # cava ascii_max_range

CAVA_CONFIG = f"""
[general]
bars = {BARS}
framerate = 60

[input]
method = pulse
source = auto

[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = {MAX_HEIGHT}
bar_delimiter = 59
frame_delimiter = 10
"""


class VisualizerPanel(Gtk.Box):
    __gtype_name__ = "VisualizerPanel"

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add_css_class("fetch-card")
        self.add_css_class("card-visualizer")

        header = Gtk.Box(spacing=6)
        icon = Gtk.Image.new_from_icon_name("audio-speakers-symbolic")
        title = Gtk.Label(label="visualizer")
        title.add_css_class("card-title")
        header.append(icon)
        header.append(title)
        header.set_halign(Gtk.Align.START)
        self.append(header)

        self.bars = [0] * BARS
        self.area = Gtk.DrawingArea(vexpand=True, hexpand=True)
        self.area.set_draw_func(self._draw)
        self.append(self.area)

        self._proc = None
        self._config_path = None
        self._stop = False

        if CAVA:
            self._start_cava()
        else:
            warn = Gtk.Label(
                label="cava not found — install it for a live audio visualizer.",
                wrap=True,
            )
            warn.add_css_class("dim-label")
            self.append(warn)

        self.connect("destroy", self._on_destroy)

    def _start_cava(self):
        fd, path = tempfile.mkstemp(suffix=".cava.conf")
        with os.fdopen(fd, "w") as f:
            f.write(CAVA_CONFIG)
        self._config_path = path
        self._proc = subprocess.Popen(
            ["cava", "-p", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        threading.Thread(target=self._read_loop, daemon=True).start()

    def _read_loop(self):
        buf = b""
        while not self._stop and self._proc and self._proc.poll() is None:
            chunk = self._proc.stdout.read(1024)
            if not chunk:
                break
            buf += chunk
            while b"\n" in buf:
                line, buf = buf.split(b"\n", 1)
                if not line:
                    continue
                try:
                    vals = [int(v) for v in line.decode().strip(";").split(";") if v]
                except ValueError:
                    continue
                if len(vals) == BARS:
                    GLib.idle_add(self._set_bars, vals)

    def _set_bars(self, vals):
        self.bars = vals
        self.area.queue_draw()
        return False

    def _draw(self, _area, cr, width, height, *_):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()

        n = len(self.bars) or 1
        gap = 2
        bar_w = max(1, (width - gap * (n - 1)) / n)

        for i, v in enumerate(self.bars):
            frac = min(1.0, v / MAX_HEIGHT)
            bar_h = frac * height
            x = i * (bar_w + gap)
            y = height - bar_h

            # green -> yellow -> orange -> red gradient by height, matching
            # the terminal visualizer's color ramp
            if frac < 0.35:
                r, g, b = 0.30, 0.75, 0.25
            elif frac < 0.6:
                r, g, b = 0.75, 0.75, 0.15
            elif frac < 0.85:
                r, g, b = 0.90, 0.55, 0.10
            else:
                r, g, b = 0.90, 0.20, 0.15

            cr.set_source_rgb(r, g, b)
            cr.rectangle(x, y, bar_w, bar_h)
            cr.fill()

    def _on_destroy(self, *_a):
        self._stop = True
        if self._proc:
            self._proc.terminate()
        if self._config_path and os.path.exists(self._config_path):
            try:
                os.remove(self._config_path)
            except OSError:
                pass
