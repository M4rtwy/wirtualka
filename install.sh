#!/bin/sh
# Instalator wirtualki. Nie potrzebuje roota.
set -e

DEST="${XDG_DATA_HOME:-$HOME/.local/share}/wirtualka-app"
BIN="$HOME/.local/bin"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"

command -v python3 >/dev/null || { echo "brakuje python3"; exit 1; }
command -v qemu-system-x86_64 >/dev/null || echo "uwaga: brakuje qemu - doinstaluj qemu-desktop"

mkdir -p "$DEST" "$BIN" "$APPS" "$ICONS"
rm -rf "$DEST/wirtualka"
cp -r wirtualka "$DEST/wirtualka"

printf '#!/bin/sh\ncd "%s" || exit 1\nexec python3 -m wirtualka "$@"\n' "$DEST" > "$BIN/wirtualka"
chmod +x "$BIN/wirtualka"

cp data/icons/wirtualka.svg "$ICONS/dev.m4rtwy.wirtualka.svg"
cat > "$APPS/dev.m4rtwy.wirtualka.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=Maszyny wirtualne
GenericName=Menedzer maszyn wirtualnych
Comment=Proste maszyny wirtualne na QEMU/KVM, po polsku
Exec=$BIN/wirtualka --gui
Icon=dev.m4rtwy.wirtualka
Terminal=false
Categories=System;Emulator;
Keywords=maszyna;wirtualna;vm;qemu;kvm;
StartupNotify=true
StartupWMClass=dev.m4rtwy.wirtualka
DESKTOP

if [ -d "$HOME/.config/fish" ]; then
    mkdir -p "$HOME/.config/fish/completions"
    [ -f completions/wirtualka.fish ] && cp completions/wirtualka.fish "$HOME/.config/fish/completions/wirtualka.fish"
fi

update-desktop-database "$APPS" 2>/dev/null || true

echo "gotowe."
case ":$PATH:" in
    *":$BIN:"*) echo "sprobuj: wirtualka --help" ;;
    *) echo "dodaj $BIN do PATH, potem: wirtualka --help" ;;
esac
