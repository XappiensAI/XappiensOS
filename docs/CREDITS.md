# Créditos y origen / Credits and origin

[← Volver a la portada](../README.md) · [Guía técnica](DEVELOPMENT.md) · [NOTICE](../NOTICE)

XappiensOS es un proyecto de **[Xappiens](https://xappiens.com)** (XappiensAI).
Se apoya en el trabajo de otras comunidades de software libre, y queremos
reconocerlo con claridad.

## Pop!_OS y System76

El sistema de construcción de XappiensOS es una obra derivada de
[`pop-os/iso`](https://github.com/pop-os/iso), el sistema con el que
**System76, Inc.** construye las imágenes de **Pop!_OS**. XappiensOS usa
también el escritorio **COSMIC**, el kernel `linux-system76`, el instalador
`pop-installer` / distinst y el tema de GRUB `pop-grub-theme`, todos
desarrollados por System76 y la comunidad de Pop!_OS.

- Proyecto original: <https://github.com/pop-os/iso> (GPL-3.0)
- Copyright (C) 2017-2026 System76, Inc. y colaboradores de Pop!_OS
- Autores principales del sistema de construcción original: Jeremy Soller,
  Michael Aaron Murphy y el resto de colaboradores que aparecen en el
  historial de git de este repositorio, que se conserva completo.
- Escritorio COSMIC: <https://github.com/pop-os/cosmic-epoch>

Los ficheros originales de documentación de Pop!_OS que hemos sustituido se
conservan sin cambios en [`docs/upstream/`](upstream/):

| Fichero original | Copia conservada |
|------------------|------------------|
| `README.md` | [README.pop-os-iso.md](upstream/README.pop-os-iso.md) |
| `CONTRIBUTING.md` | [CONTRIBUTING.pop-os.md](upstream/CONTRIBUTING.pop-os.md) |
| `CODE_OF_CONDUCT.md` | [CODE_OF_CONDUCT.pop-os.md](upstream/CODE_OF_CONDUCT.pop-os.md) |
| `.github/ISSUE_TEMPLATE.md` | [ISSUE_TEMPLATE.pop-os.md](upstream/ISSUE_TEMPLATE.pop-os.md) |

## Ubuntu

La base del sistema es **Ubuntu 26.04 LTS**, de Canonical Ltd. y la comunidad
de Ubuntu.

## Otros componentes

- Kernel Linux (`net/bluetooth`, GPL-2.0-only), en
  `packaging/xappiens-bt-sco-fix-dkms/`.
- Parche del micrófono de auriculares Bluetooth:
  [linux-bluetooth-headset-mic-fix](https://github.com/Mr-V1be/linux-bluetooth-headset-mic-fix).

## Marcas / Trademarks

Pop!_OS, COSMIC y System76 son marcas de System76, Inc. Ubuntu es una marca de
Canonical Ltd. XappiensOS es un proyecto independiente: no está afiliado a
System76 ni a Canonical, ni cuenta con su respaldo. Estos nombres se usan solo
para identificar el origen del software.

Pop!_OS, COSMIC and System76 are trademarks of System76, Inc. Ubuntu is a
trademark of Canonical Ltd. XappiensOS is an independent project, not
affiliated with or endorsed by System76 or Canonical.

El detalle legal completo (ficheros modificados, licencias y fuentes de los
paquetes) está en [NOTICE](../NOTICE).
