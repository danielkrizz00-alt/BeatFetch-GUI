"""Now Playing panel: controls any MPRIS-capable player (Spotify, etc.)
via playerctl. This replaces the read-only 'now playing' text block in
the terminal mockup with actual transport controls."""
import shutil
import subprocess

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

PLAYERCTL = shutil.which("playerctl")


def _pctl(*args, timeout=2):
    if not PLAYERCTL:
        return ""
    try:
        r = subprocess.run(["playerctl", *args], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


class NowPlayingPanel(Gtk.Box):
    __gtype_name__ = "NowPlayingPanel"

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add_css_class("fetch-card")
        self.add_css_class("card-nowplaying")
        self._seeking = False
        self._length_us = 0

        header = Gtk.Box(spacing=6)
        icon = Gtk.Image.new_from_icon_name("multimedia-player-symbolic")
        title = Gtk.Label(label="now playing")
        title.add_css_class("card-title")
        header.append(icon)
        header.append(title)
        header.set_halign(Gtk.Align.START)
        self.append(header)

        self.player_label = Gtk.Label(xalign=0)
        self.player_label.add_css_class("dim-label")
        self.append(self.player_label)

        self.track_label = Gtk.Label(xalign=0, wrap=True)
        self.track_label.add_css_class("track-title")
        self.append(self.track_label)

        self.artist_label = Gtk.Label(xalign=0)
        self.artist_label.add_css_class("track-artist")
        self.append(self.artist_label)

        self.scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        self.scale.set_range(0, 1)
        self.scale.set_draw_value(False)
        self.scale.set_sensitive(False)
        self.scale.set_can_focus(False)
        self.scale.set_hexpand(True)
        self.scale.add_css_class("progress-scale")
        self.append(self.scale)

        self.time_label = Gtk.Label(xalign=0)
        self.time_label.add_css_class("dim-label")
        self.time_label.add_css_class("caption")
        self.append(self.time_label)

        controls = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        self.prev_btn = self._icon_button("media-skip-backward-symbolic", self._on_prev)
        self.play_btn = self._icon_button("media-playback-start-symbolic", self._on_play_pause)
        self.next_btn = self._icon_button("media-skip-forward-symbolic", self._on_next)
        controls.append(self.prev_btn)
        controls.append(self.play_btn)
        controls.append(self.next_btn)
        self.append(controls)

        if not PLAYERCTL:
            warn = Gtk.Label(
                label="playerctl not found — install it to enable media controls.",
                wrap=True,
            )
            warn.add_css_class("dim-label")
            self.append(warn)

        self.refresh()
        GLib.timeout_add(1000, self._tick)

    def _icon_button(self, icon_name, handler):
        btn = Gtk.Button()
        btn.set_child(Gtk.Image.new_from_icon_name(icon_name))
        btn.add_css_class("circular")
        btn.add_css_class("flat")
        btn.connect("clicked", handler)
        return btn

    def _set_seeking(self, val):
        self._seeking = val

    def _on_seek_released(self, *_a):
        self._seeking = False
        if self._length_us:
            frac = self.scale.get_value()
            target_s = frac * (self._length_us / 1_000_000)
            _pctl("position", str(target_s))

    def _on_play_pause(self, *_a):
        _pctl("play-pause")
        GLib.timeout_add(150, lambda: (self.refresh(), False)[1])

    def _on_next(self, *_a):
        _pctl("next")
        GLib.timeout_add(300, lambda: (self.refresh(), False)[1])

    def _on_prev(self, *_a):
        _pctl("previous")
        GLib.timeout_add(300, lambda: (self.refresh(), False)[1])

    def _tick(self):
        self.refresh()
        return True

    @staticmethod
    def _fmt(us):
        s = int(us / 1_000_000)
        return f"{s // 60}:{s % 60:02d}"

    def refresh(self):
        if not PLAYERCTL:
            return
        status = _pctl("status")
        if not status:
            self.player_label.set_text("nothing playing")
            self.track_label.set_text("")
            self.artist_label.set_text("")
            self.time_label.set_text("")
            self.play_btn.set_child(Gtk.Image.new_from_icon_name("media-playback-start-symbolic"))
            return

        players = _pctl("--list-all").split("\n")
        player = players[0] if players and players[0] else "player"
        title = _pctl("metadata", "title") or _pctl("metadata", "xesam:title")
        artist = _pctl("metadata", "artist") or _pctl("metadata", "xesam:artist")
        length_str = _pctl("metadata", "mpris:length")
        pos_str = _pctl("position")

        self._length_us = int(length_str) if length_str.isdigit() else 0
        try:
            pos_s = float(pos_str) if pos_str else 0.0
        except ValueError:
            pos_s = 0.0
        pos_us = int(pos_s * 1_000_000)

        self.player_label.set_text(f"▶ {player or 'player'}")
        self.track_label.set_text(title or "—")
        self.artist_label.set_text(artist or "")

        if self._length_us:
            if not self._seeking:
                self.scale.set_value(pos_us / self._length_us)
            pct = int(100 * pos_us / self._length_us)
            self.time_label.set_text(
                f"{self._fmt(pos_us)} / {self._fmt(self._length_us)} ({pct}%) [{status}]"
            )
        else:
            self.time_label.set_text(status)

        icon = "media-playback-pause-symbolic" if status == "Playing" else "media-playback-start-symbolic"
        self.play_btn.set_child(Gtk.Image.new_from_icon_name(icon))
