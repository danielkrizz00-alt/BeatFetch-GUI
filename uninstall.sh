#!/usr/bin/env bash
set -euo pipefail

APP_NAME="gnome-fetch-panel"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/$APP_NAME.desktop"
LAUNCHER="$BIN_DIR/$APP_NAME"

info()  { echo -e "\033[1;36m==>\033[0m $*"; }
warn()  { echo -e "\033[1;33m!!\033[0m $*"; }

info "Removing $APP_NAME installation"
rm -rf "$INSTALL_DIR"
rm -f "$LAUNCHER"
rm -f "$DESKTOP_FILE"
update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true

info "Removed $APP_NAME files and desktop entry."
warn "System packages like fastfetch, cava, and playerctl were left installed on purpose."
