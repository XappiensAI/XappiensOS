# XappiensOS 26.04 — basado en Pop!_OS 26.04 (Ubuntu 26.04 LTS "Resolute Raccoon")
#
# Heredamos toda la configuración de Pop!_OS y sólo sobrescribimos lo nuestro.
# Así, al fusionar cambios de upstream (pop-os/iso), recibimos sus arreglos
# sin tener que tocar este fichero.
include config/pop-os/26.04.mk

DISTRO_NAME=XappiensOS

# Las etiquetas de volumen se recalculan solas a partir de DISTRO_NAME
# (XappiensOS_26.04_amd64, ..._NVIDIA, ..._HP).

# Dependencias de las herramientas que añade el overlay de XappiensOS.
XAPPIENS_PKGS=python3-gi gir1.2-gtk-3.0 gir1.2-gtklayershell-0.1 wl-clipboard libwayland-client0 libxkbcommon0 xkb-data
POST_DISTRO_PKGS+=$(XAPPIENS_PKGS)

# La personalización (identidad del sistema, ajustes por defecto, etc.) se
# aplica mediante:
#   config/xappiens-os/includes.chroot/  -> ficheros copiados al sistema instalado
#   config/xappiens-os/hooks/chroot/*.sh -> scripts ejecutados dentro del chroot
#   config/xappiens-os/includes.live/    -> ficheros sólo para la sesión live
#   config/xappiens-os/hooks/live/*.sh   -> scripts sólo para la sesión live
