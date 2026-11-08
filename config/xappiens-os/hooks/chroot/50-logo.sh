#!/bin/bash
# XappiensOS: logo propio (distributor-logo-xappiens) y avatar por defecto en
# lugar de los de Pop!_OS. La lógica vive en /usr/lib/xappiens/set-logo,
# compartida con el paquete xappiens-default-settings.
set -euo pipefail

chmod 0755 /usr/lib/xappiens/set-logo
/usr/lib/xappiens/set-logo

echo "Logo: $(readlink -f /usr/share/icons/Pop/256x256/places/distributor-logo.svg 2>/dev/null || echo '(sin tema Pop)')"
echo "Avatar: $(readlink -f /usr/share/pixmaps/faces/pop-robot.png 2>/dev/null || echo '(sin avatar de Pop)')"
