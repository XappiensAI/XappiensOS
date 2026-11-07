#!/usr/bin/env bash
# Añade la fuente de net/bluetooth para una versión del kernel. El paquete DKMS
# sólo compila para las versiones que tengan su fuente aquí: así nunca se
# instala un Bluetooth de otra versión del kernel (le faltarían sus
# correcciones de seguridad).
#
# La fuente sale del kernel que distribuye System76 (github.com/pop-os/linux),
# no de kernel.org, para no perder ningún cambio propio de Pop!_OS en
# net/bluetooth.
#
# Uso:  packaging/xappiens-bt-sco-fix-dkms/fetch-source.sh 7.2.16
#       POP_KERNEL_BRANCH=master_resolute (por defecto) — rama de pop-os/linux
#       LINUX_SRC=/ruta/a/un/checkout  — usar uno ya descargado
#
# Después, reconstruye el paquete: packaging/build-deb.sh
set -euo pipefail

VER="${1:?indica la versión del kernel, p. ej. 7.2.16}"
[[ $VER =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Versión no válida: $VER" >&2; exit 2; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HERE/upstream/$VER"
URL=https://github.com/pop-os/linux.git
BRANCH="${POP_KERNEL_BRANCH:-master_resolute}"

TMP=""
if [ -n "${LINUX_SRC:-}" ]; then
    SRC="$LINUX_SRC"
    ORIGIN="$(git -C "$SRC" remote get-url origin 2>/dev/null || echo "$SRC")"
else
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    SRC="$TMP/linux"
    ORIGIN="$URL ($BRANCH)"
    git clone --quiet --depth 1 --filter=blob:none --sparse --branch "$BRANCH" "$URL" "$SRC"
    git -C "$SRC" sparse-checkout set net/bluetooth include/net/bluetooth
fi

# La rama tiene que estar exactamente en la versión pedida.
have="$(awk -F' = ' '/^VERSION =/{v=$2} /^PATCHLEVEL =/{p=$2} /^SUBLEVEL =/{s=$2} END{print v"."p"."s}' "$SRC/Makefile")"
if [ "$have" != "$VER" ]; then
    echo "$ORIGIN está en el kernel $have, no en $VER" >&2
    exit 1
fi

rm -rf "$DEST"
mkdir -p "$DEST/net"
cp -a "$SRC/net/bluetooth" "$DEST/net/bluetooth"

# Huella de hci_conn_drop() en las cabeceras de esta versión: el parche la
# reemplaza, así que prepare.sh comprueba que las cabeceras del kernel con el
# que se compila tienen exactamente la misma función.
sed -n '/^static inline void hci_conn_drop(/,/^}/p' \
    "$SRC/include/net/bluetooth/hci_core.h" | sha256sum | cut -d' ' -f1 \
    > "$DEST/hci_conn_drop.sha256"
[ -s "$DEST/hci_conn_drop.sha256" ] || { echo "No encuentro hci_conn_drop()" >&2; exit 1; }

cat > "$DEST/SOURCE" <<EOF
$ORIGIN
kernel $VER  commit $(git -C "$SRC" rev-parse HEAD)
paths: net/bluetooth (copiado sin cambios)
EOF

echo "Fuente de net/bluetooth $VER en ${DEST#"$HERE"/}"
