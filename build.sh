#!/usr/bin/env bash
# XappiensOS — script de construcción
#
#   ./build.sh            construye la ISO (objetivo `iso`)
#   ./build.sh qemu       construye la ISO y la arranca en QEMU (UEFI)
#   ./build.sh all        ISO + zsync + SHA256SUMS firmados
#   ./build.sh clean      limpia la construcción
#
# Variables opcionales:
#   XAPPIENS_BUILD_ROOT  dónde construir (defecto: ~/xappiens-build). DEBE ser
#                        un sistema de ficheros Linux (ext4, btrfs, xfs...).
#   DISTRO_VERSION       versión a construir (defecto: 26.04)
#   NVIDIA=1             variante con drivers NVIDIA
#   GPG_NAME             clave GPG con la que firmar el pool de la ISO
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

DISTRO_CODE=xappiens-os
DISTRO_VERSION="${DISTRO_VERSION:-26.04}"
DISTRO_ARCH="$(dpkg --print-architecture)"
XAPPIENS_BUILD_ROOT="${XAPPIENS_BUILD_ROOT:-$HOME/xappiens-build}"
GPG_NAME="${GPG_NAME:-XappiensOS Build Key}"
POP_KEY=204DD8AEC33A7AFF

die() { echo "ERROR: $*" >&2; exit 1; }
info() { echo "==> $*"; }

# 1. Dependencias
missing=()
for cmd in debootstrap germinate mksquashfs xorriso zsync rsync qemu-system-x86_64; do
    command -v "$cmd" >/dev/null || missing+=("$cmd")
done
if [ ${#missing[@]} -gt 0 ]; then
    die "faltan herramientas: ${missing[*]}. Ejecuta ./deps.sh primero."
fi

# 2. El directorio de construcción debe estar en un sistema de ficheros Linux:
#    debootstrap/chroot necesitan permisos POSIX, propietarios, nodos de
#    dispositivo y enlaces duros que NTFS/exFAT/FAT no soportan.
mkdir -p "$XAPPIENS_BUILD_ROOT"
fstype="$(findmnt -n -o FSTYPE -T "$XAPPIENS_BUILD_ROOT")"
case "$fstype" in
    ext2|ext3|ext4|btrfs|xfs|f2fs|zfs|tmpfs) ;;
    *) die "$XAPPIENS_BUILD_ROOT está en '$fstype'. Usa XAPPIENS_BUILD_ROOT=/ruta/en/ext4" ;;
esac

# 3. Clave pública de los repositorios de Pop!_OS (la usa el chroot)
if ! gpg --list-keys "$POP_KEY" >/dev/null 2>&1; then
    info "Importando la clave de los repositorios de Pop!_OS ($POP_KEY)"
    gpg --keyserver keyserver.ubuntu.com --recv-keys "$POP_KEY"
fi

# 4. Clave de firma de la construcción (firma el repositorio APT del pool de la ISO)
if ! gpg --list-secret-keys "$GPG_NAME" >/dev/null 2>&1; then
    info "Creando clave GPG local de construcción: '$GPG_NAME'"
    gpg --batch --passphrase '' --quick-gen-key \
        "$GPG_NAME <build@xappiens-os.invalid>" rsa4096 sign never
fi

BUILD="$XAPPIENS_BUILD_ROOT/$DISTRO_VERSION/$DISTRO_ARCH"
info "XappiensOS $DISTRO_VERSION ($DISTRO_ARCH) -> $BUILD"

# 5. Paquetes propios (packaging/): los instalan los hooks del chroot.
if [ "${1:-iso}" != clean ]; then
    info "Construyendo los paquetes de XappiensOS"
    rm -rf "$BUILD/packages"
    OUT="$BUILD/packages" DISTRO_VERSION="$DISTRO_VERSION" bash packaging/build-deb.sh
    export XAPPIENS_PACKAGES="$BUILD/packages"
fi

exec make \
    DISTRO_CODE="$DISTRO_CODE" \
    DISTRO_VERSION="$DISTRO_VERSION" \
    BUILD="$BUILD" \
    GPG_NAME="$GPG_NAME" \
    "${@:-iso}"
