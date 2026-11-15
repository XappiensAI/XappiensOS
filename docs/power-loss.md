# Batería agotada y apagados forzados

## Qué pasó (15 de noviembre de 2026, ASUS ProArt P16 H7606WV)

1. Al 2 % de batería UPower lanzó su acción crítica por defecto,
   `HybridSleep`. La hibernación no está configurada en una instalación
   normal (no hay `resume=` en la línea del kernel, el swapfile de 12 GB es
   menor que los 30 GB de RAM y zram no sirve para guardar la imagen), así que
   el equipo se quedó en `PM: hibernation: hibernation entry` sin terminar.
   El gancho `pop-default-settings_zram-hibernate` además falla en `/bin/sh`
   (`[: pre: unexpected operator`) y no detiene zram.
2. Se conectó el cargador y hubo que apagarlo a la fuerza.
3. En el siguiente arranque `fsck` recuperó el journal de la raíz (inodos
   huérfanos de archivos abiertos, nada perdido) y quitó el bit de sucio de la
   partición EFI. `dpkg --audit` quedó limpio: no se cortó ninguna
   actualización.
4. Desde entonces **todo** iba de 4 a 10 veces más lento, también la BIOS y
   el cargador de arranque (firmware 5,9 s → 23 s, cargador 0,4 s → 9,9 s,
   espacio de usuario 11 s → 93 s). La CPU no pasaba de ~600 MHz con un núcleo
   al 100 %, aunque el límite de la política era 5,1 GHz, la temperatura era
   43 °C y los límites de potencia (`ppt_*`) seguían en 80 W. Cambiar el perfil
   de energía no tenía efecto.
5. Por la lentitud, udev tardaba más de un minuto en preparar las GPU y el
   compositor de acceso (`cosmic-comp` del usuario `cosmic-greeter`) arrancaba
   antes de tiempo: `Backend initialized without output` varias veces hasta
   que la AMD estaba lista.

El límite lo impone el controlador embebido (EC) del portátil, por debajo del
sistema operativo. No se arregla desde Linux.

## Cómo recuperarlo

1. Apaga el equipo del todo (no suspender).
2. Desconecta el cargador y cualquier dispositivo USB-C.
3. Mantén pulsado el botón de encendido **40 segundos**.
4. Conecta el cargador original y enciende.

Comprobación: `/usr/lib/xappiens/power-check --quiet; echo $?` devuelve `0`
y dice hasta cuántos MHz llega la CPU. Si sigue en `1`, entra en la BIOS
(F2 al encender), carga los valores por defecto, guarda y repite el
apagado de 40 segundos.

## Qué hace XappiensOS para que no vuelva a pasar

- **Apagado limpio antes de agotar la batería.**
  `/etc/UPower/UPower.conf.d/60-xappiens-battery.conf` cambia la acción
  crítica a `PowerOff` (logind apaga de forma ordenada) y deja más margen:
  aviso al 15 %, crítico al 8 % y apagado al 5 %. Cerca del vacío esta batería
  deja de informar bien de su carga (`\_SB.BAT1._BST` falla en el journal) y
  el porcentaje cae a saltos, así que el 2 % original era demasiado justo.
  Si tu equipo sí tiene la hibernación configurada, crea
  `/etc/UPower/UPower.conf.d/90-local.conf` con
  `[UPower]` y `CriticalPowerAction=HybridSleep`.
- **Aviso si el firmware deja la CPU limitada.** Al iniciar sesión en COSMIC,
  `xappiens-power-check.service` espera 45 s, carga un núcleo durante 2 s y,
  si no pasa de 1,25 veces la frecuencia mínima mientras la política permite
  al menos el doble, muestra una notificación con los pasos de arriba y lo
  deja en el journal (`journalctl --user -u xappiens-power-check`). No cambia
  ningún ajuste; si el usuario limita la CPU a propósito (política baja), no
  avisa.

## Aplicarlo en un equipo ya instalado

Con el paquete: `packaging/build-deb.sh` y
`sudo apt install ./build/packages/xappiens-default-settings_*.deb`.

A mano, desde el repositorio:

```bash
sudo install -Dm644 config/xappiens-os/includes.chroot/etc/UPower/UPower.conf.d/60-xappiens-battery.conf /etc/UPower/UPower.conf.d/60-xappiens-battery.conf
sudo systemctl restart upower
```
