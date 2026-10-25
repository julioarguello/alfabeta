---

description: "Tareas de la spec 001: Classroom → Drive familiar, con configuración por alumno"
---

# Tasks: Los contenidos de cada asignatura, de Classroom al Drive de la familia

**Input**: `specs/001-classroom-sync/` (plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md)

**Tests**: obligatorios. La constitución exige pruebas de cada extractor contra páginas guardadas con
datos inventados (VI) y un guardarraíl con casos que demuestren que salta (II); la puerta de cada PR
incluye `ruff`, `pyright`, `pytest` y el guardarraíl.

**Organization**: por historia de usuario; cada fase es un corte vertical que deja el paquete coherente
y demostrable, y cada PR pasa `make ci`. Las issues se abren tras aprobar el PR de la spec; cada fase
dirá entonces la suya.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (ficheros distintos, sin dependencias pendientes)
- **[Story]**: historia de la spec (US1…US6)

---

## Phase 0: PR de la spec

- [ ] T000 Antes del commit de la constitución en el PR de la spec, copiar el bloque «Sync Impact Report» de `.specify/memory/constitution.md` a la descripción del PR (Governance) y borrarlo del fichero, y pasar un escaneo de datos personales sobre `specs/`, `.specify/` y la historia publicada (`git log --all -p`) (el guardarraíl aún no existe: búsqueda de los valores de la configuración privada, sin mostrarlos; anotar en el PR el resultado, sin los valores), y nombrar en el PR las puertas que no corren porque aún no hay código (ruff, Pyright, pytest, guardarraíl)

---

## Phase 1: Setup

**Purpose**: proyecto Python y de pruebas listo, con la puerta única `make ci` en verde desde el primer PR.

- [ ] T001 Crear `pyproject.toml` (proyecto `alfabeta`, `requires-python = ">=3.12"`, sin dependencias de ejecución, grupo `dev` con `ruff`, `pyright`, `pytest` y `jsonschema`, `[tool.uv] package = true`, paquete en `src/alfabeta/`), `.python-version` con `3.12` y `uv.lock` con `uv lock`
- [ ] T002 [P] Configurar ruff en `pyproject.toml` (`target-version = "py312"`, `line-length = 120`, comillas dobles, docstrings Google; `select` E W F I B C4 SIM UP RUF D TC ANN; `ignore` E501 D100 D104 D107 ANN401; `tests/**` sin ANN, D, RUF001, RUF012, RUF043, RUF059, TC, SIM) con `src = ["src", "tests"]` y `extend-exclude = ["skills/sciencebits-a-notebooklm"]` (excepción de Complexity Tracking), y pytest (`testpaths = ["tests"]`, `python_files = ["test_*.py"]`, `addopts = "-v --tb=short"`)
- [ ] T003 [P] Crear `pyrightconfig.json` único en la raíz: `pythonVersion` "3.12", `typeCheckingMode` "strict", `venvPath` ".", `venv` ".venv", `include` ["src", "tests"], `reportMissingTypeStubs` false, `executionEnvironments` para `src` y `tests` (este último con `reportPrivateUsage` "none")
- [ ] T004 [P] Crear `package.json` con `jsdom` como única dependencia de desarrollo y el script `test` = `node --test tests/js/`; generar `package-lock.json`; crear `tests/js/humo.test.mjs` que carga `jsdom`
- [ ] T005 Crear `src/alfabeta/__init__.py` (versión), `src/alfabeta/__main__.py` mínimo con argparse, la opción global `--inicio` y `--version`, y `tests/test_humo.py` que lo ejecuta; así la puerta recoge pruebas desde el primer PR
- [ ] T006 Crear `Makefile` con `setup-python` (`uv lock --check`, `uv sync --locked`), `setup-node` (`npm ci`) y `ci` (`ruff check`, `ruff format --check`, `pyright`, `pytest` que falla si recoge cero pruebas, `npm test`), cada paso nombrado en la salida; todas las recetas con el intérprete de `.venv`. El paso del guardarraíl lo añade T014: el PR de la fase 1 nombra esa puerta como omitida hasta entonces
- [ ] T007 [P] Crear `.github/workflows/ci.yml` con dos jobs sin `needs:` entre ellos ni filtro `paths:`: `autofix` (ruff `--fix` y formato, no bloquea) y `quality-gate` (setup-uv con caché, `python-version-file: .python-version`, Node, `make setup-python setup-node ci`, bloquea)
- [ ] T008 [P] Ampliar `.gitignore` con `.venv/`, `node_modules/`, `.pytest_cache/` y `*.local.*`
- [ ] T009 [P] Crear `CONTRIBUTING.md` en castellano: preparar el entorno (`make setup-python setup-node`), la puerta `make ci`, Pyright estricto como único comprobador de tipos, y la regla de que en `tests/fixtures/` solo entran páginas sintéticas generadas con `anonimizar`

---

## Phase 2: Foundational (bloquea todas las historias)

**Purpose**: los tres spikes, el guardarraíl, el anonimizador, la configuración por alumno, el dominio,
fechas, estado, bloqueo, fuentes, ubicación y la orden.

**⚠️ CRITICAL**: ninguna página guardada entra en el repositorio antes de T013–T016.

### Spikes (resultados en `specs/001-classroom-sync/research.md`)

