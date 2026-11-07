#!/bin/bash
# XappiensOS: correcciones de Bluetooth.
#
#  - xappiens-bt-quirks.service: en cada arranque aplica los ajustes que
#    necesite el hardware (p. ej. perfil de llamadas para MediaTek MT7925).
#  - xappiens-bt-sco-fix-dkms: módulo bluetooth corregido (micrófono mudo tras
#    la primera llamada). El .deb lo construye build.sh (packaging/build-deb.sh)
#    y xappiens-hooks.sh lo deja en /iso/packages.
set -euo pipefail

chmod 0755 /usr/lib/xappiens/bt-quirks
systemctl enable xappiens-bt-quirks.service

shopt -s nullglob
debs=(/iso/packages/xappiens-bt-sco-fix-dkms_*_all.deb)
if [ ${#debs[@]} -ne 1 ]; then
    echo "ERROR: falta xappiens-bt-sco-fix-dkms en /iso/packages; construye con ./build.sh" >&2
    exit 1
fi

# El initramfs se regenera más adelante (etapa live) y en el sistema instalado.
# Secure Boot del equipo que construye no importa: Pop!_OS arranca sin él.
export DEBIAN_FRONTEND=noninteractive XAPPIENS_NO_INITRAMFS=1 XAPPIENS_IGNORE_SECURE_BOOT=1
apt-get install -y --no-install-recommends "${debs[0]}"
dkms status xappiens-bt-sco-fix

# Si el kernel de la ISO no tiene fuente en el paquete, DKMS no compila nada:
# mejor fallar que publicar una ISO sin el arreglo sin darse cuenta.
if ! dkms status xappiens-bt-sco-fix | grep -q ': installed'; then
    echo "ERROR: el módulo bluetooth corregido no se ha instalado para ningún kernel." >&2
    echo "  Kernels: $(ls /lib/modules | tr '\n' ' ')" >&2
    echo "  Añade su fuente: packaging/xappiens-bt-sco-fix-dkms/fetch-source.sh <versión>" >&2
    exit 1
fi
