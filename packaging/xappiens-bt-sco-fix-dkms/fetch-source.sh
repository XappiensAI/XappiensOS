#!/usr/bin/env bash
# Añade la fuente original (kernel.org, rama stable) de net/bluetooth para una
# versión del kernel. El paquete DKMS sólo compila para las versiones que
# tengan su fuente aquí: así nunca se instala un Bluetooth de otra versión
# del kernel (le faltarían sus correcciones de seguridad).
#
# Uso:  packaging/xappiens-bt-sco-fix-dkms/fetch-source.sh 7.2.16
#       LINUX_SRC=/ruta/a/linux-stable fetch-source.sh 7.2.15   (sin descargar)
#
# Después, reconstruye el paquete: packaging/build-deb.sh
set -euo pipefail

VER="${1:?indica la versión del kernel, p. ej. 7.2.16}"
[[ $VER =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Versión no válida: $VER" >&2; exit 2; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HERE/upstream/$VER"
URL=https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git

TMP=""
if [ -n "${LINUX_SRC:-}" ]; then
    SRC="$LINUX_SRC"
    [ "$(git -C "$SRC" describe --tags --exact-match 2>/dev/null)" = "v$VER" ] ||
        { echo "$SRC no está en la etiqueta v$VER" >&2; exit 1; }
else
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    SRC="$TMP/linux"
    git clone --quiet --depth 1 --filter=blob:none --sparse --branch "v$VER" "$URL" "$SRC"
    git -C "$SRC" sparse-checkout set net/bluetooth include/net/bluetooth
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
$URL
tag v$VER  commit $(git -C "$SRC" rev-parse HEAD)
paths: net/bluetooth (copiado sin cambios)
EOF

echo "Fuente de net/bluetooth $VER en ${DEST#"$HERE"/}"
