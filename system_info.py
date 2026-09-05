"""System info panel: shells out to fastfetch or hyfetch and displays
the colored output natively via GTK + Pango markup."""
import shutil
import subprocess

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Pango

from ansi_pango import ansi_to_pango

BACKENDS = {
    "fastfetch": {
        "bin": "fastfetch",
        # --pipe keeps color codes but drops interactive/tty-only bits
        "args": ["--pipe"],
    },
    "hyfetch": {
        "bin": "hyfetch",
        # hyfetch wraps neofetch/fastfetch; -m preset avoids the
        # interactive first-run color-mode prompt.
        "args": ["-m", "rgb"],
    },
}


def available_backends():
    return [name for name, cfg in BACKENDS.items() if shutil.which(cfg["bin"])]


class SystemInfoPanel(Gtk.Box):
    __gtype_name__ = "SystemInfoPanel"

    def __init__(self, backend: str = "fastfetch"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add_css_class("fetch-card")
        self.add_css_class("card-system")
        self.backend = backend

        header = Gtk.Box(spacing=6)
        icon = Gtk.Image.new_from_icon_name("computer-symbolic")
        title = Gtk.Label(label="system")
        title.add_css_class("card-title")
        header.append(icon)
        header.append(title)
        header.set_halign(Gtk.Align.START)
        self.append(header)

        scroller = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.label = Gtk.Label(xalign=0, yalign=0)
        self.label.set_wrap(False)
        self.label.set_selectable(True)
        self.label.add_css_class("mono")
        scroller.set_child(self.label)
        self.append(scroller)

        self.refresh()
        GLib.timeout_add_seconds(1, self._refresh_tick)

    def _refresh_tick(self):
        self.refresh()
        return True

    def set_backend(self, backend: str):
        self.backend = backend
        self.refresh()

    def refresh(self):
        self.label.set_markup("<i>loading…</i>")
        GLib.Thread.new("fetch-run", self._run_async, None)

    def _run_async(self, _data):
        cfg = BACKENDS.get(self.backend, BACKENDS["fastfetch"])
        try:
            result = subprocess.run(
                [cfg["bin"], *cfg["args"]],
                capture_output=True,
                text=True,
                timeout=10,
            )
            raw = result.stdout or result.stderr or "(no output)"
        except FileNotFoundError:
            raw = f"'{cfg['bin']}' not found on PATH.\nInstall it, or switch backend in the header menu."
        except Exception as e:  # noqa: BLE001
            raw = f"Error running {cfg['bin']}: {e}"

        markup = ansi_to_pango(raw)
        GLib.idle_add(self._apply_markup, markup)

    def _apply_markup(self, markup):
        try:
            self.label.set_markup(markup)
        except GLib.Error:
            # Fall back to plain text if fastfetch emitted something
            # Pango couldn't parse (rare, but be defensive).
            self.label.set_text(GLib.markup_escape_text(markup))
        return False
