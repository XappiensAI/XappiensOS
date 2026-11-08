#!/bin/bash
# El overlay se copia con permisos 0644; comparte la integración con el .deb.
set -euo pipefail
chmod 0755 /usr/lib/xappiens/clipboard-history /usr/lib/xappiens/configure-desktop
chmod 0755 /usr/lib/xappiens/paste-key
chmod 0755 /usr/lib/xappiens/shortcuts
chmod 0755 /usr/lib/systemd/user-environment-generators/90-xappiens-desktop
/usr/lib/xappiens/configure-desktop
