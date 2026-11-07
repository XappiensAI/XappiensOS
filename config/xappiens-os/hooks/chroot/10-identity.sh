#!/bin/bash
# XappiensOS: genera la identidad del sistema (/etc/xappiens/*) y la activa.
set -euo pipefail

: "${DISTRO_NAME:=XappiensOS}"
: "${DISTRO_VERSION:=26.04}"
: "${UBUNTU_CODE:=resolute}"

PRETTY="$DISTRO_NAME $DISTRO_VERSION LTS"

mkdir -p /etc/xappiens

cat > /etc/xappiens/os-release <<OSR
NAME="$DISTRO_NAME"
VERSION="$DISTRO_VERSION LTS"
ID=xappiens
ID_LIKE="pop ubuntu debian"
PRETTY_NAME="$PRETTY"
VERSION_ID="$DISTRO_VERSION"
HOME_URL="https://github.com/XappiensAI/XappiensOS"
SUPPORT_URL="https://github.com/XappiensAI/XappiensOS/discussions"
BUG_REPORT_URL="https://github.com/XappiensAI/XappiensOS/issues"
VERSION_CODENAME=$UBUNTU_CODE
UBUNTU_CODENAME=$UBUNTU_CODE
LOGO=distributor-logo-pop-os
OSR

cat > /etc/xappiens/lsb-release <<LSB
DISTRIB_ID=XappiensOS
DISTRIB_RELEASE=$DISTRO_VERSION
DISTRIB_CODENAME=$UBUNTU_CODE
DISTRIB_DESCRIPTION="$PRETTY"
LSB

printf '%s \\n \\l\n\n' "$PRETTY" > /etc/xappiens/issue
printf '%s\n' "$PRETTY" > /etc/xappiens/issue.net

chmod 0755 /usr/lib/xappiens/apply-branding
/usr/lib/xappiens/apply-branding

echo "Identidad del sistema:"
cat /etc/os-release
