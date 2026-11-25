# MUN Devkit

[English](README.md) · **Español**

[![Comprobaciones](https://github.com/Play-MUN/mun-devkit/actions/workflows/checks.yml/badge.svg?branch=main)](https://github.com/Play-MUN/mun-devkit/actions/workflows/checks.yml)
[![Licencia: Apache-2.0 y MIT-0](https://img.shields.io/badge/licencia-Apache--2.0%20%C2%B7%20MIT--0-blue)](docs/licensing.md)

Herramientas para hacer y portar juegos para MUN™: una herramienta de
ordenador (`mdk`), un pequeño cliente estático en C para lo que una consola
da a un juego, un simulador de sesión, y un ejemplo que va del código
fuente a la imagen de una Game Card.

Un juego de MUN es un programa corriente de Linux para AArch64 que sigue
unos pocos contratos de [MUN OS](https://github.com/Play-MUN/mun-os): una
tarjeta con un manifiesto, un perfil de ejecución, datos en el entorno y
partidas que la consola escribe en la tarjeta. El devkit no sustituye ni
envuelve esos contratos. Reutiliza la herramienta de tarjetas y el
validador del propio MUN OS, de modo que una tarjeta que hace `mdk` es una
tarjeta que el código de la consola ya ha leído.

**MUN Disk** y **Game Card** son una sola cosa: MUN Disk es el nombre del
soporte de la consola, el producto que un jugador tiene en la mano; Game
Card es como lo llaman su formato y sus herramientas, y también estas
páginas cuando hablan de la imagen, del manifiesto o de la herramienta de
tarjetas.

## El proyecto

MUN es una consola en desarrollo para juegos físicos que son tuyos, hecha
por Play MUN: [playmun.com](https://playmun.com). El devkit es uno de sus
dos repositorios abiertos:

| | |
| --- | --- |
| [MUN OS](https://github.com/Play-MUN/mun-os/blob/main/README.es.md) | El sistema operativo abierto de la consola. Funciona en tu ordenador con QEMU, y una tarjeta hecha con el devkit entra en él |
| [Running a game](https://github.com/Play-MUN/mun-os/blob/main/docs/runtime.md) | La sesión que recibe un juego: su perfil de ejecución, su entorno, cómo termina (en inglés) |
| [Saves](https://github.com/Play-MUN/mun-os/blob/main/docs/saves.md) | Qué es una partida guardada, el servicio que la escribe y cada código con que responde (en inglés) |
| [Game Cards](https://github.com/Play-MUN/mun-os/blob/main/docs/game-cards.md) | El formato de la tarjeta, su manifiesto y la herramienta de tarjetas (en inglés) |
| [Llevar un juego a MUN](https://github.com/Play-MUN/mun-os/blob/main/docs/es/guides/port-a-game.md) | La guía del propio MUN OS para portar un juego, paso a paso |

Esas páginas son los contratos; este repositorio los sigue y dice contra
qué revisión se comprobó (`mun-os.lock.json`).

## Estado

Temprano. Lo que existe es lo que se enumera aquí, y nada de ello se ha
ejecutado en el hardware de una consola.

| Parte | Estado |
| --- | --- |
| `mdk doctor`, `os`, `env`, `new`, `build`, `check`, `pack`, `sim` | Funcionan en macOS (Apple Silicon) y en Linux ARM64 con un motor de contenedores: cada pull request ejecuta allí el recorrido completo (Ubuntu 24.04). En Linux x86-64 se ejecutan las comprobaciones de ordenador; compilar para una consola necesita allí emulación y no se ha probado |
| MUN OS seguido | v0.1.0-dev.5 (`mun-os.lock.json`); las comprobaciones pasan también con las herramientas de v0.1.0-dev.4 |
| Cliente estático en C (`client/c`): datos de la sesión, restauración y guardado confirmado | Probado contra el simulador y contra partidas guardadas tal como las escribe una consola |
| Simulador de sesión | Reproduce la disposición de la sesión, el servicio de guardado y cómo termina una sesión; no el sandbox ni ningún dispositivo |
| Ejemplo `samples/hello-mun` (SDL2, OpenGL, OpenAL; perfil `linux-arm64-gl-v0`) | Compila, pasa las comprobaciones, se empaqueta y se ejecuta en el simulador, dibujando con el renderizador por software de Mesa |
| Adaptador para Godot (`engines/godot`): GDScript, sin código nativo | Escrito para Godot 4.7 y comprobado con una sola versión exacta, la oficial 4.7.2-stable para Linux ARM64, que `engines/godot/fetch.sh` descarga y verifica. Guarda y restaura contra el simulador; un juego exportado para una consola todavía no es posible ([por qué](engines/godot/README.md)). Otras versiones no se han probado: un informe de una que funcione, o que no, es bienvenido |
| Otros motores | Nada todavía |

Los perfiles de ejecución son de MUN OS y allí son provisionales: sus
documentos dicen que solo se han medido en máquinas virtuales.

## Qué necesitas

- Python 3.9 o posterior.
- Las herramientas del propio MUN OS, en la revisión que nombra
  `mun-os.lock.json`. `mdk os fetch` clona exactamente esa revisión en
  `.local/mun-os`; `--mun-os` o `MUN_OS_DIR` nombran otra copia, y
  `../mun-os`, junto al devkit, se usa cuando no hay otra. `mdk` dice qué
  revisión encuentra y avisa cuando difiere de la fijada.
- e2fsprogs 1.47 o posterior, para hacer imágenes de tarjeta (macOS:
  `brew install e2fsprogs`).
- Un motor de contenedores que ejecute `linux/arm64` (`docker`), para
  compilar para una consola. En un ordenador ARM64 la compilación es
  nativa.

`./mdk doctor` comprueba cada cosa y dice qué hacer con la que falte.

### Interfaz gráfica amigable

¿Prefieres botones a la terminal? El mismo recorrido está en una ventana de
escritorio:

```sh
./mdk-gui
# or
./mdk gui
```

Setup, proyecto nuevo, compilar, comprobar, empaquetar y simular llaman a
`mdk` con los mismos argumentos que la CLI. En Windows (Snapdragon X Elite /
ARM, o x86) el camino soportado es WSL 2 + Docker; véase
[docs/gui.md](docs/gui.md).

## De nada a una partida guardada

```sh
./mdk doctor                    # qué tiene este ordenador y qué le falta
./mdk os fetch                  # una vez: las herramientas de MUN OS en la revisión fijada
./mdk env build                 # una vez: el entorno de compilación (necesita la red)

./mdk new star-well --title "Star Well" --id org.example.star-well
cd star-well
../mdk build                    # compilar dentro del entorno
../mdk check                    # la compilación contra su perfil de ejecución
../mdk pack                     # build/star-well.img, y un registro de lo que contiene
../mdk sim --container --fresh --env MUN_HELLO_HEADLESS=1 \
           --env "MUN_HELLO_SCRIPT=up up up save wait quit"     # una sesión que guarda
../mdk sim --container --env MUN_HELLO_HEADLESS=1 \
           --env "MUN_HELLO_SCRIPT=up save wait quit"           # la siguiente restaura
```

`mdk new` copia el ejemplo nativo con el nombre del proyecto; desde
entonces el proyecto es suyo. `tests/test_journey.py` ejecuta exactamente
estos pasos y exige cada resultado. `make sample`, en la raíz, compila y
empaqueta el propio ejemplo; `make check` ejecuta las pruebas que este
ordenador puede ejecutar y nombra las que omitió, y `make check-full` falla
con cualquiera que no pueda ejecutar.

`make dev-tools` instala los dos analizadores de Python con versiones y
hashes fijados (`tools/dev-requirements.txt`) en `.local/venv`, y
`make analyse` los ejecuta. Un aviso se corrige o, cuando no es un defecto,
se marca en su propia línea con la regla y el motivo
(`# nosec B603: ...`); nunca para un fichero o una regla enteros. El código
C se compila con el analizador del compilador en el entorno de compilación
y no da ningún aviso.

Para ver la tarjeta en la consola virtual de MUN OS, desde la copia de
MUN OS (`.local/mun-os` después de `mdk os fetch`): `./mun get`,
`./mun dev run --window`, y después `./mun dev vm dev card-attach NAME` con
la imagen copiada a su `.local/gamecards/NAME.img`
(`docs/getting-started.md` de MUN OS).

### El entorno de compilación

`mdk build` ejecuta la orden de compilación del proyecto en un contenedor
Debian 13 ARM64 cuyos paquetes vienen de la misma instantánea fechada de
Debian que la imagen de MUN OS (`tools/env/Dockerfile`), sin acceso a la
red. El programa se enlaza así contra las versiones de las bibliotecas que
tiene una consola de esa línea de MUN OS, y la compilación no depende de lo
que tenga instalado el ordenador. `mdk env info` imprime las versiones del
compilador y de las bibliotecas.

### Las comprobaciones

`mdk check` lee el ejecutable de entrada y el contenido antes de hacer una
tarjeta:

```
E-ARCH    game is a 64-bit little-endian x86-64 program. MUN runs 64-bit AArch64 Linux programs.
          Build or export it for Linux ARM64 (aarch64); a Windows, macOS or x86-64 build must be made again.

E-LIB     game needs libcurl.so.4, which the profile linux-arm64-gl-v0 does not provide.
          The profile provides: libEGL.so.1, libGL.so.1, libSDL2-2.0.so.0, ...
          Link it into the game statically, or drop the feature that uses it. The card's content is
          read-only data: a library placed there cannot be loaded.
```

Cada hallazgo tiene un código estable, qué está mal y qué hacer. Los
códigos: `E-ENTRY`, `E-NOT-ELF`, `E-ARCH`, `E-NOT-PROGRAM`, `E-SIZE`,
`E-INTERP`, `E-LIB`, `E-GLIBC`, `E-CONTENT`, `E-CONTENT-LINK`,
`E-CONTENT-ENTRY`, `E-CARD-ID`, `E-CARD-VERSION`, `E-CARD-TITLE`,
`E-PROFILE`, `E-HARDEN`, `E-HARDEN-BUILD`, y los avisos `W-RUNPATH`,
`W-CODE`, `W-CARD-SIZE`, `W-HARDEN`, `W-HARDEN-BUILD`. La tarjeta en sí la
valida la herramienta de MUN OS, cuyos códigos están en
`docs/game-cards.md` de MUN OS.

### Endurecimiento

El ejemplo, un proyecto iniciado a partir de él y el cliente se compilan
con las opciones de `mk/hardening.mk`: `-fstack-protector-strong`,
`-fstack-clash-protection`, `-D_FORTIFY_SOURCE=3` (en una compilación que
optimiza), `-mbranch-protection=standard`, `-fPIE -pie` y
`-Wl,-z,relro -Wl,-z,now -Wl,-z,noexecstack`. Cada una se prueba antes en
el compilador y se deja fuera si la rechaza, de modo que el mismo makefile
compila en otro sistema.

Después `mdk check` lee el resultado, no el makefile:

```
hardening position-independent executable: yes; full RELRO: yes; non-executable stack: yes;
          stack protector: yes; fortified calls: yes; branch protection: yes
```

Seis propiedades están en el propio programa. La protección contra el
choque de pila no deja marca en él, y un programa solo muestra que *alguna*
función tiene canario: para eso, `mdk build` guarda las órdenes del
compilador que imprimió la compilación (`build/compile-commands.json`) y
`mdk check` exige todas las opciones en cada una de ellas.

`build.hardening`, en `mun-project.toml`, dice en qué caso está un
proyecto:

| Valor | Para | Una propiedad u opción que falta |
| --- | --- | --- |
| `"required"` | Un programa que compilas tú. El ejemplo y `mdk new` dicen esto | Un error: `E-HARDEN`, `E-HARDEN-BUILD` |
| `"report"` (por defecto) | Un ejecutable que no compilaste tú: la plantilla de exportación de un motor, un programa enlazado con una biblioteca compilada en otra parte | Un aviso, `W-HARDEN`. La comprobación pasa |

El segundo caso existe por la protección de saltos: el enlazador marca un
programa para BTI y PAC solo cuando todos sus objetos están marcados, y los
objetos de un motor o de una biblioteca no son del desarrollador para
recompilarlos.

### La tarjeta

`mdk pack` ejecuta `mun-card create` de MUN OS y después
`mun-card inspect`, y escribe `build/<name>.card.json`: el SHA-256 de la
imagen, lo que una consola lee de ella, el hash y las bibliotecas del
ejecutable, y las revisiones de las herramientas. Las mismas entradas y el
mismo e2fsprogs dan la misma imagen, byte a byte.

### El simulador

`mdk sim` ejecuta el juego como una sesión: una copia del ejecutable
arrancada sin argumentos, `work/` como su directorio personal, los datos
`MUN_*`, la partida restaurada desde un directorio de tarjeta
(`build/sim-card`), y un socket de guardado que responde como el de la
consola, con sus códigos y sus frases.

```sh
mdk sim --container --fail no_space      # todo guardado se rechaza como tarjeta llena
mdk sim --container --fail save_failed:1 # el siguiente guardado no se atiende; el de después sí
mdk sim --container --fail closed:1      # la consola cierra sin responder la conexión del siguiente guardado
mdk sim --container --stop-after 5       # SIGTERM a los 5 s, SIGKILL 3 s después
mdk sim --container --save-delay 2       # una tarjeta lenta
mdk sim --container --hold-saves --stop-when saving   # detenido con un guardado sin responder
mdk sim --container --stop-when saved    # detenido cuando la tarjeta ya tiene una partida
mdk sim --fresh                          # empezar con una tarjeta sin partida
```

No reproduce el sandbox (usuario, dispositivos, sistema de solo lectura,
contenido no ejecutable, límites de memoria y de tareas), la pantalla, el
sonido o los dispositivos de entrada, ni una tarjeta real. Un juego que
pasa en él sigue los contratos; si se ejecuta en una consola se establece
en una consola.

## Guardar desde C

```c
#include "mun.h"

mun_session *session;
mun_open(&session);

static char payload[MUN_SAVE_LOAD_MAX_BYTES];
size_t length;
mun_save_info info;
switch (mun_save_load(session, payload, sizeof payload, &length, &info)) {
case MUN_OK:      /* parse `payload`, a JSON object, by info.schema */ break;
case MUN_NO_SAVE: /* a new game */ break;
default:          /* unavailable or damaged: start without it */ break;
}

mun_save_result result;
if (mun_save_write(session, 1, "{\"level\":3}", 11, 25000, &result) == MUN_OK)
    show_saved();                       /* only now: the card holds it */
else
    show_not_saved(result.code);        /* "no_space", "card_removed", ... */
```

Qué significa un rechazo para el juego:

| `result.code` | Qué pasó | Qué hacer |
| --- | --- | --- |
| `no_space`, `card_removed`, `card_mismatch`, `card_unavailable`, `save_path_unsafe`, `write_failed`, `sync_failed`, `reader_unavailable` | La tarjeta, o el lector, no pudo aceptar la partida. La que tenía antes está intacta | Decírselo al jugador; el siguiente intento necesita que cambie la situación de la tarjeta |
| `save_failed`, `save_busy` | La consola no pudo atender esta petición (estaba ocupada con otro guardado, o no pudo pasar este). No se escribió nada | Pasajero: decir «no guardado» y ofrecer el guardado de nuevo en el siguiente punto de guardado del juego. No reintentar en bucle |
| `save_too_large`, `save_invalid` | La propia petición | Un fallo del juego: corregir los datos |

Dos cosas que un juego no ve como respuesta a un guardado, en MUN OS
posterior a v0.1.0-dev.5:

- Una sesión que no se pudo preparar termina antes de que el juego
  arranque, con el resultado de lanzamiento `prepare_failed`. El jugador
  vuelve al menú de la consola; no se ejecuta código del juego, así que no
  hay nada que tratar, y el simulador no lo produce.
- El servicio de tarjetas de la consola funciona dentro de un límite de
  memoria. La partida más grande que cabe en una tarjeta cabe de sobra en
  él. Si el servicio terminara mientras escribe, la tarjeta conserva su
  última partida completa, y al juego se le dice que el guardado no se hizo
  (un rechazo, o una conexión cerrada: `MUN_IO`).

Una conexión que la consola cierra sin responder es `MUN_IO`, y la falta de
respuesta a tiempo es `MUN_TIMEOUT`: las dos terminan la llamada, nunca una
espera sin fin, y las dos dejan el resultado sin conocer hasta que el
siguiente arranque lea la partida.

`mun_save_write` bloquea hasta que la consola responde: llámala fuera del
hilo que dibuja. `client/c/mun.h` documenta cada función, estado y regla.
Compila `mun.c` dentro del juego; no hay biblioteca compartida.

## Organización

```
mdk                    the host tool's entry point
mdk-gui                friendly desktop front-end (also: mdk gui)
tools/mdk/             its source (Python, standard library only)
tools/gui/             the desktop front-end (Tk; standard library only)
tools/env/             the build environment's definition
scripts/windows/       WSL setup and launch helpers for Windows ARM and x86
client/c/              mun.h, mun.c and the client's test program
mk/hardening.mk        the options a console program is compiled with
contracts/profiles/    what mdk checks a build against, per runtime profile
samples/hello-mun/     the native sample
samples/hello-mun-godot/   the same small game as a Godot project
engines/godot/         the Godot adapter, and how to fetch the pinned engine
tests/                 host tests; the sample's run in the environment
mun-os.lock.json       the MUN OS revision the devkit was checked against
LICENSE, LICENSES/     the licence texts; docs/licensing.md says which covers what
```

## Contribuir

Las correcciones, las pruebas, los ejemplos, las traducciones y los
informes de lo que pasó en tu ordenador son bienvenidos:
[contribuir](CONTRIBUTING.es.md) dice cómo viaja un cambio y con qué debe
llegar, y quien participa sigue el
[código de conducta](CODE_OF_CONDUCT.es.md). Las preguntas van en un issue
o en el canal de desarrolladores del [Discord de MUN](https://discord.gg/UxgExjjhxH); las decisiones
quedan en los issues. Un problema de seguridad va en privado al mantenedor
([seguridad](SECURITY.es.md)).

## Licencia

Tres licencias, según dónde acaba cada parte
([licencias](docs/licensing.md)):

- las herramientas, bajo la [Apache License 2.0](LICENSE);
- el cliente que un juego compila dentro de sí (`client/c`), bajo la Apache
  License 2.0 con las excepciones de LLVM, para que un juego lo distribuya
  sin tener que incluir nada;
- los ejemplos, los complementos para motores y lo que copia `mdk new`,
  bajo [MIT No Attribution](LICENSES/MIT-0.txt): tuyos para usarlos como
  quieras.

El devkit es libre para hacer, probar y distribuir juegos. Publicar en un
MUN Disk oficial es un servicio aparte, con su propio acuerdo, y los
nombres y logotipos de MUN y Play MUN no se licencian
([NAME-AND-LOGO.txt](NAME-AND-LOGO.txt)).
[docs/third-party.md](docs/third-party.md) enumera lo que usa el devkit.

Esta página es una traducción; si difiere de la [inglesa](README.md), vale
la inglesa.
