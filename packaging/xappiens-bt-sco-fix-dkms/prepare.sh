#!/bin/sh
# DKMS PRE_BUILD: prepara net/bluetooth para el kernel que se va a compilar.
#   1. Elige la fuente original de esa versión exacta (upstream/<versión>/).
#   2. Comprueba que hci_conn_drop() de las cabeceras instaladas es la misma
#      que la de esa versión (el parche la sustituye).
#   3. Aplica los parches de patches/.
# Si algo no cuadra, falla: DKMS no instala nada y se queda el módulo original.
set -eu

kernelver="$1"
ksrc="$2"
base="${kernelver%%-*}"   # 7.2.15-76070215-generic -> 7.2.15

src="upstream/$base/net/bluetooth"
if [ ! -d "$src" ]; then
    echo "xappiens-bt-sco-fix: no hay fuente de net/bluetooth para $base" >&2
    exit 1
fi

header="$ksrc/include/net/bluetooth/hci_core.h"
expected="$(cat "upstream/$base/hci_conn_drop.sha256")"
actual="$(sed -n '/^static inline void hci_conn_drop(/,/^}/p' "$header" | sha256sum | cut -d' ' -f1)"
if [ "$actual" != "$expected" ]; then
    echo "xappiens-bt-sco-fix: hci_conn_drop() de $header no coincide con la de $base" >&2
    exit 1
fi

rm -rf net
mkdir -p net
cp -a "$src" net/bluetooth
for p in patches/*.patch; do
    patch -p1 --batch --forward --quiet < "$p"
done
