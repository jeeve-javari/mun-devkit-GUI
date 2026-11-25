# Interfaz gráfica amigable

[English](gui.md) · **Español**

Una interfaz de escritorio para la misma herramienta de anfitrión que describe
el README. Cada botón ejecuta `mdk` con los mismos argumentos que escribirías;
el panel de registro muestra la misma salida. No sustituye a la CLI: la envuelve.

```sh
./mdk-gui
# o
./mdk gui
```

Necesita una pantalla (una sesión de escritorio normal, o WSLg en Windows 11).
Python 3.9 o posterior con Tk (`python3-tk` en Debian/Ubuntu).

## Qué puede hacer

| Pestaña | Acciones | Igual que |
| --- | --- | --- |
| Setup | Comprobar este ordenador, obtener las herramientas de MUN OS, construir el entorno del SDK | `mdk doctor`, `mdk os fetch`, `mdk env build` |
| Project | Proyecto nuevo a partir del ejemplo; compilar, comprobar, empaquetar | `mdk new`, `build`, `check`, `pack` |
| Simulate | Sesión con contenedor / tarjeta limpia / guion de hello-mun | `mdk sim --container …` |

El paquete completo sigue siendo este repositorio: el cliente en C, los
contratos, los ejemplos, el adaptador de Godot, las pruebas y el propio `mdk`.
La interfaz no envía un SDK más pequeño.

## Windows (Snapdragon X Elite / ARM, y x86)

Windows nativo aún no es un anfitrión de compilación de MUN: un juego de
consola es un programa Linux AArch64, y `mdk build` / `mdk sim --container`
necesitan un motor de contenedores que ejecute `linux/arm64`. En Windows ese
camino es **WSL 2 + Docker Desktop**.

| Tu PC | Qué ocurre |
| --- | --- |
| Windows en ARM (Snapdragon X Elite y similares) | WSL 2 es ARM64; los contenedores `linux/arm64` corren de forma nativa — el mismo camino cómodo que Linux ARM64 / Apple Silicon |
| Windows x86-64 | Docker emula `linux/arm64` (más lento); las tarjetas y las comprobaciones son las mismas |

1. En PowerShell con privilegios, desde la carpeta del repositorio:
   `powershell -ExecutionPolicy Bypass -File .\scripts\windows\Install-MdkGui.ps1`
   Eso instala Tk en WSL cuando puede, pone **MUN Devkit** en el Escritorio,
   e intenta abrir la ventana.
2. O haz doble clic en **`MUN Devkit.bat`** en la raíz del repositorio (el mismo lanzador).
3. Instala [Docker Desktop](https://www.docker.com/products/docker-desktop/) y
   activa la integración con WSL cuando quieras compilar / empaquetar / simular para la consola.

Luego, en la ventana, usa **Setup** hasta que doctor esté en verde, abre **Project** y
sigue el mismo recorrido que el README.

## Descarga

Una Release de GitHub puede adjuntar un zip de este árbol (código + puntos de
entrada de la GUI + ayudas de Windows). Descomprime, ejecuta el script de
Windows o `./mdk-gui` en macOS / Linux, y completa Setup una vez. Compilar
sigue necesitando Docker (y en Windows, WSL), como arriba: la interfaz no
puede inventar una cadena de herramientas que el anfitrión no tenga.

## macOS y Linux

El mismo recorrido binario que la CLI. En Apple Silicon y Linux ARM64 los
contenedores son nativos. En Linux x86-64, Docker usa emulación para
`linux/arm64` (véase la tabla de estado del README).
