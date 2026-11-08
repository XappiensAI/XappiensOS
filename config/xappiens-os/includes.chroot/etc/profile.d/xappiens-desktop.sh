# cosmic-config busca los valores del sistema en XDG_DATA_DIRS, no en /etc/cosmic.
# El directorio generado conserva todos los atajos de COSMIC y añade Super+V.
case ":${XDG_DATA_DIRS:-}:" in
    *:/etc/xappiens:*) ;;
    *) XDG_DATA_DIRS="/etc/xappiens:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}" ;;
esac
export XDG_DATA_DIRS
# También cubre gestores --user que ya estaban activos al instalar el paquete
# (por ejemplo con linger). start-cosmic sólo importa claves ya conocidas por
# el gestor antes de iniciar el compositor; registra aquí XDG_DATA_DIRS.
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user import-environment XDG_DATA_DIRS >/dev/null 2>&1 || true
fi
