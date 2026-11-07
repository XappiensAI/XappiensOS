#!/bin/bash
# XappiensOS: activa el tema de Plymouth (pantalla de arranque) "xappiens".
#
# Los ficheros del tema llegan por el overlay includes.chroot; la lógica vive
# en /usr/lib/xappiens/set-plymouth-theme, compartida con el paquete
# xappiens-default-settings. El initramfs se regenera más adelante, en la
# etapa "live" (dracut --regenerate-all en mk/chroot.mk), y el instalador lo
# vuelve a generar en el sistema instalado.
set -euo pipefail

chmod 0755 /usr/lib/xappiens/set-plymouth-theme
/usr/lib/xappiens/set-plymouth-theme

echo "Tema de Plymouth: $(readlink -f /usr/share/plymouth/themes/default.plymouth)"
