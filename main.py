#!/usr/bin/env python3
"""
GNOME Fetch Panel
==================
A native GTK4 + libadwaita reimagining of the tmux "fastfetch + now
playing + cava visualizer" dashboard: same three-pane idea, but as a
real, resizable GNOME app with actual media transport controls
instead of a read-only text block, and a switcher to pick fastfetch
or hyfetch as the system-info backend.

Run:
    python3 main.py

Dependencies (see README.md for install commands):
    - python3-gi, gtk4, libadwaita  (the GUI toolkit)
    - fastfetch and/or hyfetch      (system info — pick one or both)
    - playerctl                     (media controls, e.g. for Spotify)
    - cava                          (live audio visualizer)
"""
import os
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from system_info import SystemInfoPanel, available_backends, BACKENDS
from now_playing import NowPlayingPanel
from visualizer import VisualizerPanel

APP_ID = "com.example.GnomeFetchPanel"


class FetchWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="System Dashboard")
        self.set_default_size(1100, 480)
        self.add_css_class("fetch-window")

        toolbar_view = Adw.ToolbarView()
        self.set_content(toolbar_view)

        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)

        # --- backend switcher (fastfetch / hyfetch) ---
        backends = list(BACKENDS.keys())
        present = set(available_backends())
        self.backend_model = Gtk.StringList.new(backends)
        self.backend_dropdown = Gtk.DropDown(model=self.backend_model)
        self.backend_dropdown.set_tooltip_text("System info source")
        default_idx = 0
        for i, name in enumerate(backends):
            if name in present:
                default_idx = i
                break
        self.backend_dropdown.set_selected(default_idx)
        self.backend_dropdown.connect("notify::selected", self._on_backend_changed)
        header.pack_start(self.backend_dropdown)

        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh system info")
        refresh_btn.connect("clicked", lambda *_: self.system_panel.refresh())
        header.pack_start(refresh_btn)

        # --- three-pane layout, matching the original tmux grid ---
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)
        toolbar_view.set_content(outer)

        self.system_panel = SystemInfoPanel(backend=backends[default_idx])
        self.system_panel.set_hexpand(True)
        self.system_panel.set_vexpand(True)
        outer.append(self.system_panel)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        right.set_hexpand(True)
        right.set_vexpand(True)
        outer.append(right)

        self.now_playing = NowPlayingPanel()
        self.now_playing.set_vexpand(False)
        right.append(self.now_playing)

        self.visualizer = VisualizerPanel()
        self.visualizer.set_vexpand(True)
        right.append(self.visualizer)

        # give the two columns a natural ~55/45 split, resizable by the user
        outer.set_homogeneous(False)
        self.system_panel.set_size_request(500, -1)
        right.set_size_request(420, -1)

    def _on_backend_changed(self, dropdown, _pspec):
        idx = dropdown.get_selected()
        name = self.backend_model.get_string(idx)
        self.system_panel.set_backend(name)


class FetchApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        style_manager = Adw.StyleManager.get_default()
        style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

        css_path = GLib.build_filenamev([os.path.dirname(os.path.abspath(__file__)), "style.css"])
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(css_path)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        win = self.props.active_window or FetchWindow(self)
        win.present()


if __name__ == "__main__":
    import sys

    app = FetchApp()
    sys.exit(app.run(sys.argv))
