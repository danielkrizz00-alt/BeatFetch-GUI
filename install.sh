#!/usr/bin/env bash
#
# install.sh — installs GNOME Fetch Panel for the current user.
#
# What it does:
#   1. Installs dependencies via the host distro's package manager
#   2. Copies the app to ~/.local/share/gnome-fetch-panel
#   3. Installs a `gnome-fetch-panel` launcher to ~/.local/bin
#   4. Installs a .desktop entry so it shows up in GNOME Activities
#
# Usage:
#   ./install.sh              # interactive
#   ./install.sh --yes        # non-interactive, assume yes to prompts
#   ./install.sh --uninstall  # remove everything this script installed
#
set -euo pipefail

APP_NAME="gnome-fetch-panel"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"
LAUNCHER="$BIN_DIR/$APP_NAME"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ASSUME_YES=false
UNINSTALL=false
for arg in "$@"; do
    case "$arg" in
        --yes|-y) ASSUME_YES=true ;;
        --uninstall) UNINSTALL=true ;;
        --help|-h)
            echo "Usage: $0 [--yes] [--uninstall]"
            exit 0
            ;;
    esac
done

info()  { echo -e "\033[1;36m==>\033[0m $*"; }
warn()  { echo -e "\033[1;33m!!\033[0m $*"; }
error() { echo -e "\033[1;31m✗\033[0m $*" >&2; }

confirm() {
    $ASSUME_YES && return 0
    read -r -p "$1 [Y/n] " reply
    [[ -z "$reply" || "$reply" =~ ^[Yy]$ ]]
}

detect_pkg_manager() {
    if command -v apt-get >/dev/null 2>&1; then echo "apt"; return 0; fi
    if command -v dnf >/dev/null 2>&1; then echo "dnf"; return 0; fi
    if command -v yum >/dev/null 2>&1; then echo "yum"; return 0; fi
    if command -v zypper >/dev/null 2>&1; then echo "zypper"; return 0; fi
    if command -v pacman >/dev/null 2>&1; then echo "pacman"; return 0; fi
    if command -v apk >/dev/null 2>&1; then echo "apk"; return 0; fi
    echo "none"
}

install_hyfetch() {
    local manager
    manager="$(detect_pkg_manager)"

    case "$manager" in
        apt)
            if ! command -v hyfetch >/dev/null 2>&1; then
                sudo apt-get update
                sudo DEBIAN_FRONTEND=noninteractive apt-get install -y hyfetch || true
            fi
            ;;
        dnf)
            sudo dnf install -y hyfetch || true
            ;;
        yum)
            sudo yum install -y hyfetch || true
            ;;
        zypper)
            sudo zypper --non-interactive install -y hyfetch || true
            ;;
        pacman)
            if command -v yay >/dev/null 2>&1; then
                yay -S --noconfirm hyfetch || true
            elif command -v paru >/dev/null 2>&1; then
                paru -S --noconfirm hyfetch || true
            else
                warn "hyfetch is not available from the package manager, so it will stay optional."
            fi
            ;;
        apk)
            sudo apk add --no-cache hyfetch || true
            ;;
        *)
            if command -v python3 >/dev/null 2>&1; then
                python3 -m pip install --user hyfetch || true
            fi
            ;;
    esac
}

install_dependencies() {
    local manager
    manager="$(detect_pkg_manager)"

    case "$manager" in
        apt)
            info "Installing dependencies with apt"
            sudo apt-get update
            sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
                python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 fastfetch playerctl cava
            ;;
        dnf)
            info "Installing dependencies with dnf"
            sudo dnf install -y \
                python3-gobject gtk4 libadwaita fastfetch playerctl cava
            ;;
        yum)
            info "Installing dependencies with yum"
            sudo yum install -y \
                python3-gobject gtk4 libadwaita fastfetch playerctl cava
            ;;
        zypper)
            info "Installing dependencies with zypper"
            sudo zypper --non-interactive install -y \
                python3-gobject gtk4 libadwaita fastfetch playerctl cava
            ;;
        pacman)
            info "Installing dependencies with pacman"
            sudo pacman -S --needed --noconfirm \
                python-gobject gtk4 libadwaita fastfetch playerctl cava
            ;;
        apk)
            info "Installing dependencies with apk"
            sudo apk add --no-cache \
                py3-gobject gtk4 libadwaita fastfetch playerctl cava
            ;;
        *)
            warn "No supported package manager was detected on this system."
            warn "Install these manually before running the app:"
            warn "  PyGObject / python3-gi, GTK4, libadwaita, fastfetch, playerctl, cava"
            warn "  Optional: hyfetch"
            return 1
            ;;
    esac
}

