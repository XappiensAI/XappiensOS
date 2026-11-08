# Guía técnica de XappiensOS

[← Volver a la portada](../README.md) · [Hoja de ruta](ROADMAP.md)

**XappiensOS** es un sistema operativo libre basado en **Pop!_OS** y en
**Ubuntu 26.04 LTS "Resolute Raccoon"**, con el escritorio **COSMIC**.

Queremos conservar lo mejor de Pop!_OS —ligereza, rendimiento, compatibilidad de
hardware, un escritorio moderno— y construir encima nuestra propia identidad,
ajustes y herramientas.

> Estado: **pre-alfa**. La configuración de construcción parte de Pop!_OS
> 26.04; la ISO completa, su instalador y la instalación en VM y hardware real
> siguen pendientes de validación. Ver [ROADMAP.md](ROADMAP.md).

## Base técnica

| Componente   | Origen                                            |
|--------------|---------------------------------------------------|
| Base         | Ubuntu 26.04 LTS (`resolute`)                     |
| Escritorio   | COSMIC (repositorios `resolute` de Pop!_OS)       |
| Kernel       | `linux-system76` (7.x)                            |
| Arranque     | systemd-boot + kernelstub (instalado), GRUB (ISO) |
| Live/initrd  | dracut (`dmsquash-live`)                          |
| Instalador   | `pop-installer` / distinst                        |
| Construcción | Fork de [`pop-os/iso`](https://github.com/pop-os/iso) (debootstrap + Makefiles) |

## Estructura del repositorio

```
config/
  pop-os/26.04.mk           # configuración original de Pop!_OS (upstream, no tocar)
  xappiens-os/
    26.04.mk                # nuestra configuración: hereda de Pop y sobrescribe
    includes.chroot/        # ficheros que se copian al sistema instalado
    includes.live/          # ficheros sólo para la sesión live (opcional)
    hooks/chroot/*.sh       # scripts ejecutados dentro del chroot del sistema
    hooks/live/*.sh         # scripts ejecutados dentro del chroot live
scripts/xappiens-hooks.sh   # aplica overlays y hooks (llamado desde mk/chroot.mk)
    grub-theme/             # menú de arranque de la ISO (generado)
packaging/                  # paquetes .deb (ajustes, módulo Bluetooth, marca del instalador)
branding/                   # fuentes de la marca: pantalla de arranque (plymouth/),
                            # logo, instalador y menú de arranque (installer/)
build.sh                    # punto de entrada para construir XappiensOS
mk/, data/, scripts/        # sistema de construcción heredado de Pop!_OS
docs/                       # documentación del proyecto
```

## Construir la ISO

Requisitos: un sistema basado en Ubuntu/Pop!_OS, `sudo`, ~25 GB libres en un
sistema de ficheros Linux (ext4/btrfs/xfs) y conexión a internet.

```bash
git clone --recurse-submodules https://github.com/XappiensAI/XappiensOS.git
cd XappiensOS
./deps.sh          # instala debootstrap, xorriso, squashfs-tools, qemu...
./build.sh         # construye la ISO en ~/xappiens-build/26.04/amd64/
./build.sh qemu    # arranca la ISO en una máquina virtual
```

> **Importante:** la construcción **no puede** hacerse en NTFS/exFAT/FAT.
> Si el repositorio está en un disco así, `build.sh` construye por defecto en
> `~/xappiens-build`; puedes cambiarlo con `XAPPIENS_BUILD_ROOT=/ruta/ext4`.

Variantes: `NVIDIA=1 ./build.sh` genera la ISO con drivers NVIDIA.

En un anfitrión Ubuntu/Pop!_OS 24.04, `debootstrap` todavía no conoce
`resolute`; el build usa entonces su script genérico de Ubuntu (`gutsy`), igual
que las versiones nuevas de debootstrap.

### Marca de la ISO y del instalador

- **Menú de arranque** (GRUB de la ISO): `config/xappiens-os/grub-theme/`,
  elegido con `GRUB_THEME`/`GRUB_THEME_DIR` en `config/xappiens-os/26.04.mk`.
- **Instalador** (`pop-installer`): el paquete `xappiens-installer-branding` se
  instala en la etapa live (`hooks/live/10-installer.sh`) con el estilo, las
  ilustraciones y el nombre "Instalar XappiensOS". Al instalar, el propio
  instalador lo purga junto con `pop-installer`.
- **Logo** `distributor-logo-xappiens` (`LOGO=` de os-release), que sustituye
  al de Pop!_OS en su tema de iconos (`hooks/chroot/50-logo.sh`).
- **Nombre del equipo**: `pop-installer` fija `pop-os`; el sistema instalado lo
  cambia por `xappiens-os` en el primer arranque (`xappiens-hostname.service`).
- **Identidad e instalador**: el motor del instalador (distinst) lee
  `/etc/os-release` de la imagen y sólo admite `NAME="Pop!_OS"`; con
  `XappiensOS` falla ("unsupported OS release"). Por eso el squashfs lleva los
  enlaces de identidad de Pop (`hooks/live/90-identity.sh`, último hook live) y
  `xappiens-identity.service` aplica la de XappiensOS en cada arranque, antes
  del escritorio. Durante la instalación también la aplica el hook de APT
  `99xappiens-branding`.

Todo lo gráfico sale de [`branding/installer/make-installer.py`](../branding/installer/README.md).

La clave GPG que puede generar `build.sh` es local al proceso de construcción;
no es una firma oficial de lanzamientos de XappiensOS. La publicación de ISOs y
sumas firmadas es un hito pendiente de la [hoja de ruta](ROADMAP.md).

## Convertir un Pop!_OS 26.04 instalado

El paquete `xappiens-default-settings` lleva el mismo contenido que la ISO
(identidad, pantalla de arranque y herramientas del escritorio), así que convierte un
Pop!_OS 26.04 en XappiensOS conservando tus archivos, aplicaciones y ajustes.

1. **Parte de una instalación ya basada en Pop!_OS 26.04**. El paquete de
   identidad no es compatible con 24.04. Si necesitas actualizar la base,
   consulta las [instrucciones oficiales de System76](https://support.system76.com/articles/upgrade-pop/)
   y las versiones disponibles para tu instalación. Haz antes una copia de
   seguridad de tus datos.
2. **Construye e instala los paquetes** (construirlos no necesita `sudo`):

   ```bash
   packaging/build-deb.sh
   sudo apt install ./build/packages/xappiens-default-settings_*.deb \
                    ./build/packages/xappiens-bt-sco-fix-dkms_*.deb
   ```

   - `xappiens-default-settings`: identidad, pantalla de arranque, historial del
     portapapeles, [atajos personalizados](keyboard-shortcuts.md) y ajustes de Bluetooth según el hardware (perfil de llamadas
     para MediaTek MT7925).
   - `xappiens-bt-sco-fix-dkms`: módulo bluetooth corregido para el micrófono
     de auriculares que se queda mudo tras la primera llamada
     ([detalles](../packaging/xappiens-bt-sco-fix-dkms/README.md)).

   El tercer paquete, `xappiens-installer-branding`, es sólo para la sesión
   live de la ISO (depende de `pop-installer`): no lo instales en un sistema
   ya instalado.

3. Reinicia para ver la nueva pantalla de arranque. El historial y su atajo se
   activan al volver a iniciar sesión en COSMIC.

Los ajustes de Bluetooth se aplican según el hardware. El módulo DKMS sólo se
compila para kernels cuya fuente está incluida; con otro kernel se usa el
módulo original. El alcance, los equipos comprobados y Secure Boot están
explicados en [la guía del módulo](../packaging/xappiens-bt-sco-fix-dkms/README.md).

El paquete se niega a instalarse sobre otra versión de la base (p. ej. 24.04),
porque `/etc/os-release` anunciaría una versión que no es la real. Para
volver a Pop!_OS basta con `sudo apt remove xappiens-default-settings`.

## Historial del portapapeles

En COSMIC, **Super + V** abre un diálogo con el texto y las imágenes copiados
durante la sesión. Selecciona una entrada para pegarla en la aplicación que
estabas usando. El historial arranca automáticamente y se conserva en memoria;
no se guarda entre sesiones. El diálogo también permite vaciarlo.

Viene incluido tanto en la ISO como en `xappiens-default-settings`. Después de
instalar el paquete, vuelve a iniciar sesión para activar el atajo y el servicio.
Se conservan las asignaciones de teclado personalizadas: si ya habías asignado
Super + V a otra función, puedes cambiarla en los ajustes de teclado de COSMIC.
Consulta [la integración y las pruebas de escritorio](clipboard-history.md).

## Pruebas

```bash
/usr/bin/python3 -m unittest discover -s tests -v
```

La suite cubre almacenamiento, límites, deduplicación, atajos, captura
asíncrona y widgets GTK. La prueba Wayland opcional requiere Sway, `grim`,
`wtype` y GtkLayerShell; utiliza datos de ejemplo en un compositor aislado.
Las pruebas opcionales se omiten si faltan herramientas o el sandbox impide
crear sockets temporales. No usan el portapapeles de la sesión del usuario.

Validar herramientas por separado no sustituye el arranque y la instalación
de la ISO completa en COSMIC. Consulta las comprobaciones de escritorio en
[la guía del portapapeles](clipboard-history.md#validación-en-una-sesión-cosmic-de-prueba).

## Seguir a Pop!_OS (upstream)

Este repositorio mantiene la historia de `pop-os/iso`, de modo que podemos
incorporar sus mejoras:

```bash
git remote add upstream https://github.com/pop-os/iso.git   # una sola vez
git fetch upstream
git merge upstream/master
```

Nuestros cambios sobre ficheros de upstream se limitan a propósito a muy pocas
líneas (`mk/automatic.mk`, `mk/chroot.mk`, `deps.sh`) para que las fusiones
sean sencillas. Todo lo demás vive en `config/xappiens-os/`.

## Licencia

XappiensOS es y será siempre **software libre**, bajo la GPL-3.0, igual que
el sistema de construcción de Pop!_OS del que deriva (ver [LICENSE.md](../LICENSE.md)).
La atribución al proyecto original, los ficheros modificados y los avisos de
marcas están en [NOTICE](../NOTICE). Pop!_OS y System76 son marcas de System76, Inc.;
XappiensOS es un proyecto independiente y no está afiliado a System76.
