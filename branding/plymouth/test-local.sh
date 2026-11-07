#!/usr/bin/env bash
# Prueba la pantalla de arranque de XappiensOS en este equipo, sin reiniciar.
#
# Uso (necesita sudo):  branding/plymouth/test-local.sh [segundos] [--password]
#
# Ejecútalo desde una consola de texto (Ctrl+Alt+F3, inicia sesión y lanza el
# script): Plymouth necesita la pantalla para él solo y no se ve encima de una
# sesión gráfica. Al terminar vuelve a dejar el tema que tenías.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/../../config/xappiens-os/includes.chroot/usr/share/plymouth/themes/xappiens"
THEMES=/usr/share/plymouth/themes
DEST="$THEMES/xappiens"
SECS=10
ASK_PASSWORD=0
for arg in "$@"; do
    case "$arg" in
        --password) ASK_PASSWORD=1 ;;
        ''|*[!0-9]*) echo "Argumento no válido: $arg" >&2; exit 2 ;;
        *) SECS="$arg" ;;
    esac
done

command -v plymouthd >/dev/null || { echo "plymouth no está instalado" >&2; exit 1; }
[ -f "$SRC/xappiens.plymouth" ] || { echo "No encuentro el tema en $SRC" >&2; exit 1; }

PREV="$(readlink -f "$THEMES/default.plymouth")"
PREV_AUTO=0
update-alternatives --query default.plymouth | grep -q '^Status: auto' && PREV_AUTO=1

restore() {
    sudo plymouth quit 2>/dev/null || true
    if [ "$PREV_AUTO" = 1 ]; then
        sudo update-alternatives --auto default.plymouth >/dev/null
    else
        sudo update-alternatives --set default.plymouth "$PREV" >/dev/null
    fi
    sudo update-alternatives --remove default.plymouth "$DEST/xappiens.plymouth" >/dev/null 2>&1 || true
    sudo rm -rf "$DEST"
    echo "Restaurado el tema anterior: $(readlink -f "$THEMES/default.plymouth")"
}

sudo mkdir -p "$DEST"
sudo cp "$SRC"/* "$DEST"/
# Prioridad baja: sólo se usa porque lo fijamos a mano durante la prueba.
sudo update-alternatives --install "$THEMES/default.plymouth" default.plymouth "$DEST/xappiens.plymouth" 10 >/dev/null
trap restore EXIT
sudo update-alternatives --set default.plymouth "$DEST/xappiens.plymouth" >/dev/null

sudo plymouthd
sudo plymouth show-splash
if [ "$ASK_PASSWORD" = 1 ]; then
    sleep 3
    sudo plymouth ask-for-password --prompt "Contraseña del disco (prueba, escribe cualquier cosa)" >/dev/null || true
fi
sleep "$SECS"