# ---------------------------------------------------------------------------
if $UNINSTALL; then
    info "Removing $INSTALL_DIR"
    rm -rf "$INSTALL_DIR"
    info "Removing $LAUNCHER"
    rm -f "$LAUNCHER"
    info "Removing $DESKTOP_FILE"
    rm -f "$DESKTOP_FILE"
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
    info "Uninstalled. (System packages like fastfetch/cava/playerctl were left alone.)"
    exit 0
fi

# ---------------------------------------------------------------------------
info "GNOME Fetch Panel installer"
if [[ ! -f "$SCRIPT_DIR/main.py" ]]; then
    error "Run this script from inside the gnome-fetch-panel directory (main.py not found next to install.sh)."
    exit 1
fi

manager="$(detect_pkg_manager)"
if [[ "$manager" == "none" ]]; then
    warn "No supported package manager was detected; this installer will skip dependency installation."
    if ! confirm "Continue with just the app files (skip package install)?"; then
        exit 1
    fi
    SKIP_DEPS=true
else
    SKIP_DEPS=false
fi

# --- 1. Dependencies ---------------------------------------------------
if ! $SKIP_DEPS; then
    info "Detected package manager: $manager"
    MISSING=()
    case "$manager" in
        apt)
            for pkg in python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 fastfetch playerctl cava; do
                dpkg -s "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
            done
            ;;
        dnf|yum|zypper)
            for pkg in python3-gobject gtk4 libadwaita fastfetch playerctl cava; do
                rpm -q "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
            done
            ;;
        pacman)
            for pkg in python-gobject gtk4 libadwaita fastfetch playerctl cava; do
                pacman -Qi "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
            done
            ;;
        apk)
            for pkg in py3-gobject gtk4 libadwaita fastfetch playerctl cava; do
                apk info -e "$pkg" >/dev/null 2>&1 || MISSING+=("$pkg")
            done
            ;;
    esac

    if [[ ${#MISSING[@]} -gt 0 ]]; then
        info "Missing packages: ${MISSING[*]}"
        if confirm "Install them now with the system package manager?"; then
            install_dependencies
        else
            warn "Skipping dependency install. The app may not run correctly until these are installed."
        fi
    else
        info "All required dependencies are already installed."
    fi

    if ! command -v hyfetch >/dev/null 2>&1; then
        if confirm "hyfetch was not found. Install it as an optional enhancement?"; then
            install_hyfetch
        else
            warn "hyfetch remains optional; fastfetch is enough for the app to work."
        fi
    fi
fi

# --- 2. Copy app files ---------------------------------------------------
info "Installing app to $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR"/*.py "$SCRIPT_DIR"/style.css "$INSTALL_DIR/"

# --- 3. Launcher script ---------------------------------------------------
info "Installing launcher to $LAUNCHER"
mkdir -p "$BIN_DIR"
cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
exec python3 "$INSTALL_DIR/main.py" "\$@"
EOF
chmod +x "$LAUNCHER"

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR is not on your PATH."
    warn "Add this to ~/.bashrc or ~/.zshrc:"
    warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

# --- 4. Desktop entry ------------------------------------------------------
info "Installing desktop entry"
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=System Dashboard
Comment=fastfetch/hyfetch system info, media controls, and an audio visualizer
Exec=$LAUNCHER
Icon=computer-symbolic
Terminal=false
Categories=System;AudioVideo;
StartupWMClass=com.example.GnomeFetchPanel
EOF
update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

info "Done. Launch it from Activities as \"System Dashboard\", or run: $APP_NAME"