- [ ] T010 Spike S1: con la cuenta escolar en Chrome y un adjunto real, probar en orden `drive.usercontent.google.com/download?id=<id>&export=download&authuser=<n>`, la exportación `docs.google.com/<tipo>/d/<id>/export?format=pdf&authuser=<n>` y el botón de descarga del visor; anotar en research R4 el método que deja el fichero completo en la carpeta de descargas, para ficheros y para Documentos/Presentaciones/Hojas de Google
- [ ] T011 Spike S2: crear una tarea programada de prueba en la app que abra Classroom en Chrome, lea el título y descargue un fichero sin aprobación en ese momento, y comprobar con un proceso desacoplado de prueba (no hace falta `bloqueo tomar`, que aún no existe) que un proceso que arranca una llamada de herramienta de Claude sobrevive a esa llamada; anotar el resultado en research R1 y, si no sobrevive, aplicar la alternativa de research R6 en T024–T025 y borrar la tarea de prueba
- [ ] T012 Spike S3: guardar el HTML de la página de inicio, «Trabajo de clase», una página de detalle de tarea, una de material, una de pregunta y el tablón de una clase real en `~/.alfabeta/<alumno>/datos/capturas-crudas/` (fuera del repo); comprobar que leer el detalle de una pregunta no cambia «Tu trabajo»; anotar si el detalle de una tarea muestra alguna marca de modificación y los patrones de URL de elementos y adjuntos; decidir y anotar en research R3 cómo recorre el extractor las páginas sin perder el script inyectado; anotar en research R8 la lista de etiquetas de interfaz observadas y cuánto tarda una clase completa, y fijar con esa medida el valor de `bloqueo_inactividad_minutos` en `contracts/config-template.toml` y `config/template.toml` a la vez (más largo que el tramo más largo sin renovar de cualquiera de las dos skills, la de Classroom y la de Science Bits)

### Guardarraíl y anonimizador (constitución II y III; FR-005)

- [ ] T013 [P] Escribir `tests/test_guardarrail.py`: casos que deben saltar, construidos en tiempo de ejecución para que el propio fichero de pruebas no dispare el guardarraíl (correo, ruta de usuario de macOS, id con forma de Classroom, de Drive y de cuaderno (UUID), y el `id`, `nombre_visible`, `cuenta`, `raiz` y `clase_classroom` de una configuración de prueba en un `--inicio` temporal, y un id de clase guardado en su `datos/decisiones.json`), y casos que no (plantilla `config/template.toml`, correos `example.org`/`example.com`, rutas relativas, marcadores `<…>`, ids sintéticos `sint-<n>`, hashes de `uv.lock` y `package-lock.json`, identificadores de código largos en `snake_case` o `camelCase` y nombres de fichero de prueba, valores no identificativos como `curso_escolar` e `idiomas`); `--historia` encuentra un dato plantado en un commit de un repositorio temporal y ya borrado del árbol; `--todo` sin ficheros que revisar sale con 2 y `--cambios` sin ficheros sale con 0 y aviso; sin configuraciones locales, aviso en stderr y salida 0 con los genéricos; fichero y línea en la salida sin repetir el dato
- [ ] T014 Implementar `src/alfabeta/guardarrail.py` y el subcomando `guardarrail [--cambios | --todo | --historia]` según `contracts/cli.md` y research R13: detectores genéricos (correo, ruta de usuario, ids con forma de Classroom, Drive o cuaderno) y nominales (solo claves identificativas de las configuraciones locales y los ids de Classroom y Drive de sus `datos/decisiones.json` y `datos/estado.json`), autocomprobación que planta un defecto por detector en memoria en cada ejecución, salidas 0 · 1 · 2 (los genéricos no revisaron ningún fichero) · 3 (detector ciego); añadir `guardarrail --todo` como paso de `make ci` en `Makefile`
- [ ] T015 Añadir el gancho `.githooks/pre-commit` que llama a `python -m alfabeta guardarrail --cambios`, la receta `make setup-hooks` que lo copia a `.git/hooks/pre-commit` y de la que depende `make setup-python` (el entorno no queda preparado sin el gancho); `make ci` fuera de la integración continua falla si `.git/hooks/pre-commit` no es igual a `.githooks/pre-commit`; y el apartado del guardarraíl y de `make setup-hooks` en `CONTRIBUTING.md`
- [ ] T016 Implementar `src/alfabeta/anonimizar.py` y el subcomando `anonimizar <entrada> <salida>`: genera una página sintética que conserva etiquetas HTML, clases CSS, jerarquía y las etiquetas de interfaz de la lista permitida (la anotada en T012), e inventa todo texto y atributo restante (títulos, descripciones, fechas, nombres de fichero, textos accesibles) con valores estables, y los ids con la forma `sint-<n>` en la misma posición de la URL; sale con 1 y no escribe si sobrevive cualquier texto de la entrada fuera de la lista o si el guardarraíl encuentra algo; prueba en `tests/test_anonimizar.py` con una página inventada que planta un título, un nombre y un id

### Configuración por alumno (FR-001…FR-004; contracts/config-template.toml)

- [ ] T017 [P] Copiar el contrato a `config/template.toml` y borrar `config.example.json`
- [ ] T018 [P] Escribir `tests/test_configuracion.py`: clave que falta, que sobra, que cambia de tipo o que contiene `changeme` en cualquier parte del valor → error que nombra la clave y no muestra el valor; `drive.raiz` igual a la raíz de «Mi unidad» o inexistente → error sin mostrar la ruta; `--inicio` inexistente → error sin crearlo; `datos/` o `herramientas.carpeta` dentro de `drive.raiz` → error
- [ ] T019 Implementar `src/alfabeta/configuracion.py` y el subcomando `config comprobar`: carga con `tomllib`, compara el conjunto de claves y tipos con `config/template.toml`, rechaza valores que contienen `changeme`, resuelve las rutas del alumno (`config.toml`, `datos/`) desde `--inicio` y el `id` del alumno («minúsculas ASCII»)
- [ ] T020 [P] Escribir `tests/test_template_cubre_lecturas.py`: toda clave que lee `src/alfabeta/` existe en `config/template.toml` (recorrido del AST de los accesos a la configuración), con control positivo: sobre un módulo de prueba con N accesos conocidos encuentra los N, y una clave no declarada plantada en él hace fallar la comprobación (no se compara con el número de claves de la plantilla: algunas solo las leen las skills)

### Dominio, fechas, estado, bloqueo, fuentes y ubicación

