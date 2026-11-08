<p align="center">
  <img src="docs/assets/banner.svg" alt="XappiensOS — A desktop of our own · Un escritorio propio" width="100%">
</p>

<p align="center">
  <a href="docs/ROADMAP.md"><img src="https://img.shields.io/badge/status-pre--alpha-D5A57D?style=for-the-badge&labelColor=524B62" alt="Status: pre-alpha"></a>
  <a href="config/xappiens-os/26.04.mk"><img src="https://img.shields.io/badge/base-Ubuntu%2026.04%20LTS-738794?style=for-the-badge&labelColor=524B62&logo=ubuntu&logoColor=white" alt="Base: Ubuntu 26.04 LTS"></a>
  <a href="https://github.com/pop-os/cosmic-epoch"><img src="https://img.shields.io/badge/desktop-COSMIC-E8C984?style=for-the-badge&labelColor=524B62" alt="Desktop: COSMIC"></a>
  <a href="LICENSE.md"><img src="https://img.shields.io/badge/license-GPL--3.0-524B62?style=for-the-badge&logo=gnu&logoColor=E8C984" alt="License: GPL-3.0"></a>
</p>

<p align="center">
  <a href="#english"><b>🇬🇧 English</b></a> &nbsp;·&nbsp;
  <a href="#español"><b>🇪🇸 Español</b></a>
</p>

<p align="center">
  <a href="docs/DEVELOPMENT.md">Build guide / Guía técnica</a> &nbsp;·&nbsp;
  <a href="docs/ROADMAP.md">Roadmap</a> &nbsp;·&nbsp;
  <a href="https://github.com/XappiensAI">XappiensAI</a>
</p>

---

## English

**XappiensOS** is a free operating system built on **Pop!_OS**, **Ubuntu 26.04 LTS** and the **COSMIC** desktop. We keep that foundation and add our own identity, desktop tools and hardware-specific fixes.

