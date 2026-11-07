#!/usr/bin/env bash
# XappiensOS: aplica el overlay de ficheros y ejecuta los hooks de una etapa.
#
# Uso: xappiens-hooks.sh <chroot|live> <directorio-chroot> <directorio-config>
#
# Se llama desde mk/chroot.mk con el chroot ya montado. Si la configuración de
# la distro no tiene overlay ni hooks (p. ej. pop-os), no hace nada.
set -euo pipefail

STAGE="$1"
ROOT="$2"
CONF="$3"

OVERLAY="$CONF/includes.$STAGE"
HOOKS="$CONF/hooks/$STAGE"

if [ -d "$OVERLAY" ]; then
    echo "==> [xappiens:$STAGE] overlay $OVERLAY"
    # Permisos normalizados (755 dirs / 644 ficheros): el repositorio puede
    # estar en un sistema de ficheros sin permisos POSIX (NTFS, exFAT...).
    # Los hooks se encargan de marcar como ejecutable lo que lo necesite.
    sudo rsync -rlpt --chmod=D755,F644 "$OVERLAY/" "$ROOT/"
fi

if [ -d "$HOOKS" ]; then
    sudo rm -rf "$ROOT/iso/hooks"
    sudo mkdir -p "$ROOT/iso/hooks"
    sudo rsync -rt --chmod=D755,F755 "$HOOKS/" "$ROOT/iso/hooks/"

    for hook in $(cd "$ROOT/iso/hooks" && ls -1 -- *.sh 2>/dev/null | sort); do
        echo "==> [xappiens:$STAGE] hook $hook"
        sudo env -i \
            PATH=/usr/sbin:/usr/bin:/sbin:/bin \
            DISTRO_CODE="${DISTRO_CODE:-}" \
            DISTRO_NAME="${DISTRO_NAME:-}" \
            DISTRO_VERSION="${DISTRO_VERSION:-}" \
            UBUNTU_CODE="${UBUNTU_CODE:-}" \
            UBUNTU_NAME="${UBUNTU_NAME:-}" \
            chroot "$ROOT" /bin/bash -e "/iso/hooks/$hook"
    done

    sudo rm -rf "$ROOT/iso/hooks"
fi
