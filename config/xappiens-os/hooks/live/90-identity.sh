#!/bin/bash
# XappiensOS: la imagen de la ISO lleva la identidad de Pop!_OS en os-release.
#
# El motor del instalador (distinst) lee /etc/os-release de la imagen que
# instala y sólo admite NAME="Pop!_OS" (elige con él cargador de arranque,
# controladores y partición de recuperación). Así que, como último paso antes
# de crear el squashfs, los enlaces vuelven a /etc/pop-os/. Nuestra identidad
# sigue en /etc/xappiens/ y se aplica:
#   - al arrancar, con xappiens-identity.service (sesión live e instalado);
#   - durante la instalación, con el hook de APT 99xappiens-branding, cuando
#     distinst ejecuta apt en el sistema de destino.
# Debe ser el último hook live: cualquier apt posterior volvería a cambiarla.
set -euo pipefail

/usr/lib/xappiens/apply-branding --revert
echo "Identidad de la imagen (para distinst): $(. /etc/os-release; echo "$NAME $VERSION_ID")"
test -f /etc/xappiens/os-release
systemctl is-enabled xappiens-identity.service
