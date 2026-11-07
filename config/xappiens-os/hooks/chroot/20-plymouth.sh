#!/bin/bash
# XappiensOS: activa el tema de Plymouth (pantalla de arranque) "xappiens".
#
# Los ficheros del tema llegan por el overlay includes.chroot. Aquí sólo se
# selecciona como tema por defecto. El initramfs se regenera más adelante, en
# la etapa "live" (dracut --regenerate-all en mk/chroot.mk), y el instalador
# lo vuelve a generar en el sistema instalado.
set -euo pipefail

THEMES=/usr/share/plymouth/themes
THEME="$THEMES/xappiens/xappiens.plymouth"

if [ ! -f "$THEME" ]; then
    echo "ERROR: falta $THEME (¿se aplicó el overlay?)" >&2
    exit 1
fi

if ! command -v plymouthd >/dev/null 2>&1; then
    echo "AVISO: plymouth no está instalado; no se activa el tema." >&2
    exit 0
fi

# Ubuntu/Pop eligen el tema con la alternativa default.plymouth. La fijamos en
# modo manual para que una actualización del tema de Pop no la recupere.
update-alternatives --install "$THEMES/default.plymouth" default.plymouth "$THEME" 300
update-alternatives --set default.plymouth "$THEME"

# Algunas herramientas (plymouth-populate-initrd, plymouth-set-default-theme)
# leen el tema de /etc/plymouth/plymouthd.conf: lo dejamos también ahí.
mkdir -p /etc/plymouth
CONF=/etc/plymouth/plymouthd.conf
if [ -f "$CONF" ] && grep -q '^[[:space:]]*Theme[[:space:]]*=' "$CONF"; then
    sed -i 's/^[[:space:]]*Theme[[:space:]]*=.*/Theme=xappiens/' "$CONF"
elif [ -f "$CONF" ] && grep -q '^\[Daemon\]' "$CONF"; then
    sed -i '/^\[Daemon\]/a Theme=xappiens' "$CONF"
else
    printf '[Daemon]\nTheme=xappiens\n' >> "$CONF"
fi

echo "Tema de Plymouth: $(readlink -f "$THEMES/default.plymouth")"