- [ ] T021 [P] Implementar `src/alfabeta/modelo.py` con las dataclasses inmutables de data-model.md: `Alumno`, `Asignatura`, `Decision` (`tipo` ∈ `clase_asociada` · `emparejamiento_tema` · `emparejamiento_elemento` · `examen_detectado` · `candidato_descartado` · `correccion_examen` · `numero_tema_profesor`; clave `(tipo, origen)`; `seguridad` ∈ `alta` · `media` · `baja`; `estado` `propuesta` → `confirmada` · `rechazada`, `confirmada` o `rechazada` → `sustituida`), `Elemento` (`tipo` ∈ `tarea` · `material` · `pregunta` · `anuncio`; `estado` ∈ `pendiente` · `entregada` · `devuelta` · `vencida` · `falta_segun_profesor` · vacío), `Adjunto` (`clase_adjunto` ∈ `fichero` · `documento_google` · `video` · `enlace` · `formulario`; «los tres últimos no se descargan»), `Replica`, `Correccion`, `EntradaAgenda` (`categoria` ∈ `examen` · `entrega` · `cuestionario` · `material` · `aviso`, «exactamente una»), `Ejecucion`
- [ ] T022 [P] Escribir `tests/test_fechas.py` con tabla de casos: «13 oct» en un curso 2026-2027 → 2026; «14 ene» → 2027; «Mañana, 8:00», «Hoy» y día de la semana resueltos respecto a `capturado`, también para una captura aplicada al día siguiente; «Fecha de entrega: 19 oct, 8:00»; cambio de hora de octubre y de marzo; «Última modificación» nunca se toma como publicación
- [ ] T023 Implementar `src/alfabeta/fechas.py` (`ResolvedorFechas`): textos de Classroom en castellano → fecha o fecha-hora en `Europe/Madrid` con `zoneinfo`, año desde el curso escolar (septiembre a diciembre, primer año; enero a agosto, segundo), relativas respecto al momento de la captura
- [ ] T024 [P] Escribir `tests/test_estado.py`: escritura atómica; no se reescribe si no cambia; `bloqueo tomar --modo` guarda el modo y devuelve un identificador de ejecución; `bloqueo tomar` impide un segundo `bloqueo tomar` del mismo alumno o de otro (bloqueo del navegador; salida 1, motivo `bloqueo_ocupado`, una sola línea `detenida`); una segunda ejecución no puede usar ni soltar el bloqueo de la primera (otro `ALFABETA_EJECUCION` → salida 1); sin `ALFABETA_EJECUCION`, los subcomandos que exigen el bloqueo salen con 1; `bloqueo tomar` y `registro detener` funcionan con una configuración cuyo `[sincronizacion]` es válido aunque falle otra clave o falte el Drive; cada subcomando lo renueva; sin renovación durante `bloqueo_inactividad_minutos` (reloj simulado) el vigilante lo suelta solo y escribe `detenida` con motivo `inactividad`; si muere el vigilante, el sistema libera los `flock`; `registro detener` escribe su línea con cada motivo de la lista (incluidos `bloqueo_no_tomado` y `configuracion_invalida`) y rechaza uno que no está; una línea JSON por ejecución en `registro.jsonl` sin el nombre ni el correo del alumno
- [ ] T025 Implementar `src/alfabeta/estado.py` (`AlmacenEstado`, registro JSON Lines) y los subcomandos `bloqueo tomar` / `bloqueo renovar` / `bloqueo soltar` (bloqueo del alumno y del navegador del Mac con `fcntl.flock` en un proceso vigilante que se libera por inactividad) y `registro detener` (research R6, contracts/cli.md)
- [ ] T026 [P] Implementar `src/alfabeta/fuentes.py`: Protocol `Fuente` (`nombre`, `elementos()`); `FuenteClassroom` y `FuenteLibro` se completan en US1 y US4
- [ ] T027 [P] Escribir `tests/test_ubicacion.py`: tema emparejado y confirmado → `<curso>/<asignatura>/Tema NN - <título>/<fuente>/`; tema del profesor sin libro → `Tema PNN - <título del profesor>` con `NN` = su orden en «Trabajo de clase» la primera vez que se ve, que no cambia si el profesor reordena los temas; sin tema o sin confirmar → `<AAAA-MM>/<fuente>/` por fecha de publicación; material de un fichero → `AAAA-MM-DD - <título>.<ext>`; material con varios ficheros, con enlaces o con descripción → carpeta con sus ficheros, `descripcion.md` si tiene texto y `enlaces.md` si tiene enlaces; tarea o pregunta → siempre carpeta con `enunciado - <nombre>` y `enunciado.md` con las instrucciones o la pregunta; material sin ficheros ni enlaces, solo con texto → nota `.md` (aunque tenga descripción); material sin ficheros y con enlaces → carpeta con `descripcion.md` y `enlaces.md`; tema del profesor rechazado como emparejamiento → `Tema PNN`, con `NN` fijado en la ejecución que coloca por primera vez algo de ese tema (un reordenamiento posterior no lo cambia); elemento con un `emparejamiento_elemento` confirmado → ese tema del libro, aunque su tema diga otra cosa; aviso → nota `AAAA-MM-DD - aviso - <primeras palabras, 60 caracteres>.md`, o carpeta con la nota y los adjuntos si los tiene; nombres válidos en Drive, de 255 bytes UTF-8 como máximo y únicos sin perder elementos
- [ ] T028 Implementar `src/alfabeta/ubicacion.py` (`Ubicador`) según FR-012…FR-015c
- [ ] T029 Crear en `tests/fixtures/classroom/` capturas JSON inventadas con un `ejecucion` inventado, que `prueba descargar --capturas` sustituye (lista de clases y dos clases: temas, elementos de todos los tipos, adjuntos de todas las clases, una tarea entregada, una devuelta, una marcada como falta, una con «Última modificación», un anuncio de examen en castellano y otro en un segundo idioma de la clase), válidas según `contracts/captura.schema.json`, y copiar los esquemas a `src/alfabeta/esquemas/`; prueba en `tests/test_contratos.py` con `jsonschema` y otra que comprueba que las copias, y `config/template.toml`, son idénticas byte a byte a `contracts/`
- [ ] T030 Implementar `src/alfabeta/prueba.py` y el subcomando `prueba preparar`: exige `--inicio` explícito y crea allí el alumno `prueba` con configuración inventada válida, `drive/` como raíz con una carpeta `Tema 01 - <título inventado>/sciencebits/` en una asignatura con libro, `descargas/` vacía y las capturas de T029 en `capturas-prueba/`; implementar también `prueba descargar --capturas`, que las copia a `descargas/` con el `ejecucion` en curso, como las dejaría el extractor (los adjuntos y las decisiones los añade T039)

