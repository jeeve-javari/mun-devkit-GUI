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
| Setup | Comprobar este ordenador, obtener las herramientas de MUN OS, construir el entorno del SDK; **Check for updates** / **Update & restart** | `mdk doctor`, `mdk os fetch`, `mdk env build`; `git fetch` + `git pull --ff-only` |
| Project | Elegir una **pista de motor**, crear un proyecto, luego compilar / comprobar / empaquetar | `mdk new` / copia del ejemplo; `build`, `check`, `pack` |
| Engines | Mapa sincero de cada pista (lista / parcial / planificada) | — |
| Simulate | **Play in MUN OS** (copia el `.img` empaquetado → `mun play --card`); o sesión en contenedor del SDK | `mun play --card …` / `mdk sim --container …` |

**Update & restart** (también el botón **Update…** del encabezado) obtiene el
remoto git del Devkit, adelanta tu rama actual y vuelve a abrir la ventana.
Rechaza un árbol sucio o una rama divergente: limpia eso en una terminal
antes. Necesita un clon git normal (no un zip sin `.git`).

**Play in MUN OS** necesita un checkout de mun-os (la carpeta donde ejecutas
`py mun play`). Indica esa ruta una vez en la pestaña Simulate; se guarda con
el resto de ajustes. **Pack then Play** empaqueta la tarjeta y abre QEMU de
un tirón.

### Pistas de motor (para todos)

Un juego de MUN es siempre un programa **Linux AArch64** en una Game Card.
La interfaz no finge que todo motor exporte hoy: nombra el camino:

| Pista | Estado | Crear proyecto |
| --- | --- | --- |
| Nativo (C / SDL2) | Lista | `mdk new` (hello-mun) |
| Godot 3.5 + FRT | Lista | copia `samples/hello-mun-godot3` |
| Godot 3.6+ | Parcial | solo guía — usa la pista 3.5 y alinea tu build |
| Godot 4.7 | Parcial | copia `samples/hello-mun-godot` (exportación a consola aún no) |
| Unity | Planificada | guía — hace falta un player arm64 y trabajo de perfil |
| Unreal | Planificada | guía — probablemente un perfil Vulkan más adelante |
| Trae tu propio binario | Lista | andamiaje de la tarjeta nativa; sustituye el ELF de entrada |

Que el hardware «soporte Unity / Unreal» es necesario pero no basta: MUN
sigue necesitando un perfil de ejecución, las reglas de la tarjeta (entrada
≤ 64 MiB, `content/` noexec) y el empaquetado del Devkit. Hasta entonces
esas filas quedan **Planificada** y apuntan a
[traer un juego](https://github.com/Play-MUN/mun-os/blob/main/docs/guides/port-a-game.md).

El paquete completo sigue siendo este repositorio: el cliente en C, los
contratos, los ejemplos, los adaptadores de Godot, las pruebas y el propio
`mdk`. La lógica de pistas vive en `tools/gui/engines.py` para que un motor
nuevo sea datos, no un fork de la interfaz.

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
sigue el mismo recorrido que el README. La carpeta del proyecto (y los campos de
«nuevo proyecto») se guardan en `~/.config/mun-devkit/gui-state.json` al cerrar
la ventana.

Si la consola negra parpadea y se cierra: ejecuta el lanzador desde PowerShell
para que el error se quede en pantalla (`.\scripts\windows\Launch-MdkGui.bat`).
También se escribe una copia del registro en `%TEMP%\mun-devkit-launch.log`.
Lo más habitual es que falte Tk (`sudo apt install -y python3-tk` en Ubuntu)
o que WSLg necesite `wsl --update`.

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
