#!/usr/bin/env bash
# Construye los paquetes de XappiensOS (_all.deb) en build/packages/:
#
#   xappiens-default-settings   convierte un Pop!_OS ya instalado en XappiensOS
#                               sin reinstalar (mismo overlay que la ISO:
#                               config/xappiens-os/includes.chroot)
#   xappiens-bt-sco-fix-dkms    módulo bluetooth corregido (micrófono de
#                               auriculares mudo tras la primera llamada)
#   xappiens-installer-branding marca de XappiensOS en el instalador de la
#                               sesión live (sólo para la ISO)
#
#   packaging/build-deb.sh
#   sudo apt install ./build/packages/xappiens-default-settings_*.deb \
#                    ./build/packages/xappiens-bt-sco-fix-dkms_*.deb
#
# No necesita sudo. build.sh lo ejecuta antes de construir la ISO.
# Variables opcionales: DISTRO_NAME, DISTRO_VERSION, UBUNTU_CODE, VERSION, OUT.
set -euo pipefail
umask 022

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OVERLAY="$REPO/config/xappiens-os/includes.chroot"

DISTRO_NAME="${DISTRO_NAME:-XappiensOS}"
DISTRO_VERSION="${DISTRO_VERSION:-26.04}"
UBUNTU_CODE="${UBUNTU_CODE:-resolute}"
if [ -z "${VERSION:-}" ]; then
    if git -C "$REPO" rev-parse --git-dir >/dev/null 2>&1; then
        count="$(git -C "$REPO" rev-list --count HEAD)"
        hash="$(git -C "$REPO" rev-parse --short HEAD)"
        VERSION="$DISTRO_VERSION.0+git$count.$hash"
        [ -z "$(git -C "$REPO" status --porcelain -- config packaging)" ] || VERSION="$VERSION.dirty"
    else
        # Sin git (p. ej. desde un .tar): versión por fecha.
        VERSION="$DISTRO_VERSION.0+$(date -u +%Y%m%d%H%M)"
    fi
fi
OUT="${OUT:-$REPO/build/packages}"
# Sin identidad de git (CI, equipos nuevos) se usa la del proyecto.
git_name="$(git -C "$REPO" config user.name 2>/dev/null || true)"
git_email="$(git -C "$REPO" config user.email 2>/dev/null || true)"
if [ -n "$git_name" ] && [ -n "$git_email" ]; then
    MAINTAINER="${MAINTAINER:-$git_name <$git_email>}"
else
    MAINTAINER="${MAINTAINER:-XappiensOS <xappiensos@users.noreply.github.com>}"
fi

command -v dpkg-deb >/dev/null || { echo "Falta dpkg-deb" >&2; exit 1; }

# Se prepara fuera del repositorio: puede estar en NTFS, sin permisos POSIX.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$OUT"

subst() {
    # La expresión regular lleva \ y |: se escapa para sed.
    local kregex
    kregex="$(printf '%s' "${KERNEL_REGEX:-}" | sed 's/[\\#&]/\\&/g')"
    sed -e "s|@DISTRO_NAME@|$DISTRO_NAME|g" \
        -e "s|@DISTRO_VERSION@|$DISTRO_VERSION|g" \
        -e "s|@UBUNTU_CODE@|$UBUNTU_CODE|g" \
        -e "s|@VERSION@|$VERSION|g" \
        -e "s#@KERNEL_REGEX@#$kregex#g" "$1"
}

# Copia los scripts del mantenedor (preinst, postinst, prerm, postrm) que haya.
maintainer_scripts() {
    local src="$1" root="$2" script
    for script in preinst postinst prerm postrm; do
        [ -f "$src/$script" ] || continue
        subst "$src/$script" > "$root/DEBIAN/$script"
        chmod 0755 "$root/DEBIAN/$script"
    done
}

# control + conffiles + .deb
finish() {
    local pkg="$1" root="$2" depends="$3" summary="$4" description="$5"
    if [ -d "$root/etc" ]; then
        ( cd "$root" && find etc -type f | sort | sed 's|^|/|' ) > "$root/DEBIAN/conffiles"
    fi
    [ -s "$root/DEBIAN/conffiles" ] || rm -f "$root/DEBIAN/conffiles"
    cat > "$root/DEBIAN/control" <<EOF
Package: $pkg
Version: $VERSION
Architecture: all
Maintainer: $MAINTAINER
Installed-Size: $(du -sk --exclude=DEBIAN "$root" | cut -f1)
Depends: $depends
Section: misc
Priority: optional
Homepage: https://github.com/XappiensAI/XappiensOS
Description: $summary
$description
EOF
    local deb="$OUT/${pkg}_${VERSION}_all.deb"
    dpkg-deb --root-owner-group -Zxz --build "$root" "$deb" >/dev/null
    echo "$deb"
}