**Checkpoint**: `make ci` en verde con configuración, fechas, estado, bloqueo, ubicación y guardarraíl; spikes anotados.

---

## Phase 3: User Story 1 - Lo que publica el profesor, en la carpeta de su tema o de su mes (P1) 🎯 MVP

**Goal**: una asignatura sincronizada: materiales y enunciados de tareas replicados con la fecha delante,
enlaces anotados, temas sin emparejar esperando en su mes.

**Independent Test**: quickstart escenario 2.

### Tests for User Story 1

- [ ] T031 [P] [US1] Generar con `anonimizar` las páginas sintéticas de S3 y guardarlas en `tests/fixtures/classroom/paginas/` (inicio, listado, detalle de tarea, de material y de pregunta, tablón), con su fecha y el tipo de página de origen, sin ids ni rutas del alumno, en `tests/fixtures/classroom/README.md`; añadir una página sintética de desafío anti-robot y una con etiquetas de interfaz en otro idioma
- [ ] T032 [P] [US1] Escribir `tests/js/extract.test.mjs`: con `jsdom` sobre las páginas sintéticas, `extract.js` devuelve capturas `clases` y `clase` con las claves del contrato; los comentarios de clase, los comentarios privados y el autor que llevan plantados las páginas de detalle no aparecen en la captura; temas en orden, `texto_fecha_listado` literal, «Sin tema» como `tema: null`, adjuntos por `clase_adjunto` y `completa: true`; con la página de desafío devuelve `parada` con motivo `desafio`; con la de otro idioma, `interfaz_inesperada`
- [ ] T033 [US1] Escribir en `tests/js/extract.test.mjs` la prueba de solo lectura: escuchas de clic, envío de formularios y navegación en las páginas sintéticas; el extractor no pulsa ningún botón del panel «Tu trabajo», no envía nada, no navega a formularios ni cuestionarios y espera al menos 2 s entre navegaciones (reloj simulado)
- [ ] T034 [P] [US1] Escribir `tests/test_captura.py`: normalización de las capturas de T029 a `Elemento` y `Adjunto`, estado según la tabla de data-model.md (cada fila, incluido «Falta» con fecha futura → `pendiente`, incluido «falta esto» ganando a «Calificado» y un texto desconocido que deja el estado vacío y se registra)
- [ ] T035 [P] [US1] Escribir `tests/test_plan_aplicar_us1.py`: con el alumno `prueba`, `bloqueo tomar` → `prueba descargar --capturas` → `descargas recoger` (capturas) → `plan` → `prueba descargar` → `descargas recoger` (adjuntos) → `aplicar`, con `ALFABETA_EJECUCION`; una captura con otro `ejecucion` en las descargas no se recoge; una captura fuera del curso escolar configurado → `plan` sale con 1 y escribe `detenida` con `configuracion_invalida`; un adjunto no traído queda en `enlaces.md` de su elemento con enlace y motivo; `plan` pide las descargas esperadas y `aplicar` deja cada elemento en su carpeta o anotado con enlace y motivo (SC-001); un adjunto que no llega queda «no traído»; una captura de clase inválida no impide aplicar la otra (FR-029); sin el bloqueo tomado, `plan` y `aplicar` salen con 1; confirmar un emparejamiento después de una primera `aplicar` mueve las réplicas de la carpeta de mes a la del tema sin duplicarlas; con `--asignatura` solo se planifica y aplica esa asignatura; una captura `parada` con `clase` deja esa clase sin aplicar y el resultado `parcial` con su motivo; `aplicar` sin capturas nuevas sigue moviendo las réplicas que cambió una decisión

### Implementation for User Story 1

