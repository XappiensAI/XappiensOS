# Contribuir a XappiensOS / Contributing

Gracias por tu interés en XappiensOS. El proyecto está en **pre-alfa**: toda
ayuda para construir, probar y documentar el sistema es bienvenida.

## Antes de empezar

- Lee la [guía técnica](docs/DEVELOPMENT.md) y la [hoja de ruta](docs/ROADMAP.md).
- Busca en las [incidencias](https://github.com/XappiensAI/XappiensOS/issues)
  por si alguien ya ha informado del mismo problema o idea.

## Informar de un fallo

Abre una incidencia con:

1. La versión del sistema (`cat /etc/os-release`).
2. El paquete afectado y su versión (`apt policy <paquete>`).
3. Qué ha pasado, qué esperabas y cómo reproducirlo.
4. Registros o capturas si ayudan.

## Proponer cambios

1. Haz un fork y crea una rama desde `main`.
2. Mantén los cambios pequeños y centrados en un solo tema.
3. Lanza las pruebas (`python3 -m unittest discover -s tests -v`) antes de abrir el
   pull request; la sección [Pruebas](docs/DEVELOPMENT.md#pruebas) explica las
   comprobaciones de escritorio.
4. Describe en el pull request qué cambia y cómo lo has probado.

Los cambios sobre ficheros heredados del sistema de construcción original
deben ser mínimos; lo propio de XappiensOS vive en `config/xappiens-os/`,
`branding/`, `packaging/` y `scripts/xappiens-hooks.sh`.

## Licencia

Al contribuir aceptas que tu aportación se distribuya bajo la
[GPL-3.0](LICENSE.md) (o la licencia indicada en el directorio, como
`packaging/xappiens-bt-sco-fix-dkms/`, GPL-2.0-only).

---

**English:** bug reports and pull requests are welcome in English or Spanish.
Please follow the steps above: check existing issues, include system and
package versions, keep pull requests focused and run the tests before
submitting. Contributions are accepted under the GPL-3.0.

Toda participación se rige por nuestro [código de conducta](CODE_OF_CONDUCT.md).
