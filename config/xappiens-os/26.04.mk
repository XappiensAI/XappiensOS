# XappiensOS 26.04 — basado en Pop!_OS 26.04 (Ubuntu 26.04 LTS "Resolute Raccoon")
#
# Heredamos toda la configuración de Pop!_OS y sólo sobrescribimos lo nuestro.
# Así, al fusionar cambios de upstream (pop-os/iso), recibimos sus arreglos
# sin tener que tocar este fichero.
include config/pop-os/26.04.mk

DISTRO_NAME=XappiensOS

# Las etiquetas de volumen se recalculan solas a partir de DISTRO_NAME
# (XappiensOS_26.04_amd64, ..._NVIDIA, ..._HP).

# Paquetes propios de XappiensOS que se instalarán tras los de Pop.
# (Vacío hasta que tengamos nuestro repositorio APT; ver docs/ROADMAP.md)
XAPPIENS_PKGS=
POST_DISTRO_PKGS+=$(XAPPIENS_PKGS)

# La personalización (identidad del sistema, ajustes por defecto, etc.) se
# aplica mediante:
#   config/xappiens-os/includes.chroot/  -> ficheros copiados al sistema instalado
#   config/xappiens-os/hooks/chroot/*.sh -> scripts ejecutados dentro del chroot
#   config/xappiens-os/includes.live/    -> ficheros sólo para la sesión live
#   config/xappiens-os/hooks/live/*.sh   -> scripts sólo para la sesión live