- [ ] T036 [US1] Implementar `skills/classroom-sync/scripts/extract.js` según research R3: captura de la lista de clases y captura por clase («Trabajo de clase» y detalle de tarea, material y pregunta: publicación, modificación, entrega, puntos, descripción, estado de «Tu trabajo» y adjuntos; el id de cada elemento y de cada adjunto se toma por su posición en los patrones de URL anotados en S3, con una regla para elementos y otra para adjuntos de Drive, nunca por su forma); solo navega a las páginas permitidas por FR-007, espera ≥2 s con variación entre páginas, nunca pulsa el panel «Tu trabajo» ni sigue formularios o cuestionarios; detecta desafíos y etiquetas de interfaz inesperadas y devuelve una `parada`; marca `completa`; recibe de Claude el `ejecucion` en curso y descarga el resultado como `alfabeta-captura-<ejecucion>-<clase>-<marca>.json`, con el campo `ejecucion`
- [ ] T037 [US1] Implementar `src/alfabeta/captura.py`: lee capturas, comprueba a mano sus claves imprescindibles (sin dependencias) y las normaliza a `Elemento` y `Adjunto` con `ResolvedorFechas` y la tabla de estados; el estado sale del detalle, no del listado (FR-008a); completar `FuenteClassroom` en `src/alfabeta/fuentes.py`
- [ ] T038 [US1] Implementar `src/alfabeta/decisiones.py` (`AlmacenDecisiones` en `datos/decisiones.json`) y los subcomandos `decisiones proponer`, `confirmar`, `corregir` y `cambiar` según `contracts/cli.md`; prueba en `tests/test_decisiones.py` (un `(tipo, origen)` con una decisión no sustituida no se vuelve a proponer, salvo una `rechazada` cuyo origen muestra una modificación posterior o, para `emparejamiento_tema`, cuyo título cambió o con un tema del libro nuevo en el Drive después del rechazo; una propuesta idéntica no escribe; `confirmar --rechazar` sobre un `examen_detectado` sale con 1; `cambiar` deja la anterior (confirmada o rechazada) `sustituida`; `--tipo` desambigua; `seguridad` obligatoria en propuestas; un `candidato_descartado` cuenta desde que es propuesta y, rechazado por la familia, devuelve el candidato a pendientes; un `examen_detectado` o `candidato_descartado` cuya `huella_origen` ya no casa con el texto pasa a `sustituida`, salvo que tenga `correccion_examen`)
- [ ] T039 [US1] Implementar `src/alfabeta/plan.py` (`Planificador`) y el subcomando `plan`: fuentes + estado + decisiones → `datos/plan.json` con descargas pedidas (url según S1 y nombre esperado; solo nuevas, modificadas, renombradas o de revisión completa, FR-026), réplicas a escribir y decisiones pendientes (clases sin asociar, temas sin emparejar, y elementos de un tema del profesor que abarca varios temas del libro); un tema rechazado vuelve a pendientes solo si cambia su título o aparece un tema del libro nuevo; `--asignatura` limita el alcance y, sin él, solo entran las clases que `descargas recoger` anotó en el bloqueo desde el último `bloqueo tomar`; un `(tipo, origen)` que ya tiene una decisión no sustituida no vuelve a `decisiones_pendientes` (salvo la regla de las rechazadas), de modo que un `candidato_descartado` de un elemento no impide proponer su `emparejamiento_elemento`; un `candidato_descartado` rechazado por la familia devuelve su candidato a pendientes en el siguiente `plan`; sale con 1 y `configuracion_invalida` si una captura se hizo fuera del curso escolar configurado; reparte en tandas distintas las descargas con el mismo nombre esperado; ampliar `prueba preparar` para dejar en `adjuntos-prueba/` (fuera de las descargas) los adjuntos inventados con los nombres que pide el plan, implementar `prueba descargar` según `contracts/cli.md`, y dejar las asociaciones de clase confirmadas y una propuesta `examen_detectado`
- [ ] T040 [US1] Implementar `src/alfabeta/descargas.py` (`BandejaDescargas` sobre `descargas.carpeta`) y `descargas recoger`: mueve solo los ficheros del plan y las capturas de la ejecución en curso (`ejecucion` en nombre y campo), anota en el bloqueo las clases recogidas, ignora los `.crdownload` de Chrome a medio descargar, casa cada adjunto por su nombre esperado o ese nombre con el sufijo ` (<n>)` del navegador y solo si se creó después del plan, y verifica que están completos (FR-018); prueba en `tests/test_descargas.py` con dos adjuntos del mismo nombre en tandas distintas (cada uno acaba en la réplica de su elemento) y un fichero con el nombre esperado anterior al plan, que no se recoge
- [ ] T041 [US1] Implementar `src/alfabeta/replicas.py` (`Aplicador`) y `aplicar` para materiales, enunciados y notas `enlaces.md` y `descripcion.md`, borrando de `datos/` los adjuntos recogidos una vez colocados o comprobados idénticos, anotando un adjunto no traído en `enlaces.md` de su elemento, dejando sin aplicar la clase de una captura `parada` (resultado `parcial` con su motivo), recalculando destinos con las decisiones vigentes, moviendo sin duplicar las réplicas cuyo destino cambió por una decisión confirmada después de su colocación, y registrando `numero_tema_profesor` la primera vez que coloca algo de un tema `Tema PNN`, escribiendo solo en la raíz del alumno, sin mostrar nunca su ruta absoluta, y deteniéndose sin escribir si el Drive no está montado (FR-030, FR-031)
- [ ] T042 [US1] Escribir `skills/classroom-sync/SKILL.md`: todas las órdenes se ejecutan en el Mac con `uv run --project <herramientas.repositorio> python -m alfabeta`, nunca en la máquina virtual de la app; `bloqueo tomar --modo interactiva`, cuyo `ejecucion` se pasa en `ALFABETA_EJECUCION` a cada orden siguiente (en línea, `ALFABETA_EJECUCION=<id> uv run …`, porque cada llamada de herramienta es un shell nuevo), y `config comprobar`; abrir Classroom en Chrome con la extensión de Claude y localizar la cuenta escolar recorriendo `/u/<n>` y comparando el correo en local; si la sesión caducó, hay un desafío o la interfaz no es la esperada, `registro detener` con su motivo y aviso a la familia; capturar la lista de clases (el extractor recibe el `ejecucion`), `descargas recoger`, `plan` y proponer las asociaciones de clase (en interactiva, confirmarlas en ese momento); capturar cada clase asociada (o solo las de la asignatura pedida), con `descargas recoger` tras cada clase (que también renueva el bloqueo); si a mitad la sesión caduca, aparece un desafío o la interfaz no es la esperada, recoger la `parada` y aplicar las clases ya capturadas (`parcial` con su motivo, data-model «Ejecución»); `plan` de nuevo y proponer emparejamientos de tema y, para los temas que abarcan varios del libro, de cada elemento, con motivo y seguridad; descargar los adjuntos pedidos con el método de S1, con al menos 2 s con variación entre descargas y `descargas recoger` tras cada tanda; `aplicar`; `bloqueo soltar`; prohibiciones de solo lectura y de datos personales
- [ ] T043 [US1] Listar en el resumen de `aplicar` las clases no asociadas y las ocultas (FR-008), los emparejamientos pendientes de confirmar y los estados desconocidos

**Checkpoint**: US1 funciona sola con el alumno `prueba` y con una asignatura real (quickstart 2 y los puntos de US1 del escenario 9).

---

## Phase 4: User Story 2 - La agenda del alumno (P1)

**Goal**: `agenda.json` y `agenda.md` por curso con las cinco categorías, exámenes detectados, «Pendiente»
y «Hecho», sin depender del día.

**Independent Test**: quickstart escenario 3.

### Tests for User Story 2

