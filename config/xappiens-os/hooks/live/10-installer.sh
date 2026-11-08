#!/bin/bash
# XappiensOS: marca propia en el instalador de la sesión live.
#
# xappiens-installer-branding (packaging/build-deb.sh) trae el estilo, las
# ilustraciones y el icono del instalador. Se instala aquí, en la etapa live,
# así que figura en filesystem.manifest-remove y el instalador lo purga del
# sistema instalado junto con pop-installer.
set -euo pipefail

shopt -s nullglob
debs=(/iso/packages/xappiens-installer-branding_*_all.deb)
if [ ${#debs[@]} -ne 1 ]; then
    echo "ERROR: falta xappiens-installer-branding en /iso/packages; construye con ./build.sh" >&2
    exit 1
fi

export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends "${debs[0]}"

grep -E '^(Name|Icon)=' /usr/share/applications/io.elementary.installer.desktop
ls -l /root/.config/gtk-3.0/gtk.css
