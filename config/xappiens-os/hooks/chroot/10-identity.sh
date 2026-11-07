#!/bin/bash
# XappiensOS: genera la identidad del sistema (/etc/xappiens/*) y la activa.
# La lógica vive en /usr/lib/xappiens/ (overlay), compartida con el paquete
# xappiens-default-settings.
set -euo pipefail

chmod 0755 /usr/lib/xappiens/write-identity /usr/lib/xappiens/apply-branding

DISTRO_NAME="${DISTRO_NAME:-}" DISTRO_VERSION="${DISTRO_VERSION:-}" \
UBUNTU_CODE="${UBUNTU_CODE:-}" /usr/lib/xappiens/write-identity
/usr/lib/xappiens/apply-branding

echo "Identidad del sistema:"
cat /etc/os-release