- [ ] T044 [P] [US2] Escribir `tests/test_clasificacion.py`: cada elemento recibe exactamente una categoría con la precedencia examen > cuestionario > entrega > material > aviso (pregunta que es examen → `examen`; tarea con título de prueba en cualquiera de los idiomas del alumno → `examen`; «Pregunta» sin indicios → `cuestionario`; tarea cuyo único adjunto es un formulario → `cuestionario`; tarea con un formulario y un fichero → `entrega`; anuncio sin examen → `aviso`); el 100 % de los anuncios de examen inventados de T029 sale como candidato (SC-004a)
- [ ] T045 [P] [US2] Escribir `tests/test_agenda.py`: cada estado en su lista según la tabla de FR-020c (`pendiente`, `vencida`, `falta_segun_profesor` → Pendiente; `entregada`, `devuelta` → Hecho; examen detectado → Pendiente hasta que exista una captura de su clase posterior a su fecha, descartado → fuera; examen que es una tarea en `vencida` con una captura de su clase posterior a su fecha → Hecho, y en `falta_segun_profesor` → Pendiente); «Pendiente» del más próximo al más lejano con los sin fecha al final; «Hecho» por fecha de entrega o examen, del más reciente al más antiguo; un examen detectado es una entrada propia `<elemento>#examen-<k>` y el material o aviso de origen conserva la suya; una entrega, cuestionario o examen sin `estado` va a «Pendiente»; un examen detectado sin fecha sigue en «Pendiente» hasta que la familia lo corrija o lo descarte; estados incluido `falta_segun_profesor`; examen detectado con `detectado: true` y `origen`, presente en la agenda desde que es propuesta y sin confirmar; un elemento que anuncia dos exámenes da dos entradas `<elemento>#examen-1` y `-2`; el 100 % de las propuestas `examen_detectado` de prueba están en la agenda (SC-004a); material y aviso en «Publicado» tras «Hecho»; una corrección de la familia prevalece en la siguiente ejecución; `carpeta` vacía para un aviso sin réplica; `enlace_classroom` sin `/u/<n>`; `agenda.json` válido según `contracts/agenda.schema.json` (todas las claves obligatorias) y sin marca de tiempo; `agenda.md` indica abrir los enlaces con la cuenta escolar; generar dos veces con distinto «hoy» no reescribe los ficheros
- [ ] T046 [P] [US2] Ampliar `tests/js/extract.test.mjs` con el tablón: anuncios con `texto_creacion`, texto y adjuntos; se ignoran las notificaciones de elementos nuevos; sin comentarios de alumnos ni nombres

### Implementation for User Story 2

- [ ] T047 [US2] Ampliar `skills/classroom-sync/scripts/extract.js` para leer los anuncios del tablón (texto, «Fecha de creación» y adjuntos), sin comentarios ni autores, y `src/alfabeta/captura.py` para normalizarlos a `Elemento` de tipo `anuncio` con `publicado` desde «Fecha de creación» (caso nuevo en `tests/test_captura.py`)
- [ ] T048 [US2] Implementar `src/alfabeta/clasificacion.py` (`Clasificador`): categoría cerrada con precedencia (FR-020a) y candidatos a examen por indicios en títulos, descripciones y anuncios, que pasan a `plan.json` como decisiones pendientes salvo que su origen ya tenga una decisión `examen_detectado` o `candidato_descartado` vigente (una `rechazada` no cuenta: el candidato vuelve) (un `examen_detectado` o `candidato_descartado` deja de valer si cambia la huella del texto de su origen, `huella_origen`, salvo que la familia lo corrigiera); un solo candidato por elemento (Claude decide cuántos exámenes anuncia y numera `k`)
- [ ] T049 [US2] Ampliar `skills/classroom-sync/SKILL.md`: para cada candidato a examen, Claude propone fecha, motivo y seguridad en el idioma de la clase con `decisiones proponer` (`examen_detectado`, origen `<elemento>#examen-<k>` con `k` = 1, 2… si anuncia varios); en ejecución programada quedan como «detectado»
- [ ] T050 [US2] Implementar `src/alfabeta/agenda.py` (`GeneradorAgenda`) y el subcomando `agenda`: contenido que depende solo del estado y las decisiones, ficheros reescritos solo si cambian sus bytes, bloqueo comprobado y renovado, JSON `{escritos:[…]}` en stdout y el texto para personas en stderr; `aplicar` la regenera al final (FR-020…FR-020c)

**Checkpoint**: US1 y US2 funcionan; la familia ve una agenda completa del curso.

---

## Phase 5: User Story 3 - Volver a sincronizar sin duplicar y con cambios (P2)

**Goal**: ejecuciones repetidas idempotentes, cambios detectados, nada borrado, reanudación tras corte.

**Independent Test**: quickstart escenario 4.

- [ ] T051 [P] [US3] Escribir `tests/test_incremental.py`: segunda ejecución sin cambios → cero ficheros modificados en la raíz y estado sin reescribir (SC-002); elemento con «Última modificación» posterior → se vuelve a pedir su adjunto y, si la huella cambia, versión nueva y `<nombre> (anterior AAAA-MM-DD)`; elemento sin cambios → no se pide hasta la revisión completa; elemento ausente de una captura `completa: true` → réplica conservada y `retirado`; ausente de una `completa: false` → nada retirado; ejecución cortada a mitad → la siguiente termina sin duplicar; una revisión completa que encuentra los mismos bytes no reescribe `estado.json` y la siguiente se cuenta desde la línea del registro con `revision_completa: true` (la primera sincronización cuenta como revisión completa); dos capturas idénticas con una fecha de examen entre ellas → solo cambia esa entrada en la agenda; una segunda captura con otro `capturado` y ninguna fecha entre las dos → ni `estado.json` ni la agenda se reescriben (FR-025)
- [ ] T052 [US3] Implementar en `src/alfabeta/replicas.py` y `src/alfabeta/plan.py` la comparación por huella SHA-256 antes de escribir, la marca de modificación vista, la revisión completa periódica (`sincronizacion.revision_completa_dias`), las versiones anteriores (FR-015b), el marcado de retirados solo con captura completa (FR-027) y la reanudación desde `plan.json` y la poda de capturas antiguas de `datos/capturas/` por encima de `capturas_conservadas`
- [ ] T053 [US3] Completar el registro de la ejecución en `src/alfabeta/estado.py` (contadores, estados desconocidos, decisiones pendientes, `modo` leído del bloqueo (`bloqueo tomar --modo`), índice `/u/<n>` leído de `indice_cuenta` en la captura de clases, `resultado`, `motivo`) y el resumen «qué ha cambiado desde la última vez» de `aplicar` (FR-028)
- [ ] T054 [US3] Aplicar `decisiones cambiar` sobre un emparejamiento confirmado o rechazado: mover las réplicas a su carpeta correcta sin duplicarlas ni perderlas (caso límite de la spec), con prueba en `tests/test_incremental.py`

