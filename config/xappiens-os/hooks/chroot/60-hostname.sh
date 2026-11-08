#!/bin/bash
# XappiensOS: el instalador de Pop!_OS pone "pop-os" como nombre del equipo;
# xappiens-hostname.service lo cambia por "xappiens-os" en el primer arranque
# del sistema instalado (ver /usr/lib/xappiens/default-hostname).
set -euo pipefail

chmod 0755 /usr/lib/xappiens/default-hostname
systemctl enable xappiens-hostname.service
