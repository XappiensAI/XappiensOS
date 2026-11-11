# Arranque gráfico, HDMI y particiones EFI

## Entrega de la gráfica a COSMIC

`cosmic-greeter` y la sesión del usuario ejecutan compositores distintos.
Si el segundo arranca antes de que termine el primero, puede recibir
`Failed to add device ... Resource temporarily unavailable` y finalizar con
`Backend initialized without output`. El problema está descrito en
[cosmic-greeter#500](https://github.com/pop-os/cosmic-greeter/issues/500).

El perfil de XappiensOS ejecuta `prepare-session` antes de que `start-cosmic`
inicie el compositor del usuario. Espera a que termine el `cosmic-comp` de la
cuenta `cosmic-greeter`, con un límite de cinco segundos. No mata procesos,
abre dispositivos DRM ni reinicia el gestor de acceso. Los procesos zombis
no cuentan: ya han liberado sus descriptores. Si no hay compositor de acceso,
continúa inmediatamente; si vence el límite, registra un aviso y continúa.

La protección se aplica a sesiones Wayland COSMIC nuevas cuyo shell de inicio
carga `/etc/profile`, como Bash, el shell predeterminado de esta instalación.
No se ejecuta en terminales de un escritorio ya activo, otros escritorios,
TTY, root ni la propia cuenta del acceso. Un shell que no carga ese perfil
necesita su propia integración; esta mitigación no sustituye el arreglo upstream
ni garantiza resolver todos los errores que muestran el mismo mensaje.

El aviso aislado `Unable to become drm master` también puede aparecer en
sesiones que funcionan. Para diagnosticar, buscar el error fatal, la secuencia
de sesiones y si realmente aparece el escritorio; `graphical.target` no lo
demuestra por sí solo.

## Servicio antiguo de pegado

Las herramientas actuales de atajos y portapapeles no necesitan `ydotoold`.
`prepare-session` desactiva el antiguo servicio de usuario de hotkey-paste
únicamente si coincide con la configuración original, está habilitado, su
ejecutable `/usr/bin/ydotoold` no existe y no tiene overrides de systemd.
Conserva el archivo de servicio para poder revertir la operación. No modifica
instalaciones funcionales o personalizadas. Puede ejecutarse expresamente en
una sesión existente, sin sudo:

```bash
/usr/lib/xappiens/prepare-session --cleanup-legacy
```

## NVIDIA y HDMI

En portátiles híbridos, la pantalla interna y HDMI pueden pertenecer a GPU
distintas. Comprobarlo con `lspci -nnk` y los conectores de `/sys/class/drm/`
antes de deshabilitar un controlador. Deshabilitar la NVIDIA puede inutilizar
el HDMI aunque el escritorio siga funcionando en la integrada.

Para obtener el controlador NVIDIA integrado con la base Pop!_OS, seguir la
[documentación de System76](https://support.system76.com/support/system76-driver)
y revisar primero el plan de APT:

```bash
apt-get --simulate --no-remove install system76-driver-nvidia
sudo apt-get --no-remove install system76-driver-nvidia
```

Para la ISO, `NVIDIA=1 ./build.sh` incluye ese metapaquete. El repositorio no
fija una rama numérica del controlador ni instala NVIDIA en todo el hardware.
Después de instalar, comprobar DKMS y el initramfs antes del siguiente
reinicio. No descargar Nouveau ni reiniciar COSMIC mientras se usa la sesión.

## Identificar la EFI antes de reparar

No asumir que la EFI activa es la primera partición. Puede quedar una EFI de
Windows y existir otra utilizada por Linux. Comparar:

```bash
findmnt /boot/efi
lsblk -o NAME,SIZE,FSTYPE,PARTUUID,MOUNTPOINTS
cat /etc/fstab
sudo bootctl status
sudo efibootmgr -v
```

El aviso `FAT-fs (nvme...): Volume was not properly unmounted` identifica la
partición concreta; no debe trasladarse a otra por su posición en el disco.
Antes de reparar: guardar copia, desmontar la partición, comprobar con
`fsck.fat -n` el dispositivo verificado y revisar el resultado. Tras reparar,
volver a comprobar y montar en su ubicación original. No ejecutar reparación
sobre un sistema de archivos montado.

Una EFI antigua de 100 MB aporta poco espacio recuperable. Conservarla hasta
verificar las entradas del firmware, sus cargadores y un arranque correcto
desde la EFI nueva. Su eliminación y la de posibles particiones de recuperación
son tareas separadas; no forman parte de una reparación del escritorio.

## Operaciones administrativas con registro de salida

En la base 26.04 con `sudo-rs 0.2.13`, un comando como
`sudo script | tee registro` puede dejar procesos hijos suspendidos (`T` en
`ps`). Es un problema distinto del bloqueo gráfico; upstream corrigió la
[propagación de SIGCONT al grupo de procesos](https://github.com/trifectatechfoundation/sudo-rs/pull/1530).
Si la versión de la distribución aún presenta el fallo y está instalado
`/usr/bin/sudo.ws`, usar ese sudo clásico para la operación. No iniciar otra
reparación de disco o de paquetes mientras la primera siga suspendida.

## Validación

`tests/test_prepare_session.py` comprueba la espera acotada, procesos que
desaparecen, zombis, aislamiento entre usuarios, integración del perfil y
conservación de servicios ajenos. La suite usa procesos y systemd simulados;
no toca la sesión del usuario. La comprobación final requiere iniciar sesión
de nuevo y probar HDMI en el hardware afectado.
