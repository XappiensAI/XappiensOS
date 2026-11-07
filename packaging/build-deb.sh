#!/usr/bin/env bash
# Construye el paquete xappiens-default-settings (_all.deb), que convierte un
# Pop!_OS ya instalado en XappiensOS sin reinstalar:
#
#   packaging/build-deb.sh            -> build/packages/xappiens-default-settings_<versión>_all.deb
#   sudo apt install ./build/packages/xappiens-default-settings_*_all.deb
#
# Su contenido es el mismo overlay que usa la ISO (config/xappiens-os/
# includes.chroot), así que un sistema convertido y uno instalado desde la ISO
# quedan igual. No necesita sudo.
#
# Variables opcionales: DISTRO_NAME, DISTRO_VERSION, UBUNTU_CODE, VERSION, OUT.
set -euo pipefail
umask 022

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PKG=xappiens-default-settings
SRC="$REPO/packaging/$PKG"
OVERLAY="$REPO/config/xappiens-os/includes.chroot"

DISTRO_NAME="${DISTRO_NAME:-XappiensOS}"
DISTRO_VERSION="${DISTRO_VERSION:-26.04}"
UBUNTU_CODE="${UBUNTU_CODE:-resolute}"
if [ -z "${VERSION:-}" ]; then
    count="$(git -C "$REPO" rev-list --count HEAD)"
    hash="$(git -C "$REPO" rev-parse --short HEAD)"
    VERSION="$DISTRO_VERSION.0+git$count.$hash"
    git -C "$REPO" diff --quiet HEAD -- config packaging || VERSION="$VERSION.dirty"
fi
OUT="${OUT:-$REPO/build/packages}"
MAINTAINER="$(git -C "$REPO" config user.name) <$(git -C "$REPO" config user.email)>"

command -v dpkg-deb >/dev/null || { echo "Falta dpkg-deb" >&2; exit 1; }

# Se prepara fuera del repositorio: puede estar en NTFS, sin permisos POSIX.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
ROOT="$STAGE/root"
mkdir -p "$ROOT/DEBIAN"

rsync -rlt --chmod=D755,F644 "$OVERLAY/" "$ROOT/"
chmod 0755 "$ROOT"/usr/lib/xappiens/*

DOC="$ROOT/usr/share/doc/$PKG"
mkdir -p "$DOC"
cat > "$DOC/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: XappiensOS
Source: https://github.com/XappiensAI/XappiensOS

Files: *
Copyright: 2026 XappiensAI y colaboradores de XappiensOS
License: GPL-3.0
 En sistemas Debian el texto completo de la licencia está en
 /usr/share/common-licenses/GPL-3.

Files: usr/share/plymouth/themes/xappiens/*
Copyright: 2026 XappiensAI
Comment: Logotipo de Xappiens (bombilla y tipografía pixelada). Generado por
 branding/plymouth/make-theme.py en el repositorio de XappiensOS.
License: GPL-3.0
EOF

subst() {
    sed -e "s|@DISTRO_NAME@|$DISTRO_NAME|g" \
        -e "s|@DISTRO_VERSION@|$DISTRO_VERSION|g" \
        -e "s|@UBUNTU_CODE@|$UBUNTU_CODE|g" "$1"
}
for script in preinst postinst prerm postrm; do
    subst "$SRC/$script" > "$ROOT/DEBIAN/$script"
    chmod 0755 "$ROOT/DEBIAN/$script"
done

# Todo lo que va en /etc es conffile (APT respeta los cambios del usuario).
( cd "$ROOT" && find etc -type f | sort | sed 's|^|/|' ) > "$ROOT/DEBIAN/conffiles"

SIZE="$(du -sk --exclude=DEBIAN "$ROOT" | cut -f1)"
cat > "$ROOT/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Architecture: all
Maintainer: $MAINTAINER
Installed-Size: $SIZE
Depends: pop-default-settings, plymouth, initramfs-tools | dracut
Section: misc
Priority: optional
Homepage: https://github.com/XappiensAI/XappiensOS
Description: identidad y ajustes por defecto de $DISTRO_NAME
 Convierte un Pop!_OS $DISTRO_VERSION instalado en $DISTRO_NAME sin reinstalar:
 nombre y versión del sistema (os-release, lsb-release, issue) y pantalla de
 arranque propia (tema de Plymouth "xappiens").
 .
 Al desinstalarlo, el sistema vuelve a identificarse como Pop!_OS.
EOF

mkdir -p "$OUT"
DEB="$OUT/${PKG}_${VERSION}_all.deb"
dpkg-deb --root-owner-group -Zxz --build "$ROOT" "$DEB" >/dev/null
echo "$DEB"