---

## Phase 6: User Story 4 - El libro en la misma estructura (P2)

**Goal**: Science Bits escribe en `<tema>/sciencebits/` del Drive familiar con la configuración por alumno.

**Independent Test**: colocar un tema de prueba y comprobar la ruta y que `classroom/` del mismo tema no cambia.

- [ ] T055 [P] [US4] Escribir `tests/test_libro.py`: `libro colocar` deja `TemaNN_<LANG>.pdf` y `.md` en `<curso>/<asignatura>/Tema NN - <título>/<libro>/` con huella y versión anterior, y añade una línea al registro (instante, fuente, tema, colocado o sin cambios); `registro cuaderno` escribe su línea con cada resultado y sale con 1 si falta `--motivo` con `fallo`; nunca escribe fuera de la raíz del alumno ni en Dropbox; un tercer proveedor inventado se conecta como otra `Fuente` sin tocar `ubicacion.py` ni `replicas.py`
- [ ] T056 [US4] Completar `FuenteLibro` en `src/alfabeta/fuentes.py` e implementar en `src/alfabeta/libro.py` y `src/alfabeta/__main__.py` los subcomandos `libro colocar` y `registro cuaderno` según `contracts/cli.md`, con el bloqueo comprobado y renovado
- [ ] T057 [US4] Actualizar `skills/sciencebits-a-notebooklm/SKILL.md`: ejecutar las órdenes en el Mac con `uv run --project <herramientas.repositorio> python -m alfabeta` (nunca en la máquina virtual, que solo ve Descargas); tomar el bloqueo (`bloqueo tomar --modo interactiva`, o `programada` si la lanza una tarea programada, y pasar su `ejecucion` en `ALFABETA_EJECUCION` a cada orden siguiente) antes de abrir Science Bits, renovarlo (`bloqueo renovar`) en cada sondeo de la captura, entre los pasos de construcción y entre cada fuente que sube `nlm`, y soltarlo al terminar; recibir o preguntar el `id` del alumno (nunca adivinarlo); leer `~/.alfabeta/<alumno>/config.toml` (`[[asignaturas]]` con `libro = "sciencebits"` y `clase_libro`, curso escolar, `alumno.nivel` en lugar de `student.grade`, `[sciencebits] url` e `idiomas` en lugar de `languages` (el primero da el título de la carpeta), `[herramientas] carpeta`, `[descargas] carpeta` en lugar de `~/Downloads` (también en `scripts/watch.py`), `[cuaderno] activado` y el nombre de cuaderno que fija la constitución, «`<nivel>. <asignatura>. Tema NN - <título>`» con `alumno.nivel`), generar como hoy y colocar con `libro colocar`; en el paso de `nlm`, listar antes las fuentes del cuaderno del tema (`nlm source list <cuaderno> --json`) y añadir solo los ficheros que no estén, comparando por el título con que `nlm source add --file` registra la fuente (comprobarlo antes con un cuaderno de prueba; constitución V y «Cuadernos»: repetir no duplica fuentes); tras el paso de `nlm` (o si `[cuaderno] activado` es falso), `registro cuaderno` con su resultado (`sin_cambios` = el cuaderno existía y no se añadió ninguna fuente), y si `nlm` falla, `fallo` con motivo y aviso a la familia, sin tocar lo colocado; sustituir `storage.tools_dir`, `storage.base_dir`, `storage.topic_folder_pattern`, `subjects`, `sciencebits.url` y `notebook.*` por esas claves; en `scripts/build.py`, quitar de `L10N` los valores `unit` y `course` (que nombran un curso, una asignatura y un tema concretos; constitución I) y hacer obligatorio `--config`, que sale nombrando la clave que falta y quitar toda referencia a `config.json` y Dropbox; ninguna clave leída fuera de la plantilla; en la descripción, los pasos y los ejemplos de `SKILL.md` (también las rutas con idioma de la URL), idiomas neutros (`es`, `en`) y el conjunto de idiomas tomado de `sciencebits.idiomas`; la tabla `L10N` de `build.py` con los textos de interfaz por idioma que admite el proveedor es una capacidad, no un dato del alumno, y se queda; quitar las instrucciones que crean la configuración o escriben en ella (si falta o no es válida, `config comprobar` y parar); «el siguiente tema» sale de las carpetas `Tema NN` que ya tienen `sciencebits/` en el Drive

---

## Phase 7: User Story 5 - Un segundo alumno y nada personal en el repositorio (P2)

**Goal**: dos alumnos inventados conviven sin tocar el repositorio; el guardarraíl cubre todo el repo.

**Independent Test**: quickstart escenario 5.

- [ ] T058 [P] [US5] Escribir `tests/test_varios_alumnos.py`: dos alumnos creados desde la plantilla en un `--inicio` temporal; sincronizar uno solo escribe su raíz, su estado y su registro; mientras uno sincroniza, el otro no puede tomar el bloqueo del navegador (comparten Chrome y la carpeta de descargas) y sus bloqueos de alumno son independientes; `git status` del repositorio sin cambios
- [ ] T059 [US5] Pasar `python -m alfabeta guardarrail --todo` con la configuración real del primer alumno presente en el Mac sobre todo el repositorio (incluidas `specs/` y `tests/fixtures/`), y `guardarrail --historia` sobre lo publicado (`git log --all -p`), y corregir cualquier hallazgo antes de cerrar la fase (uno en la historia publicada se lleva a la familia: reescribirla es su decisión)