# --------------------------------------------------------------------------
# xappiens-default-settings
# --------------------------------------------------------------------------
PKG=xappiens-default-settings
ROOT="$STAGE/$PKG"
mkdir -p "$ROOT/DEBIAN"
rsync -rlt --chmod=D755,F644 --exclude='__pycache__/' --exclude='*.py[co]' "$OVERLAY/" "$ROOT/"
chmod 0755 "$ROOT"/usr/lib/xappiens/*
chmod 0755 "$ROOT/usr/lib/systemd/user-environment-generators/90-xappiens-desktop"

mkdir -p "$ROOT/usr/share/doc/$PKG"
cat > "$ROOT/usr/share/doc/$PKG/copyright" <<EOF
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

Files: usr/share/icons/hicolor/scalable/apps/distributor-logo-xappiens.svg
 usr/share/pixmaps/faces/xappiens.png
Copyright: 2026 XappiensAI
Comment: Logotipo de Xappiens. Generado por branding/installer/make-installer.py.
License: GPL-3.0
EOF

maintainer_scripts "$REPO/packaging/$PKG" "$ROOT"
finish "$PKG" "$ROOT" \
    "pop-default-settings, plymouth, initramfs-tools | dracut, python3-gi, gir1.2-gtk-3.0, gir1.2-gtklayershell-0.1, wl-clipboard, libwayland-client0, libxkbcommon0, xkb-data" \
    "identidad y ajustes por defecto de $DISTRO_NAME" \
" Convierte un Pop!_OS $DISTRO_VERSION instalado en $DISTRO_NAME sin reinstalar:
 nombre y versión del sistema (os-release, lsb-release, issue), pantalla de
 arranque propia (tema de Plymouth \"xappiens\"), logo de la distribución,
 ajustes de Bluetooth según
 el hardware, historial del portapapeles de sesión con Super+V y acciones
 personalizadas de teclado para pegar textos o ejecutar comandos en COSMIC.
 .
 Al desinstalarlo, el sistema vuelve a identificarse como Pop!_OS."

# --------------------------------------------------------------------------
# xappiens-installer-branding (sólo sesión live de la ISO)
# --------------------------------------------------------------------------
PKG=xappiens-installer-branding
SRC="$REPO/packaging/$PKG"
ROOT="$STAGE/$PKG"
mkdir -p "$ROOT/DEBIAN"
rsync -rlt --chmod=D755,F644 "$SRC/files/" "$ROOT/"

mkdir -p "$ROOT/usr/share/doc/$PKG"
cat > "$ROOT/usr/share/doc/$PKG/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: XappiensOS
Source: https://github.com/XappiensAI/XappiensOS

Files: *
Copyright: 2026 XappiensAI y colaboradores de XappiensOS
Comment: Ilustraciones e icono generados por branding/installer/make-installer.py
 a partir del logotipo de Xappiens.
License: GPL-3.0
 En sistemas Debian el texto completo de la licencia está en
 /usr/share/common-licenses/GPL-3.
EOF

maintainer_scripts "$SRC" "$ROOT"
finish "$PKG" "$ROOT" \
    "pop-installer" \
    "marca de $DISTRO_NAME para el instalador de la sesión live" \
" Estilo con la paleta de $DISTRO_NAME, ilustraciones pixel-art propias, icono
 y nombre (\"Instalar $DISTRO_NAME\") para el instalador de Pop!_OS
 (pop-installer) en la sesión live de la ISO.
 .
 Sólo tiene sentido en la sesión live: el instalador lo elimina del sistema
 instalado junto con pop-installer."

# --------------------------------------------------------------------------
# xappiens-bt-sco-fix-dkms
# --------------------------------------------------------------------------
PKG=xappiens-bt-sco-fix-dkms
SRC="$REPO/packaging/$PKG"
ROOT="$STAGE/$PKG"
DKMS_DIR="$ROOT/usr/src/xappiens-bt-sco-fix-$VERSION"
mkdir -p "$ROOT/DEBIAN" "$DKMS_DIR"

# Sólo se compila para las versiones del kernel cuya fuente va en el paquete.
versions="$(cd "$SRC/upstream" 2>/dev/null && ls -1d [0-9]*.[0-9]*.[0-9]* 2>/dev/null | sort -V || true)"
[ -n "$versions" ] || { echo "No hay fuentes en $SRC/upstream (usa fetch-source.sh)" >&2; exit 1; }
KERNEL_REGEX="^($(printf '%s\n' "$versions" | sed 's/\./\\./g' | paste -sd'|'))-"

rsync -rlt --chmod=D755,F644 "$SRC/upstream" "$SRC/patches" "$DKMS_DIR/"
install -m 0755 "$SRC/prepare.sh" "$DKMS_DIR/prepare.sh"
subst "$SRC/dkms.conf.in" > "$DKMS_DIR/dkms.conf"

mkdir -p "$ROOT/usr/share/doc/$PKG"
install -m 0644 "$SRC/README.md" "$ROOT/usr/share/doc/$PKG/README.md"
cat > "$ROOT/usr/share/doc/$PKG/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: xappiens-bt-sco-fix
Source: https://github.com/XappiensAI/XappiensOS

Files: *
Copyright: 2026 XappiensAI y colaboradores de XappiensOS
License: GPL-2.0-only

Files: usr/src/*/upstream/*
Copyright: Autores del kernel Linux
Comment: net/bluetooth sin cambios, de
 https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
 (ver upstream/<versión>/SOURCE).
License: GPL-2.0-only

Files: usr/src/*/patches/*
Copyright: Colaboradores de linux-bluetooth-headset-mic-fix
 (https://github.com/Mr-V1be/linux-bluetooth-headset-mic-fix)
License: GPL-2.0-only
 En sistemas Debian el texto completo de la licencia está en
 /usr/share/common-licenses/GPL-2.
EOF

maintainer_scripts "$SRC" "$ROOT"
finish "$PKG" "$ROOT" \
    "dkms, patch, initramfs-tools | dracut" \
    "corrige el micrófono Bluetooth que se queda mudo tras la primera llamada" \
" Módulo bluetooth del kernel (DKMS) con una corrección para una carrera en
 las conexiones SCO/eSCO: el micrófono de los auriculares funciona en la
 primera llamada y se queda mudo al volver a entrar en Meet, Discord, Zoom...
 .
 Sólo se compila para los kernels cuya fuente lleva el paquete
 ($(printf '%s\n' "$versions" | paste -sd' ')); con otro kernel se usa el módulo original."
