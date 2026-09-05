# BeatFetch GUI (STILL IN BETA)

A native GTK4 + libadwaita GUI version of the tmux dashboard in the
screenshot: a system-info card, a **now playing** card with real
media transport controls, and a live **cava** audio visualizer —
all in one resizable GNOME window, dark-themed to match.

Differences from the terminal version, by design:

- **GUI, not ASCII.** The right-hand panel is now interactive: play /
  pause / next / previous buttons and a seekable progress bar,
  driven by `playerctl` (MPRIS), so it controls whatever's actually
  playing (Spotify, YouTube Music, browser tabs, etc.), not just
  displays it.
- **fastfetch or hyfetch, your choice.** A dropdown in the header bar
  switches the system-info backend live — no config file editing.
- **GNOME-native styling.** Built on libadwaita so it inherits your
  system's accent color, follows dark/light mode, has a proper
  header bar, and is resizable/tileable like any other GNOME app,
  while keeping the neon-card look via `style.css`.

## Install dependencies (Arch Linux)

The easiest path is the included installer, which handles all of this:

```bash
cd gnome-fetch-panel
chmod +x install.sh
./install.sh
```

It will:
1. Install missing pacman packages (`python-gobject`, `gtk4`, `libadwaita`, `fastfetch`, `playerctl`, `cava`), asking before each `sudo pacman -S`.
2. Offer to install `hyfetch` from the AUR if you have `yay` or `paru`.
3. Copy the app to `~/.local/share/gnome-fetch-panel`.
4. Install a `gnome-fetch-panel` command to `~/.local/bin`.
5. Register a **System Dashboard** entry in GNOME Activities.

Flags: `./install.sh --yes` skips confirmation prompts; `./install.sh --uninstall` removes everything the installer created (app files, launcher, desktop entry — system packages are left alone).

Prefer to do it by hand instead? The same packages, manually:

```bash
# GUI toolkit
sudo pacman -S python-gobject gtk4 libadwaita

# system info — install one or both, the app lets you pick
sudo pacman -S fastfetch
yay -S hyfetch          # AUR

# media controls (MPRIS client)
sudo pacman -S playerctl

# audio visualizer
sudo pacman -S cava
```

`cava`'s default config here uses `method = pulse` with `source =
auto`, which works out of the box on PipeWire-Arch setups (PipeWire
ships a PulseAudio-compatible socket). If your visualizer stays
flat, run `cava` once by hand to let it pick a working input.

## Run

After `install.sh`:

```bash
gnome-fetch-panel
```

(or launch **System Dashboard** from Activities). Without the installer:

```bash
cd gnome-fetch-panel
python3 main.py
```

## Uninstall

```bash
./install.sh --uninstall
```

## Install as a launchable app manually (if you skipped install.sh)

```bash
sudo mkdir -p /opt/gnome-fetch-panel
sudo cp *.py style.css /opt/gnome-fetch-panel/
cat > ~/.local/share/applications/gnome-fetch-panel.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=System Dashboard
Comment=fastfetch/hyfetch system info, media controls, and an audio visualizer
Exec=python3 /opt/gnome-fetch-panel/main.py
Icon=computer-symbolic
Terminal=false
Categories=System;AudioVideo;
EOF
update-desktop-database ~/.local/share/applications/
```

It'll then show up in the GNOME Activities overview as **System
Dashboard**.

## File layout

| File               | Purpose                                                   |
|--------------------|------------------------------------------------------------|
| `install.sh`       | Installer: deps via pacman/AUR, copies app, adds launcher + desktop entry |
| `main.py`          | Adwaita window, header bar, layout, backend switcher      |
| `system_info.py`   | Runs `fastfetch`/`hyfetch`, backend registry & switching   |
| `ansi_pango.py`     | Converts the tools' ANSI color codes to Pango markup       |
| `now_playing.py`   | MPRIS transport controls + metadata via `playerctl`        |
| `visualizer.py`    | Launches `cava` in raw mode, draws bars with Cairo          |
| `style.css`        | Neon-card theming layered on top of the Adwaita dark theme |

## Notes / things you may want to tweak

- **Backend list**: add more fetch tools by extending the `BACKENDS`
  dict in `system_info.py` — any tool that prints ANSI-colored
  `Key: Value` lines will render reasonably.
- **Player selection**: `now_playing.py` currently follows whichever
  player `playerctl` reports first. If you run multiple players
  at once and want to pin it to Spotify specifically, change the
  `_pctl(...)` calls to pass `-p spotify`.
- **Visualizer style**: bar count, color thresholds, and frame rate
  are constants at the top of `visualizer.py` / in `CAVA_CONFIG`.
