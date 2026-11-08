# Atajos personalizados

**Atajos personalizados**, en el menú de aplicaciones, permite asociar una
combinación a **pegar un texto** o **ejecutar un comando**. La herramienta forma
parte del overlay de la ISO y de `xappiens-default-settings`; no requiere keyd,
ydotool, acceso al teclado físico ni servicios ejecutados como administrador.

Para pegar una cadena con **Ctrl + Alt + '**:

1. Abre **Atajos personalizados** y pulsa **Añadir**.
2. Escribe un nombre y captura Ctrl + Alt + ' con **Capturar…**, o escribe la combinación directamente.
3. Selecciona **Pegar texto**, introduce el contenido y guarda.
4. Vuelve a la aplicación de destino y pulsa la combinación.

En el teclado español, **'** (junto al 0, `apostrophe`) y **´** (a la derecha de
ñ, `dead_acute`) son teclas distintas. Si quieres la tecla junto a ñ, captura
esa tecla o escribe **Ctrl+Alt+´**. El editor también admite **Ctrl+Alt+dead_acute**.

El texto puede contener Unicode, saltos de línea y caracteres de shell: se
transfiere como datos al portapapeles, sin interpretarlo como código. El pegado
usa CLIPBOARD y PRIMARY junto con Shift + Insert mediante el teclado virtual
Wayland que ofrece COSMIC. Las aplicaciones que no admiten Shift + Insert
requieren pegar manualmente con su acción habitual de pegado. Ejecutar un
comando es una acción distinta y explícita.

Los atajos se registran en la configuración del usuario de COSMIC y se aplican
sin reiniciar. Se conservan las entradas ajenas. Una combinación ya usada por
otro atajo personalizado se rechaza; libera esa combinación primero en Ajustes
de COSMIC. Los textos se guardan en
`$XDG_CONFIG_HOME/xappiens/shortcuts.json` (por defecto
`~/.config/xappiens/shortcuts.json`), con permisos 0600. No están cifrados y el
texto pegado entra en el portapapeles normal y puede aparecer en su historial.
El mapa de COSMIC contiene únicamente la ruta del ejecutor y el identificador
de la acción. Antes de modificarlo se guarda una copia
`custom.before-xappiens-shortcuts` junto al archivo `custom`.

## Probarlo en un equipo de desarrollo

El paquete completo de identidad está dirigido a Pop!_OS 26.04. Para instalar
solo esta herramienta en una sesión COSMIC existente, incluso sobre 24.04:

```bash
python3 scripts/install-shortcuts-local.py
```

Se instala para el usuario actual en `~/.local/lib/xappiens-shortcuts`, con un
acceso en aplicaciones y el comando `~/.local/bin/xappiens-shortcuts`.
Las dependencias son Python 3, PyGObject, GTK 3, wl-clipboard,
libwayland-client, libxkbcommon y xkb-data, ya presentes en XappiensOS.

El instalador admite `--migrate-legacy` para sustituir las entradas locales
antiguas `hotkey-paste-1` y `hotkey-paste-2`, leyendo sus valores como datos y
sin mostrarlos. Conserva los scripts originales y una copia del mapa anterior.
Si existe `/etc/keyd/hotkey-paste.conf`, hay que retirar ese archivo de la
configuración activa y recargar keyd: intercepta las combinaciones antes de
que lleguen a COSMIC.

## Validación

```bash
python3 -m unittest discover -s tests -v
```

Las pruebas del gestor utilizan configuraciones temporales; comprueban
preservación de entradas, conflictos, Unicode, permisos y errores de pegado.
La prueba Wayland opcional utiliza COSMIC real anidado en Sway headless, con
configuración, bus y portapapeles aislados y texto de ejemplo. Comprueba
Ctrl + Alt + ' con teclado español, Unicode y saltos de línea, modificadores
mantenidos durante el pegado, escritura posterior y repetición del atajo.
También crea, edita y elimina acciones con COSMIC ya iniciado, comprobando
que los cambios se aplican sin reiniciar la sesión.
Requiere `cosmic-comp`, Sway, GTK 3, wl-clipboard y una sesión con permiso para
crear sockets temporales. Se ejecuta con:

```bash
python3 tests/test_shortcuts_wayland.py -v
```
