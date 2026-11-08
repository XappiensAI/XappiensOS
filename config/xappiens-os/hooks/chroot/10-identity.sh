#!/bin/bash
# XappiensOS: genera la identidad del sistema (/etc/xappiens/*) y la activa.
# La lógica vive en /usr/lib/xappiens/ (overlay), compartida con el paquete
# xappiens-default-settings.
set -euo pipefail

chmod 0755 /usr/lib/xappiens/write-identity /usr/lib/xappiens/apply-branding

DISTRO_NAME="${DISTRO_NAME:-}" DISTRO_VERSION="${DISTRO_VERSION:-}" \
UBUNTU_CODE="${UBUNTU_CODE:-}" /usr/lib/xappiens/write-identity
/usr/lib/xappiens/apply-branding
# También al arrancar: la imagen de la ISO vuelve a la identidad de Pop!_OS
# para el instalador (ver hooks/live/90-identity.sh).
systemctl enable xappiens-identity.service

echo "Identidad del sistema:"
cat /etc/os-release
