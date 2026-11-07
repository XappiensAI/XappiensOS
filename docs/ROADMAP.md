# Hoja de ruta de XappiensOS

## Hito 0 — Cimientos ✅
- [x] Sistema de construcción derivado de `pop-os/iso`, siguiendo upstream.
- [x] Configuración `xappiens-os/26.04` heredando de Pop!_OS 26.04.
- [x] Mecanismo de overlays (`includes.*`) y hooks por etapa.
- [x] Identidad del sistema (`os-release`, `lsb-release`, `issue`) que sobrevive
      a las actualizaciones de `pop-default-settings`.

## Hito 1 — Primera ISO arrancable
- [ ] Construir `xappiens-os_26.04_amd64.iso` y arrancarla en QEMU (UEFI y BIOS).
- [ ] Verificar que el instalador funciona con `ID=xappiens`
      (si alguna herramienta de Pop exige `ID=pop`, documentarlo y ajustar).
- [ ] Instalar en una VM y comprobar actualizaciones con `apt full-upgrade`.
- [ ] Probar en hardware real (este equipo) desde USB.

## Hito 2 — Marca propia (necesario antes de distribuir públicamente)
Pop!_OS y sus logotipos son marcas registradas de System76: una distro derivada
que se publique debe sustituir su imagen.
- [ ] Logo e iconos `distributor-logo-xappiens-os` (y cambiar `LOGO=` en os-release).
- [ ] Tema de GRUB propio (sustituir el submódulo `data/grub-theme`).
- [x] Tema de Plymouth (pantalla de arranque): `branding/plymouth/`.
- [ ] Fondos de pantalla y ajustes por defecto de COSMIC.
- [ ] Nombre/usuario de la sesión live y textos del instalador.

## Hito 3 — Paquetes y repositorio propios
- [ ] Paquete `xappiens-default-settings` (sustituye overlays/hooks por un .deb).
- [ ] Paquete `xappiens-desktop` (metapaquete sobre `pop-desktop`).
- [ ] Repositorio APT firmado de XappiensOS (p. ej. GitHub Pages + reprepro/aptly).
- [ ] Clave de firma oficial del proyecto (sustituir la clave local de `build.sh`).

## Hito 4 — Integración continua y lanzamientos
- [ ] GitHub Actions: validación de scripts (shellcheck) en cada PR.
- [ ] Construcción de la ISO en un runner propio (necesita `sudo` y ~25 GB).
- [ ] Publicación de ISOs + SHA256SUMS firmados en GitHub Releases.

## Hito 5 — Lo que nos hace distintos
- [ ] Definir las aplicaciones y personalizaciones propias de XappiensOS.
