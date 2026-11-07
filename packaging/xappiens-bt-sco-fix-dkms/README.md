# xappiens-bt-sco-fix-dkms

Arregla el micrófono de los auriculares Bluetooth que **funciona en la
primera llamada y se queda mudo al volver a entrar** (Meet, Discord, Zoom…).
Confirmado en un equipo con MediaTek MT7925 (`0489:e11e`) y kernel
`7.2.15-76070215-generic` de System76.

## Qué corrige

Al cambiar rápido de socket HFP, el kernel puede liberar una conexión eSCO
saliente mientras la controladora todavía la está estableciendo. HCI no tiene
orden para cancelar esa operación, así que la controladora la completa
después y queda un enlace huérfano: llega audio para un *handle* desconocido
y la aplicación ve un micrófono presente pero mudo.

El parche (`patches/0001-delay-pending-esco-cleanup.patch`) retrasa la
limpieza de una conexión SCO/eSCO pendiente (`BT_CONNECT`) los 2 s de
`HCI_DISCONN_TIMEOUT`. ACL, LE, las conexiones ya establecidas y A2DP no
cambian. Procede de
[linux-bluetooth-headset-mic-fix](https://github.com/Mr-V1be/linux-bluetooth-headset-mic-fix)
(fork: [XappiensAI/linux-bluetooth-headset-mic-fix](https://github.com/XappiensAI/linux-bluetooth-headset-mic-fix)),
GPL-2.0-only, y se aplica sin cambios. Las otras dos correcciones de ese
proyecto (`abd93c85c866`, `8a5b0135d4a5`) ya vienen en el kernel 7.2.

## Cómo funciona

- DKMS compila `bluetooth.ko` para cada kernel instalado y para los que se
  instalen después; sólo sustituye el módulo central (`rfcomm`, `bnep`… siguen
  siendo los del kernel).
- La fuente de `net/bluetooth` va en el paquete, copiada sin cambios de la
  rama *stable* de kernel.org (`upstream/<versión>/`). Sólo se compila para
  esas versiones exactas: con otro kernel se queda el módulo original, para
  no instalar nunca un Bluetooth al que le falten las correcciones de
  seguridad de la versión nueva.
- `prepare.sh` comprueba además que `hci_conn_drop()` de las cabeceras del
  kernel es idéntica a la de esa versión (el parche la sustituye).
- Con Secure Boot activo no se instala (un módulo sin firmar no cargaría y el
  equipo se quedaría sin Bluetooth).

## Cuando Pop!_OS publique un kernel nuevo

```bash
packaging/xappiens-bt-sco-fix-dkms/fetch-source.sh 7.2.16
packaging/build-deb.sh
```

`fetch-source.sh` descarga sólo `net/bluetooth` de esa etiqueta de kernel.org.
Revisa que el parche sigue aplicando (`prepare.sh` falla si no) antes de
publicar el paquete.

## Comprobar que está activo

```bash
dkms status xappiens-bt-sco-fix
modinfo -n bluetooth          # .../updates/dkms/bluetooth.ko
journalctl -k | grep bluetooth-mic-fix
```

La última línea aparece cuando el parche actúa durante una llamada
("delaying pending eSCO cleanup").