Built by **[Xappiens](https://xappiens.com)**, developed in the open, and shared under the GPL-3.0.

> **Pre-alpha.** This repository contains the build system and packages. Validation of the complete ISO, installer and installed system is still pending. Follow the [roadmap](docs/ROADMAP.md) for the current state.

### What comes with XappiensOS

| | Feature | What it does |
|---|---|---|
| 📋 | **Clipboard history** | **Super + V** opens the text and images copied during the session. Pick an entry to paste it into the previous app. |
| ⌨️ | **Custom shortcuts** | Assign a key combination to paste saved text or run a command, with a built-in editor. [Guide](docs/keyboard-shortcuts.md). |
| 💡 | **Our own identity** | System identity and a custom Plymouth boot screen, shared by the ISO and the settings package. |
| 🎧 | **Targeted Bluetooth fixes** | Hardware-specific audio settings and a DKMS fix for the headset microphone issue documented [here](packaging/xappiens-bt-sco-fix-dkms/README.md). |
| 🪐 | **COSMIC desktop** | A Wayland desktop on the Pop!_OS foundation, with the upstream build history preserved. |

### Copy. Choose. Paste.

Copy a few items, press **Super + V**, and choose with the mouse or the arrow keys and **Enter**. Search, clear the history, or close it with **Escape**. The history stays in memory and ends when you sign out.

<p align="center">
  <img src="docs/assets/clipboard-history.png" alt="XappiensOS clipboard history popup, tested in an isolated Wayland session with sample content" width="420">
</p>

<p align="center"><sub>Actual clipboard tool in an isolated Wayland test session, using sample content.</sub></p>

The tool stores plain text and supported images. See the [clipboard guide](docs/clipboard-history.md) for storage limits, integration and tests.

### Get started

| I want to… | Start here |
|---|---|
| **Build an ISO** | [Build requirements and commands](docs/DEVELOPMENT.md#construir-la-iso) |
| **Use the settings package** | [Install on an existing Pop!_OS 26.04 system](docs/DEVELOPMENT.md#convertir-un-pop_os-2604-instalado) |
| **Understand the code** | [Architecture and repository layout](docs/DEVELOPMENT.md#estructura-del-repositorio) |
| **Test the clipboard** | [Automated and desktop checks](docs/clipboard-history.md#validación-en-una-sesión-cosmic-de-prueba) |
| **Help build XappiensOS** | [Roadmap](docs/ROADMAP.md), [issues](https://github.com/XappiensAI/XappiensOS/issues) and [development checks](docs/DEVELOPMENT.md#pruebas) |

The full settings package targets **Pop!_OS 26.04**. It changes system identity and must not be installed on 24.04. Building requires a Linux filesystem, about **25 GB free**, `sudo` and an internet connection.

<p align="right"><a href="#english">↑ back to top</a></p>

---

## Español

**XappiensOS** es un sistema operativo libre basado en **Pop!_OS**, **Ubuntu 26.04 LTS** y el escritorio **COSMIC**. Conservamos esa base y añadimos nuestra identidad, herramientas de escritorio y correcciones para hardware concreto.

Un proyecto de **[Xappiens](https://xappiens.com)**, desarrollado en abierto y compartido bajo la GPL-3.0.

> **Pre-alfa.** Este repositorio contiene el sistema de construcción y los paquetes. La validación de la ISO completa, el instalador y el sistema instalado sigue pendiente. Consulta el estado en la [hoja de ruta](docs/ROADMAP.md).

### Qué incluye XappiensOS

| | Función | Qué aporta |
|---|---|---|
| 📋 | **Historial del portapapeles** | **Super + V** muestra el texto y las imágenes copiados durante la sesión. Selecciona una entrada para pegarla en la aplicación anterior. |
| ⌨️ | **Atajos personalizados** | Asocia combinaciones de teclas a textos guardados o comandos con el editor incluido. [Guía](docs/keyboard-shortcuts.md). |
| 💡 | **Identidad propia** | Identidad del sistema y pantalla de arranque Plymouth, compartidas por la ISO y el paquete de ajustes. |
| 🎧 | **Correcciones de Bluetooth** | Ajustes de audio según el hardware y un módulo DKMS para el fallo del micrófono de auriculares descrito [aquí](packaging/xappiens-bt-sco-fix-dkms/README.md). |
| 🪐 | **Escritorio COSMIC** | Un escritorio Wayland sobre la base de Pop!_OS, conservando la historia del sistema de construcción original. |

### Copia. Elige. Pega.

Copia varios elementos, pulsa **Super + V** y elige con el ratón o con las flechas y **Enter**. Puedes buscar, vaciar el historial y cerrar con **Escape**. El contenido permanece en memoria y se borra al cerrar sesión.

La captura de arriba muestra la herramienta real en una sesión Wayland aislada con contenido de ejemplo. Guarda texto sin formato e imágenes compatibles; los límites, la integración y las pruebas están en la [guía del portapapeles](docs/clipboard-history.md).

### Empieza por aquí

| Quiero… | Guía |
|---|---|
| **Construir una ISO** | [Requisitos y comandos de construcción](docs/DEVELOPMENT.md#construir-la-iso) |
| **Usar el paquete de ajustes** | [Instalar sobre Pop!_OS 26.04](docs/DEVELOPMENT.md#convertir-un-pop_os-2604-instalado) |
| **Entender el código** | [Arquitectura y estructura del repositorio](docs/DEVELOPMENT.md#estructura-del-repositorio) |
| **Probar el portapapeles** | [Pruebas automáticas y de escritorio](docs/clipboard-history.md#validación-en-una-sesión-cosmic-de-prueba) |
| **Participar en el proyecto** | [Hoja de ruta](docs/ROADMAP.md), [incidencias](https://github.com/XappiensAI/XappiensOS/issues) y [comprobaciones de desarrollo](docs/DEVELOPMENT.md#pruebas) |

El paquete completo de ajustes está dirigido a **Pop!_OS 26.04**. Cambia la identidad del sistema y no debe instalarse sobre la 24.04. Para construir necesitas un sistema de ficheros Linux, unos **25 GB libres**, `sudo` y conexión a internet.

<p align="right"><a href="#español">↑ volver arriba</a></p>

---

<p align="center">
  <a href="LICENSE.md"><b>GPL-3.0</b></a> &nbsp;·&nbsp;
  <a href="NOTICE">Attribution / Atribución</a> &nbsp;·&nbsp;
  <a href="https://github.com/pop-os/iso">Upstream: pop-os/iso</a> &nbsp;·&nbsp;
  <a href="https://xappiens.com">xappiens.com</a>
</p>

<p align="center"><sub>Independent project. Pop!_OS and System76 are trademarks of System76, Inc. XappiensOS is not affiliated with System76.</sub></p>
<p align="center"><sub>Proyecto independiente. Pop!_OS y System76 son marcas de System76, Inc. XappiensOS no está afiliado a System76.</sub></p>
