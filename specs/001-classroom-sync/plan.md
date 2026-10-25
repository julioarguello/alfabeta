# Implementation Plan: Los contenidos de cada asignatura, de Classroom al Drive de la familia

**Branch**: `docs/1-spec-001-classroom-sync` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-classroom-sync/spec.md`

## Summary

Una skill `classroom-sync` que Claude sigue en la app de escritorio, a demanda o programada cada día.
Claude abre Classroom en Chrome con la sesión escolar del alumno y ejecuta un extractor JavaScript de
solo lectura que descarga lo que ve como JSON. Una orden Python determinista (`python -m alfabeta`)
convierte esas capturas en un plan, recoge las descargas de los adjuntos, coloca las réplicas en la
carpeta del alumno dentro del Drive familiar montado y regenera la agenda. Claude solo aporta juicio
donde hace falta (emparejar temas del profesor con los del libro, detectar exámenes en anuncios) y lo
que la familia confirma queda guardado para no decidirse otra vez. La skill de Science Bits pasa a la
misma configuración y estructura.

## Technical Context

**Language/Version**: Python 3.12 (paquete y orden); JavaScript del navegador (extractor).

**Primary Dependencies**: ninguna en ejecución (biblioteca estándar: `tomllib`, `json`, `zoneinfo`,
`hashlib`, `argparse`, `fcntl`). Desarrollo: `uv`, `ruff`, `pyright` estricto, `pytest`, `jsonschema`
(validar contratos en las pruebas); Node con `jsdom` solo para probar el extractor.

**Storage**: ficheros. Configuración TOML por alumno en `~/.alfabeta/<alumno>/config.toml`; decisiones
JSON, estado JSON, registro JSON Lines, bloqueo, plan y capturas en `~/.alfabeta/<alumno>/datos/`;
réplicas y agenda en la carpeta del alumno dentro del Drive montado por Drive para escritorio.

**Testing**: `pytest` (unidad y contrato, contra páginas y capturas sintéticas); `node --test` con
`jsdom` para el extractor; el guardarraíl con casos en ambos sentidos. Ninguna prueba llama a
Classroom.

**Target Platform**: macOS con la app de escritorio de Claude, Chrome con la extensión de Claude y Drive
para escritorio.

**Project Type**: skills de Claude + una orden de línea de comandos local.

**Performance Goals**: sin objetivo de velocidad propio; el límite lo pone navegar como un alumno, una
clase cada vez. La duración de la primera sincronización (todo el curso) se mide en el spike S3.

**Constraints**: solo lectura en Classroom; ningún dato del alumno en URLs, registro ni repositorio;
escrituras idempotentes; ejecución programada sin intervención salvo sesión caducada, desafío,
Drive sin montar o decisiones pendientes.

**Scale/Scope**: un alumno (diseño para varios), unas 12 clases, cientos de elementos por curso.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cómo lo cumple el plan | Estado |
|---|---|---|
| I. El alumno es configuración | `--alumno <id>` (alias opaco) elige una carpeta `~/.alfabeta/<id>/`; el código no conoce alumnos, centros, cursos ni cuentas. El `build.py` existente de Science Bits trae por defecto un curso, una asignatura y un tema concretos: T057 los quita y hace obligatoria su configuración | Excepción temporal hasta T057 (ver Complexity Tracking) |
| II. Tres capas | `config/template.toml` en el repo; `config.toml` fuera; decisiones, estado y demás datos en `datos/`; validación de claves contra la plantilla; guardarraíl en pre-commit y CI con autocomprobación | Cumple |
| III. Datos de menores | Nada personal en URLs (la cuenta se localiza por índice `/u/<n>`, comparando el correo en local), en el registro (ids opacos, rutas relativas, nunca la ruta absoluta de la raíz) ni en el repositorio: las páginas de prueba son sintéticas (solo la estructura de las reales; todo texto y atributo inventado). No se guardan comentarios ni nombres de compañeros. Las notas, correcciones y entregas del alumno se guardan porque son su material de estudio y van a una carpeta de la familia, no a terceros | Cumple |
| IV. Solo lectura | El extractor solo lee el DOM; navega solo a inicio, «Trabajo de clase», tablón y detalle; nunca sigue formularios ni cuestionarios ni pulsa el panel «Tu trabajo» (prueba con `jsdom` que lo comprueba); detecta desafíos anti-robot y se detiene; al menos 2 s entre páginas. Leer la página de detalle de una pregunta no es abrir un cuestionario: abrirlo es responderlo o seguir su formulario, y S3 comprueba que leerla no cambia nada (si cambiara, las preguntas se leen solo del listado) | Cumple |
| V. Idempotente e incremental | Identificador de Classroom por elemento, huella por réplica, comparación antes de escribir (también la agenda, que no depende del día), versiones anteriores conservadas, nada se borra, bloqueo por alumno y del navegador del Mac con `fcntl.flock` durante toda la ejecución, renovado en cada paso y liberado solo por inactividad. Las capturas, el plan y la línea de registro de una ejecución son su propio registro (la excepción que permite V); estado y decisiones no se reescriben si no cambian, y la fecha de la última revisión completa se toma del registro, no del estado | Cumple |
| VI. Proveedor aislado y probado | Puerto `Fuente` común: `FuenteClassroom` (capturas) y `FuenteLibro` (directorio de un proveedor de libro); la subcarpeta sale del nombre de la fuente; añadir otro libro no toca `ubicacion` ni `replicas`. Extractor de Classroom probado con `jsdom` sobre páginas sintéticas y lógica con `pytest`. Excepción registrada: los extractores ya existentes de Science Bits siguen sin pruebas (Complexity Tracking) | Cumple con excepción registrada |
| VII. Salidas opcionales | La carpeta del Drive es la salida base; el calendario queda para la épica 2. El cuaderno de Science Bits sigue como hoy (activado o no por configuración) y su resultado, también un fallo, queda en el registro con `registro cuaderno`; si falla, lo colocado en el Drive no se toca | Cumple |
| VIII. `Europe/Madrid` | Un único resolvedor de fechas con `zoneinfo`; año del curso escolar; pruebas en cambios de hora y de año | Cumple |
| IX. Simplicidad | Sin dependencias en ejecución (la validación de capturas en ejecución comprueba claves a mano); ficheros en vez de base de datos; `jsonschema`, Node y `jsdom` solo en desarrollo (ver Complexity Tracking); `uv`, ya adoptado para el entorno, solo prepara el entorno y lanza la orden en el Mac, sin bibliotecas nuevas | Cumple con justificación |

Re-evaluado tras la Fase 1 y tras el primer `/speckit-analyze` (2026-10-25): III, IV, V, VI y IX
corregidos como arriba.

## Project Structure

### Documentation (this feature)

```text
specs/001-classroom-sync/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli.md
│   ├── config-template.toml
│   ├── captura.schema.json
│   └── agenda.schema.json
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml   uv.lock   .python-version   pyrightconfig.json   Makefile   package.json
CONTRIBUTING.md
config/
└── template.toml                   # única capa de configuración en el repo
.githooks/pre-commit                # llama al guardarraíl
src/alfabeta/
├── __main__.py                     # orden y subcomandos (contracts/cli.md)
├── configuracion.py                # carga y validación contra la plantilla; rutas del alumno
├── decisiones.py                   # propuestas, confirmaciones, correcciones y cambios
├── fechas.py                       # año del curso, relativas respecto a la captura, Europe/Madrid
├── modelo.py                       # dataclasses del dominio
├── fuentes.py                      # Protocol Fuente; FuenteClassroom y FuenteLibro
├── captura.py                      # lee y comprueba capturas del extractor y las normaliza
├── clasificacion.py                # categoría de cada elemento y candidatos a examen
├── ubicacion.py                    # curso/asignatura/tema|mes/fuente y nombres de fichero
├── estado.py                       # estado JSON, registro JSON Lines, bloqueo con fcntl.flock
├── plan.py                         # diferencia fuentes ↔ estado: qué descargar, escribir, decidir
├── descargas.py                    # recogida de la carpeta de descargas y verificación
├── replicas.py                     # colocar réplicas, notas, correcciones, versiones anteriores
├── agenda.py                       # agenda.json y agenda.md («Pendiente» y «Hecho»)
├── anonimizar.py                   # páginas sintéticas a partir de la estructura de las reales
├── libro.py                        # `libro colocar`
├── prueba.py                       # `prueba preparar` y `prueba descargar`: alumno inventado para pruebas y quickstart
├── guardarrail.py                  # detector de datos personales con autocomprobación
└── esquemas/                       # captura y agenda (copias de contracts/) para pruebas y documentación
skills/
├── classroom-sync/
│   ├── SKILL.md                    # el flujo que sigue Claude y sus prohibiciones
│   └── scripts/extract.js          # extractor de solo lectura
└── sciencebits-a-notebooklm/       # pasa a la configuración por alumno y a `libro colocar`
tests/
├── fixtures/classroom/             # páginas sintéticas + capturas JSON inventadas
├── js/extract.test.mjs             # extractor contra las páginas sintéticas
└── test_*.py                       # una por módulo, más guardarraíl y contratos
.github/workflows/ci.yml            # autofix (no bloquea) + quality-gate (bloquea): make ci
```

**Structure Decision**: un solo proyecto. Un paquete en `src/` con la lógica determinista compartida
por las dos skills, que solo contienen el `SKILL.md` y el JavaScript del navegador. `src/` y `tests/`
quedan bajo ruff y Pyright sin excepciones; el JavaScript de `classroom-sync` bajo `node --test`. Los
scripts que ya tiene la skill de Science Bits quedan fuera de esas puertas en esta épica (Complexity
Tracking).

## Class design (por capas)

Hechos de los que parte el diseño (detalle en [research.md](research.md#hechos-observados)):

| Hecho | De dónde sale |
|---|---|
| El estado fiable de una tarea está en su detalle, no en el listado | Observado 2026-10-25, Classroom del alumno, solo lectura |
| Los temas del profesor y los del libro no coinciden uno a uno | Observado 2026-10-25, «Trabajo de clase» de una asignatura con libro |
| Las fechas no llevan año y pueden ser relativas | Observado 2026-10-25, «Trabajo de clase» de dos asignaturas |
| La URL de detalle lleva ids estables de clase y elemento | Observado 2026-10-25, barra de direcciones |
| El listado muestra «Última modificación» cuando un elemento se edita | Observado 2026-10-25, «Trabajo de clase» |
| Los adjuntos enlazan a `drive.google.com`; la descarga directa falló | Observado 2026-10-25 y prueba previa de la issue #1 |
| Los exámenes se anuncian en el tablón, en el idioma de la clase | Observado 2026-10-25, tablón de una asignatura con libro |
| La interfaz de Classroom de la cuenta del alumno está en castellano | Observado 2026-10-25, todas las páginas visitadas |
| La extensión oculta en su salida valores con aspecto de base64 | Observado 2026-10-25, salida de la herramienta de JavaScript |

| Capa | Nombre | Responsabilidad |
|---|---|---|
| Navegador | `extract.js` | Lee la lista de clases, temas, elementos, detalle (estado, fechas, marca de modificación, adjuntos, entrega, corrección) y tablón tal como se muestran; marca la captura como completa o no; detecta desafíos anti-robot y etiquetas de interfaz inesperadas; espera ≥2 s entre páginas; descarga el resultado como JSON |
| Navegador | Claude + `SKILL.md` | Localiza la cuenta escolar, ejecuta el extractor, descarga adjuntos según el plan, propone emparejamientos (con seguridad) y exámenes |
| Dominio | `Alumno`, `Asignatura`, `Elemento`, `Adjunto`, `Replica`, `EntradaAgenda`, `Correccion`, `Decision`, `Ejecucion` | Dataclasses inmutables (ver data-model) |
| Dominio | `Clasificador` | Categoría cerrada con precedencia y candidatos a examen por indicios |
| Dominio | `Ubicador` | Carpeta y nombre de cada réplica a partir de curso, asignatura, emparejamiento confirmado o mes, fuente y papel |
| Dominio | `ResolvedorFechas` | Fecha absoluta en `Europe/Madrid` desde el texto mostrado, el curso escolar y el momento de la captura |
| Puertos | `Fuente` | Protocol: `nombre` (la subcarpeta) y `elementos()` normalizados para `Planificador`; implementaciones `FuenteClassroom` (capturas) y `FuenteLibro` (directorio de un proveedor de libro) |
| Puertos | `AlmacenEstado`, `AlmacenDecisiones`, `CarpetaAlumno`, `BandejaDescargas` | Protocols: estado y decisiones, escritura en la carpeta del Drive, recogida de la carpeta de descargas |
| Servicios | `Planificador` | Fuentes + estado + decisiones → plan (descargas pedidas, réplicas a escribir, decisiones pendientes) |
| Servicios | `Aplicador` | Plan + descargas recogidas → réplicas, notas, correcciones, versiones anteriores, estado y registro |
| Servicios | `GeneradorAgenda` | Estado + decisiones → `agenda.json` y `agenda.md`, reescritos solo si cambian |
| Adaptadores | ficheros JSON, carpeta montada, carpeta de descargas | Implementan los puertos con escritura atómica |
| Entrada | `python -m alfabeta` | Resuelve el alumno una vez, valida la configuración, toma o comprueba el bloqueo y llama a los servicios |
| Puerta | `Guardarrail` | Detectores de datos personales, autocomprobación y salidas 0/1/2/3 (contracts/cli.md) |
| Puerta | `Anonimizador` | Convierte una página real en sintética: conserva etiquetas, clases CSS y etiquetas de interfaz de una lista permitida, e inventa todo texto y atributo restante; se niega a escribir si sobrevive cualquier texto de la entrada fuera de esa lista |

## Flujo de una ejecución

1. `python -m alfabeta bloqueo tomar --alumno <id> --modo <interactiva|programada>` (su `ejecucion` va en `ALFABETA_EJECUCION` en cada orden siguiente) y `config comprobar --alumno <id>`: bloqueos del
   alumno y del navegador tomados para toda la ejecución, configuración válida, Drive montado. Si `bloqueo tomar`
   falla, él mismo escribe su línea; si falla otra cosa, `registro detener` con su motivo y aviso a la familia. Todas las órdenes corren en el Mac
   con `uv run --project <herramientas.repositorio> python -m alfabeta`, y la skill llama a
   `descargas recoger` tras la lista de clases, tras cada clase y tras cada tanda de descargas (cada
   orden renueva el bloqueo; `bloqueo renovar` queda para las esperas largas).
2. Claude abre Classroom en Chrome, localiza la cuenta escolar por su índice y comprueba la sesión y
   el idioma de la interfaz. Si la sesión caducó, hay un desafío o la interfaz no es la esperada,
   `registro detener` con su motivo y aviso (FR-021a).
3. Captura la lista de clases; `descargas recoger` y `plan` dan las clases sin asociar. Claude propone
   sus asociaciones con `decisiones proponer`; en una ejecución interactiva la familia las confirma en
   ese momento, en una programada quedan pendientes y esas clases no se sincronizan todavía.
4. Por cada clase asociada, ejecuta `extract.js` con el `ejecucion` en curso, que descarga la captura;
   `descargas recoger` la mueve a `datos/capturas/`. Si a mitad caduca la sesión, aparece un desafío o la
   interfaz no es la esperada, el extractor descarga una captura `parada` con `clase` y se pasa al paso 7
   con las clases ya capturadas (`parcial`).
5. `plan --alumno <id>`: escribe `datos/plan.json` con las descargas que hacen falta, las decisiones
   pendientes y lo que cambiaría. Claude propone emparejamientos y exámenes detectados (con motivo y
   seguridad); en una ejecución interactiva la familia confirma los emparejamientos, y los exámenes
   detectados entran en la agenda sin confirmación.
6. Claude descarga cada adjunto pedido (método del spike S1), por las tandas del plan y con al menos 2 s
   entre descargas; `descargas recoger` tras cada tanda los verifica.
7. `aplicar --alumno <id>`: recalcula los destinos con las decisiones vigentes, coloca réplicas,
   actualiza estado y registro, regenera la agenda si cambia e imprime el resumen para la familia.
   `bloqueo soltar` al final; si la ejecución muere, el bloqueo se libera por inactividad.

## Science Bits en la misma estructura (FR-022, FR-023)

- La skill lee `~/.alfabeta/<alumno>/config.toml` en lugar de `~/.alfabeta/config.json`: `[[asignaturas]]`
  con `libro = "sciencebits"` y `clase_libro`, el curso escolar de `[alumno]`, `[sciencebits] url`,
  `[herramientas] carpeta` (en lugar de la carpeta de herramientas en Dropbox) y `[cuaderno]` (en
  lugar de `notebook.*`). Ninguna clave fuera de la plantilla, y la skill nunca escribe en la
  configuración: si falta o no es válida, `config comprobar` y para.
- Toma el bloqueo del alumno y del navegador (`bloqueo tomar --modo interactiva`, o `programada` si la lanza una tarea programada) antes de abrir Science Bits y lo suelta
  al terminar, para no coincidir con una sincronización de Classroom en el navegador ni en las
  descargas (FR-030).
- «El siguiente tema» sale de las carpetas `Tema NN` que ya tienen `sciencebits/` en el Drive; no hay
  que añadir nada a la configuración.
- Su resultado (`TemaNN_<LANG>.pdf` y `.md`) se sigue generando como hoy en la carpeta de trabajo de
  Descargas, y `libro colocar` lo pasa por `FuenteLibro` a `<curso>/<asignatura>/<Tema NN - título>/<libro>/`
  dentro de la raíz del Drive (la subcarpeta es el valor de `libro`), con las mismas reglas de huella
  y versión anterior que Classroom.
- No lee ni escribe en Dropbox; lo capturado allí antes queda como está.
- El cuaderno de Gemini Notebook sigue como hoy, activado o no con `[cuaderno] activado`, hasta la
  épica 3. En el paso de `nlm` la skill lista las fuentes del cuaderno y solo añade las que faltan (constitución V:
  repetir un tema no duplica fuentes). Tras ese paso, la skill llama a `registro cuaderno` con su resultado (`creado`,
  `sin_cambios`, `fallo` con motivo o `desactivado`): un fallo del cuaderno no deshace lo colocado y se
  ve en el registro (constitución VII).

## Spikes antes de las tareas de implementación

- **S1 · Descarga de adjuntos de Drive** desde Chrome con la cuenta escolar: los tres métodos de
  research R4, con un adjunto real. Sale el método y su prueba manual en quickstart.
- **S2 · Tarea programada con navegador y descargas**: una tarea programada de la app que abra Chrome
  con la extensión, lea el título de Classroom y descargue un fichero (una captura y un adjunto) sin
  que nadie apruebe nada en ese momento. Si no puede, la ejecución programada queda en el modo
  reducido que admite FR-021a (aviso y sincronización con la orden única).
- **S3 · Estructura real y páginas sintéticas**: guardar las páginas reales de una clase fuera del
  repositorio, generar con `anonimizar` sus versiones sintéticas, comprobar con el guardarraíl que no
  queda nada real, comprobar que la página de detalle de una pregunta se puede leer sin crear estado,
  y medir cuánto tarda una clase completa.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Node y `jsdom` como dependencias de desarrollo (IX) | La constitución exige probar cada extractor contra páginas guardadas y el extractor es JavaScript | Reimplementar la extracción en Python duplicaría la lógica y no probaría el código que corre en el navegador |
| `jsonschema` como dependencia de desarrollo (IX) | Las pruebas comprueban capturas y agendas contra los contratos completos | Comprobar a mano todo el esquema en las pruebas repetiría el contrato en código; en ejecución sí se comprueban a mano las claves imprescindibles, sin dependencia |
| Valores por defecto de un curso, una asignatura y un tema concretos en el `build.py` existente de Science Bits (I), hasta T057 | Están en `main` desde antes de esta spec; T057, en la fase de US4, los quita | Quitarlos en el PR de la spec mezclaría código con un PR solo de documentación (Flujo) |
| Extractores y scripts existentes de Science Bits sin pruebas ni puertas de calidad (VI, Flujo) | Esta épica solo cambia de dónde lee la configuración y dónde coloca el resultado esa skill; probar su captura exige páginas sintéticas de Science Bits | Hacerlo aquí duplicaría el alcance de la épica. Queda como issue de seguimiento («pruebas y puertas para la skill de Science Bits»), que se abre con las de esta spec |
