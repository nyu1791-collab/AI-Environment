#!/usr/bin/env bash
# Install productivity tools on a fresh Debian/Ubuntu VM. Safe to re-run.
# Installs public packages only. Does NOT log in to any service.
set -euo pipefail
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo -n"

$SUDO apt-get update -qq
$SUDO DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  git gh jq ripgrep fd-find tmux ffmpeg rsync unzip zip \
  python3-venv python3-pip nodejs npm

# fd is packaged as fdfind on Debian; expose it as fd.
mkdir -p "$HOME/.local/bin"
[ -e "$HOME/.local/bin/fd" ] || ln -s "$(command -v fdfind)" "$HOME/.local/bin/fd"

# uv: fast Python package and tool manager (official installer, no login).
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "installed:"
for t in git gh jq rg fd tmux ffmpeg node npm python3; do
  printf "  %-7s %s\n" "$t" "$(command -v "$t" >/dev/null && echo ok || echo MISSING)"
done
