# Hoja de ruta de XappiensOS

## Hito 0 — Cimientos ✅
- [x] Sistema de construcción derivado de `pop-os/iso`, siguiendo upstream.
- [x] Configuración `xappiens-os/26.04` heredando de Pop!_OS 26.04.
- [x] Mecanismo de overlays (`includes.*`) y hooks por etapa.
- [x] Identidad del sistema (`os-release`, `lsb-release`, `issue`) que sobrevive
      a las actualizaciones de `pop-default-settings`.

## Hito 1 — Primera ISO arrancable
- [ ] Construir `xappiens-os_26.04_amd64.iso` y arrancarla en QEMU (UEFI y BIOS).
- [x] distinst exige `NAME="Pop!_OS"` en el os-release de la imagen: la ISO
      lleva la identidad de Pop en el squashfs y aplica la de XappiensOS al
      arrancar (`xappiens-identity.service`). Ver la guía técnica.
- [x] Instalación completa en VM (QEMU, UEFI): instala, arranca y queda
      con identidad, logo, avatar y equipo `xappiens-os`.
- [ ] Instalar en una VM y comprobar actualizaciones con `apt full-upgrade`.
- [ ] Probar en hardware real (este equipo) desde USB.

## Hito 2 — Marca propia (necesario antes de distribuir públicamente)
Pop!_OS y sus logotipos son marcas registradas de System76: una distro derivada
que se publique debe sustituir su imagen.
- [x] Logo `distributor-logo-xappiens` (`LOGO=` en os-release) en lugar del
      de Pop!_OS en su tema de iconos: `branding/installer/`.
- [x] Tema de GRUB propio para el menú de arranque de la ISO.
- [x] Tema de Plymouth (pantalla de arranque): `branding/plymouth/`.
- [x] Instalador con nuestra marca: colores, ilustraciones, icono, nombre
      "Instalar XappiensOS" y equipo `xappiens-os` en vez de `pop-os`.
- [x] Instalador con la marca validado en QEMU (UEFI).
- [ ] Probarlo en hardware real y en BIOS.
- [ ] Textos del instalador que nombran Pop!_OS en su código (exige un fork
      de `pop-installer`).
- [ ] Fondos de pantalla y ajustes por defecto de COSMIC.

## Hito 3 — Paquetes y repositorio propios
- [x] Paquete `xappiens-default-settings` (`packaging/build-deb.sh`): convierte un
      Pop!_OS 26.04 instalado en XappiensOS sin reinstalar. Comparte el overlay
      con la ISO.
- [x] Paquete `xappiens-bt-sco-fix-dkms`: micrófono Bluetooth mudo tras la primera
      llamada (parche SCO/eSCO). Hay que añadir la fuente de cada kernel nuevo de
      Pop!_OS con `fetch-source.sh`.
- [ ] Paquete `xappiens-desktop` (metapaquete sobre `pop-desktop`).
- [ ] Repositorio APT firmado de XappiensOS (p. ej. GitHub Pages + reprepro/aptly).
- [ ] Clave de firma oficial del proyecto (sustituir la clave local de `build.sh`).

## Hito 4 — Integración continua y lanzamientos
- [ ] GitHub Actions: validación de scripts (shellcheck) en cada PR.
- [ ] Construcción de la ISO en un runner propio (necesita `sudo` y ~25 GB).
- [ ] Publicación de ISOs + SHA256SUMS firmados en GitHub Releases.

## Hito 5 — Lo que nos hace distintos
- [x] Historial del portapapeles de sesión: diálogo con Super + V, texto e
      imágenes, incluido en la ISO y en `xappiens-default-settings`.
- [x] Editor de atajos personalizados: pegar texto o ejecutar comandos sin
      servicios privilegiados. Pegado validado en COSMIC aislado con teclado español.
- [ ] Validar los atajos personalizados en la ISO instalada y ampliar la
      comprobación entre aplicaciones ([guía](keyboard-shortcuts.md)).
- [ ] Validar el historial en la ISO instalada, incluidas varias pantallas,
      pegado entre aplicaciones y cierre de sesión ([pruebas](clipboard-history.md)).
- [ ] Definir las aplicaciones y personalizaciones propias de XappiensOS.