---

## Phase 8: User Story 6 - Tablón, entregas del alumno y correcciones (P3)

**Goal**: anuncios guardados por mes; en cada tarea, `entrega` y `correccion` junto al `enunciado`.

**Independent Test**: dos anuncios (uno con adjunto), una tarea entregada sin corregir y otra devuelta con
corrección; cada papel reconocible por el nombre (SC-008a), sin comentarios ni nombres de compañeros.

- [ ] T060 [P] [US6] Escribir `tests/test_us6.py` (el autor y los comentarios de clase y privados plantados en la página sintética no aparecen en `correccion.md` ni en el aviso): anuncio → `<AAAA-MM>/classroom/AAAA-MM-DD - aviso - <resumen>.md` (o carpeta si tiene adjuntos) y su entrada de agenda pasa a tener `carpeta`; entrega del alumno → `entrega - <nombre>`; corrección → `correccion.md` con estado de calificación, nota solo si Classroom la muestra, comentario del profesor y fecha de devolución; reentrega → la anterior como anterior
- [ ] T061 [US6] Ampliar `skills/classroom-sync/scripts/extract.js` y `tests/js/extract.test.mjs` para leer del detalle los ficheros entregados por el alumno, el comentario y la nota visibles y la fecha de devolución (`texto_devolucion`), sin tocar el panel «Tu trabajo»
- [ ] T062 [US6] Implementar en `src/alfabeta/replicas.py` las réplicas de anuncios, entregas del alumno y `correccion.md` (FR-015a, FR-016a)

---

## Phase 9: Polish & Cross-Cutting

- [ ] T063 Ejecución programada (FR-021a), según S2: añadir a `skills/classroom-sync/SKILL.md` el modo programado (`bloqueo tomar --modo programada`; sin preguntas, propuestas pendientes; con las mismas paradas que la interactiva (data-model «Ejecución»: antes de capturar ninguna clase o con el Drive sin montar, `registro detener` con su motivo y sin escribir en la carpeta del alumno; a mitad, `parcial`), y el aviso es el resultado de la tarea en la app; en modo reducido, solo el aviso «toca sincronizar») y documentar en `README.md` cómo crear la tarea programada diaria con la hora de `programacion.diaria`
- [ ] T064 [P] Actualizar `README.md` (tabla de skills con `classroom-sync`; requisitos: Chrome con la extensión, Drive para escritorio, `uv`, Node para desarrollo; instalación con `config/template.toml`, y cómo ejecutan las skills la orden con `uv run --project`), `docs/roadmap.md` (épicas 2 y 3, y el «hoy» y «esta semana» en la épica 2), y quitar de `README.md` y `docs/classroom-investigacion.md` los detalles que acotan curso o región (nivel concreto, idiomas concretos en ejemplos y descripciones; la tabla de textos de interfaz por idioma de `build.py` no cuenta, ver T057)
- [ ] T065 [P] Escribir `tests/test_privacidad.py`: tras una ejecución completa del alumno `prueba`, ni `registro.jsonl`, ni `plan.json`, ni stderr, ni las URLs construidas contienen su `id`, `nombre_visible`, `cuenta` ni la ruta absoluta de su raíz (SC-009, FR-031): la orden nunca imprime `nombre_visible`
- [ ] T066 [P] Abrir la issue de seguimiento «pruebas y puertas de calidad para la skill de Science Bits» (excepción registrada en el plan) junto con las issues de esta spec
- [ ] T067 Ejecutar quickstart.md completo (escenarios 1 a 9) y anotar los resultados en el PR

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)**: sin dependencias; T005 antes de T006 para que la puerta recoja pruebas.
- **Foundational (2)**: tras Setup. T013–T016 antes de cualquier página real en el repo (T031). S1 (T010) antes de T039–T040; S3 (T012) antes de T014, T016, T031, T032 y T036; S2 (T011) antes de T024–T025 y T063.
- **US1 (3)**: tras Foundational. Es el MVP.
- **US2 (4)**: usa la captura y el estado de US1.
- **US3 (5)**: sobre US1 (réplicas y estado).
- **US4 (6)**: tras US1 (T041, `Aplicador`) y US3 (T052, huellas y versiones anteriores).
- **US5 (7)**: T058 tras T041 (necesita `plan` y `aplicar`); T059 cierra la fase 7; después, `guardarrail --todo` sigue corriendo en `make ci` en cada PR.
- **US6 (8)**: sobre US1 (carpetas de tarea), US2 (agenda) y US3 (versiones anteriores).
- **Polish (9)**: al final. T000 va en el PR de la spec, antes de cualquier implementación; T066 se hace al abrir las issues tras aprobarlo.

### Within Each Story

Pruebas primero (deben fallar), después dominio, servicios, orden y skill.

### Parallel Opportunities

- Setup: T002, T003, T004, T007, T008, T009 a la vez tras T001.
- Foundational: T013, T017, T018, T020, T021, T022, T024, T026, T027 a la vez; los spikes T010–T012 primero, porque sus resultados fijan T014, T024–T025 y T032.
- US1: T031–T035 a la vez; T038 tras T037 (los dos añaden subcomandos a `__main__.py`).
- T058 (US5) en paralelo con US2–US4, una vez hecho T041.

### Parallel Example: User Story 1

```text
T031 páginas sintéticas   T032 prueba de extract.js   T033 prueba de solo lectura   T034 prueba de captura   T035 prueba de plan/aplicar
```

## Implementation Strategy

### MVP First (User Story 1)

1. Setup y Foundational, con los tres spikes.
2. US1 con una asignatura real.
3. **Parar y validar** con quickstart 2 y 9.

### Incremental Delivery

1. US1 → carpetas con el material del profesor.
2. US2 → agenda con exámenes: lo que más interesa a la familia.
3. US3 → repetible a diario sin duplicar.
4. US4 → el libro junto al material.
5. US5 → segundo alumno y repositorio limpio.
6. US6 → tablón, entregas y correcciones.
7. Polish → ejecución programada y documentación.
