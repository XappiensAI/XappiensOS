# XappiensOS

**XappiensOS** es un sistema operativo libre basado en **Pop!_OS** y en
**Ubuntu 26.04 LTS "Resolute Raccoon"**, con el escritorio **COSMIC**.

Queremos conservar lo mejor de Pop!_OS —ligereza, rendimiento, compatibilidad de
hardware, un escritorio moderno— y construir encima nuestra propia identidad,
ajustes y herramientas.

> Estado: **pre-alfa**. El sistema de construcción funciona sobre la base de
> Pop!_OS 26.04; la marca propia está en curso. Ver [docs/ROADMAP.md](docs/ROADMAP.md).

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

## Estructura

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

GPL-3.0, igual que el sistema de construcción de Pop!_OS del que deriva
(ver [LICENSE.md](LICENSE.md)). Pop!_OS y System76 son marcas de System76, Inc.;
XappiensOS es un proyecto independiente y no está afiliado a System76.
