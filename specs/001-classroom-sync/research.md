# Research: Classroom → Drive familiar (spec 001)

Fase 0 del plan. Cada decisión lleva su motivo y las alternativas descartadas. Los hechos observados
citan de dónde salen; nada de lo que sigue nombra al alumno, al profesorado ni identificadores reales.

## Hechos observados

Observado el 2026-10-25 en el Classroom del alumno, en Chrome (extensión de Claude), en solo lectura:
listado de clases, «Trabajo de clase» de dos asignaturas, una página de detalle de tarea, el tablón
de una clase, «Tareas pendientes» y la raíz del Drive personal del alumno.

| Hecho | Observado en |
|---|---|
| Una docena de clases visibles y varias ocultas; títulos en varios idiomas que incluyen el curso y el grupo, con formatos distintos según el profesor | Página de inicio de Classroom |
| Una asignatura con libro en Science Bits no aparece entre las clases visibles | Página de inicio; queda como pregunta para la configuración (¿clase oculta?) |
| Los temas del profesor no coinciden con los del libro: un tema del profesor, con otro número y en otro idioma, reúne material de un tema del libro y de otro contenido; otro tema del profesor (introductorio) no existe en el libro | «Trabajo de clase» de una asignatura con libro |
| Otra asignatura numera temas y tareas («N. título», «N.M título») y tiene temas que no son unidades (preparación de una prueba inicial, exámenes guardados, «Sin tema») | «Trabajo de clase» de una asignatura sin libro |
| Tipos: «Tarea», «Material» y «Pregunta» | Ambos «Trabajo de clase» |
| El listado muestra una sola fecha por elemento: «Fecha de entrega: 13 oct», «Sin fecha de entrega», «Publicado: 22 oct» o «Última modificación: 1 oct»; nunca el año; a veces relativa («Mañana, 8:00») | Ambos «Trabajo de clase» |
| El listado marca «Completada» una tarea cuyo detalle dice «Calificado» y «El profesor ha indicado que falta esto» | Listado y detalle de la misma tarea |
| El detalle de una tarea muestra autor, fecha de publicación, puntos, fecha de entrega, instrucciones y el panel «Tu trabajo» con su estado y los botones «Añadir o crear» y «Volver a entregar»; no se vio una nota numérica | Página de detalle de una tarea calificada |
| La URL del detalle lleva identificadores estables de clase y de elemento: `/u/<n>/c/<clase>/a/<elemento>/details` | Barra de direcciones |
| Al desplegar un material se ven su descripción y sus adjuntos; un PDF adjunto enlaza a `drive.google.com` | «Trabajo de clase», material desplegado |
| El tablón muestra cada publicación con «Fecha de creación» exacta y anuncios de texto libre; uno anuncia, en otro idioma de la clase, un examen con su día de la semana y su fecha, y la lista de contenidos que entran | Tablón de una asignatura con libro |
| «Tareas pendientes» tiene pestañas «Asignado», «Sin entregar» y «Hecho», y secciones plegadas (sin fecha, esta semana, próxima semana, más tarde) | Página de tareas pendientes |
| En el mismo Chrome hay varias cuentas de Google; el índice `/u/<n>` de la cuenta escolar no es fijo | Botón de cuenta en `/u/1` a `/u/5` |
| El Drive personal del alumno ya tiene carpetas propias en la raíz de «Mi unidad» | Raíz de «Mi unidad» |
| Drive para escritorio está instalado, pero la cuenta personal del alumno no está montada | `~/Library/CloudStorage/` |

## Decisiones

### R1. Cómo se repite: skill + scripts deterministas + tarea programada

- **Decisión**: una skill `classroom-sync` que Claude sigue (como la de Science Bits) y que orquesta
  scripts de Python deterministas. La programación diaria usa las tareas programadas de la app de
  escritorio de Claude, con un prompt autocontenido que invoca la skill.
- **Motivo**: lo mecánico (estado, identificadores, nombres, estructura, agenda, recogida de
  descargas) da el mismo resultado en cada repetición si lo hacen scripts (FR-021b). Lo que pide
  juicio (emparejar temas, detectar un examen en un anuncio en otro idioma) lo hace Claude dentro de la
  misma ejecución, sin claves de API ni coste aparte, y queda registrado para no repetirse.
- **Alternativas**: (a) solo un prompt a Claude, sin scripts: no es repetible, cada ejecución decide
  distinto; (b) un script autónomo con Playwright y perfil propio: corre sin Claude pero pierde el
  juicio y obliga a custodiar la sesión de un menor; es la épica del MCP local (issue #2).
- **Riesgo a medir primero (spike S2)**: que una tarea programada pueda usar el navegador con la
  sesión del alumno y descargar ficheros (capturas y adjuntos) sin que nadie apruebe cada descarga en
  ese momento. La documentación de la herramienta dice que la tarea corre mientras la app está abierta
  y con un prompt autocontenido; no dice nada del navegador ni de las descargas. Si no puede, la
  ejecución programada se limita a avisar y la familia la lanza con una orden.

### R2. Navegador: Chrome con la extensión de Claude

- **Decisión**: Chrome con la extensión de Claude, que es lo que el operador prefiere y donde ya
  están las sesiones de la familia.
- **Selección de cuenta**: la cuenta escolar se localiza recorriendo `/u/0…/u/9` y comparando el
  correo del botón de cuenta con el de la configuración, en local. Nunca `authuser=<correo>` en una
  URL (FR-031). El índice encontrado se guarda en el registro de la ejecución, no en la configuración ni en el estado.
- **Alternativa**: el navegador integrado de la app. El extractor sería el mismo JavaScript, pero la
  descarga directa ya falló en él (issue #1); queda para una épica posterior que la pruebe.

### R3. Extracción: un extractor JavaScript sobre las páginas de consulta

- **Decisión**: `extract.js` se inyecta con la herramienta de JavaScript del navegador y devuelve
  JSON: lista de clases (visibles, ocultas, archivadas), temas y elementos de «Trabajo de clase»,
  detalle de cada elemento (estado, fechas, marca de modificación, adjuntos, entrega del alumno,
  corrección) y publicaciones del tablón. Solo navega a la página de inicio, «Trabajo de clase», el
  tablón y la página de detalle de tareas, materiales y preguntas; nunca sigue un enlace a un
  formulario o cuestionario ni pulsa el panel «Tu trabajo». Espera al menos 2 s (con variación) entre
  páginas. Cómo recorre las páginas sin perder el script inyectado (iframe oculto, `fetch` de las páginas
  de detalle o reinyección por Claude en cada página) se decide con S3 y se anota aquí antes de T032.
- **Captura completa o no**: cada captura dice si llegó al final de la clase (`completa`). Una captura
  cortada no retira elementos (FR-027).
- **Paradas**: si encuentra un desafío anti-robot (CAPTCHA, página de verificación, «demasiadas
  peticiones») o no encuentra las etiquetas de interfaz esperadas en castellano, devuelve una marca de
  parada en vez de datos y la skill termina la ejecución con motivo.
- **Motivo**: el estado fiable está en el detalle (hecho observado); el listado solo sirve para
  descubrir elementos y su marca de «Última modificación». La extensión oculta en su salida valores con
  aspecto de base64, así que el extractor devuelve los identificadores ya separados de la URL.
- **Alternativas**: leer las llamadas internas de la web de Classroom (más estable, sin documentar):
  se deja para el MCP local.

### R4. Descarga de adjuntos de Drive (spike S1, primer riesgo técnico)

- **Problema**: la descarga directa `drive.google.com/uc?export=download` falló en el navegador
  integrado (issue #1). Los adjuntos enlazan a `drive.google.com`.
- **Decisión**: probar en este orden, con la sesión de la cuenta escolar y un adjunto real, y quedarse
  con el primero que deje el fichero completo en la carpeta de descargas:
  1. `drive.usercontent.google.com/download?id=<id>&export=download&authuser=<n>`;
  2. para Documentos, Presentaciones y Hojas de Google, `docs.google.com/<tipo>/d/<id>/export?format=pdf&authuser=<n>`;
  3. el botón de descarga del visor de Drive.
- **Cuándo se descarga** (ids de elemento y de adjunto con reglas propias, según los patrones de URL
  anotados en S3): la primera vez, y después solo si el elemento muestra una modificación
  posterior a la última réplica, si cambia el nombre o el tipo del adjunto, o en la revisión completa
  periódica (`[sincronizacion] revision_completa_dias`; valor de la plantilla: 7). La fecha de la
  última revisión completa es la de la última línea del registro con `revision_completa: true`, no un
  campo del estado: una revisión que encuentra los mismos bytes no reescribe el estado. Así no hay
  cientos de descargas diarias (FR-010, FR-026) y se cumple el principio V.
- **Recogida**: `descargas recoger` (sobre la carpeta de `[descargas] carpeta`) mueve cada fichero
  esperado e ignora los `.crdownload` de Chrome a medio descargar, comprueba que está completo y lo deja
  listo para colocar (FR-018). Solo recoge lo que ha pedido.

### R5. Fechas sin año y relativas

- **Decisión**: un único resolvedor de fechas: año deducido del curso escolar (septiembre a diciembre,
  primer año; enero a agosto, segundo), relativas («Hoy», «Mañana», días de la semana) respecto al
  momento de la captura (`capturado`), no al de la ejecución que la aplica, todo en `Europe/Madrid` con
  `zoneinfo`. La fecha de publicación sale de la «Fecha de creación» del tablón o del detalle, nunca de
  «Última modificación».
- **Pruebas**: tabla de casos, incluidos el cambio de año (diciembre/enero), los cambios de hora y una
  captura aplicada al día siguiente.

### R6. Estado, bloqueo e idempotencia

- **Si el vigilante no sobrevive a la llamada de herramienta (S2)**: el bloqueo pasa a ser un fichero de
  concesión con la hora de su última renovación; cada subcomando toma el `flock` solo mientras corre,
  comprueba que la concesión es de su ejecución y la renueva; una concesión sin renovar durante
  `bloqueo_inactividad_minutos` se puede tomar, y quien la toma escribe la línea `detenida` con motivo
  `inactividad` de la anterior. Los subcomandos de `contracts/cli.md` y sus salidas no cambian; solo desaparece el vigilante.
- **Decisión**: un fichero de estado JSON por alumno en su carpeta de datos local, escrito de forma
  atómica (fichero temporal y renombrado) y solo si cambia, con un registro por elemento y por réplica:
  identificador de Classroom, papel, ruta relativa, huella (SHA-256), versión y marca de modificación
  vista. El registro de cada ejecución va en JSON Lines en la misma carpeta, junto con el índice
  `/u/<n>` usado, que no va al estado.
- **Bloqueo**: `bloqueo tomar` abre con `fcntl.flock` `datos/bloqueo` (del alumno) y
  `<inicio>/.navegador.lock` (del Mac: todos los alumnos comparten Chrome y la carpeta de descargas),
  y los mantiene un proceso vigilante durante toda la ejecución. Cada subcomando renueva el bloqueo, y
  `bloqueo renovar` lo renueva en los tramos largos del navegador (entre clases, entre tandas de
  descargas, en cada sondeo de una captura de Science Bits);
  si pasan `bloqueo_inactividad_minutos` sin renovarlo, el vigilante entiende que la ejecución murió,
  suelta los dos y escribe una línea `detenida` con motivo `inactividad`. Si el vigilante muere, el
  sistema libera los `flock`. Un bloqueo ocupado detiene la ejecución con su propio motivo (FR-030).
- **Paradas antes de aplicar**: `registro detener --motivo <m>` escribe la línea `detenida` de una
  ejecución que se para en el navegador (sesión caducada, desafío, interfaz inesperada) o antes
  (Drive sin montar). Un bloqueo ocupado lo registra el propio `bloqueo tomar`, y una parada de `plan` o
  `aplicar`, ellos mismos.
- **Motivo**: biblioteca estándar, legible por una persona, suficiente para cientos de elementos por
  curso. Una segunda ejecución sin cambios compara huellas y no escribe (FR-025).
- **Alternativa**: SQLite. Más robusto con mucho volumen; innecesario aquí (constitución IX).

### R7. Juicio de Claude: asociaciones, emparejamientos y exámenes detectados

- **Decisión**: los scripts preparan la lista de lo que necesita decisión (clases sin asociar, temas sin
  emparejar, publicaciones con indicios de examen) y Claude propone, con motivo y seguridad (alta,
  media, baja), siguiendo la skill. La familia confirma, rechaza, corrige (fecha, categoría o
  descartar un examen) o cambia (un emparejamiento ya confirmado). Las decisiones van a
  `datos/decisiones.json`, ligadas al identificador de Classroom. Una decisión confirmada no se vuelve
  a proponer (FR-021b); cambiarla la pasa a `sustituida` y crea la nueva.
- **Sin confirmar**: los elementos de un tema sin emparejar van a su carpeta de mes; un examen
  detectado entra en la agenda marcado «detectado» hasta que la familia lo confirme o lo corrija.

### R8. Pruebas contra páginas sintéticas

- **Decisión**: las páginas reales se guardan solo fuera del repositorio (`datos/capturas-crudas/`).
  Lo que entra en `tests/fixtures/classroom/` son páginas **sintéticas**: `anonimizar` conserva la
  estructura (etiquetas, clases CSS, jerarquía) y las etiquetas de interfaz de una lista permitida
  («Trabajo de clase», «Fecha de entrega», «Tu trabajo»…), e inventa todo texto y atributo restante:
  títulos, descripciones, fechas, nombres de fichero, ids y textos accesibles. Se niega a escribir si
  sobrevive cualquier texto de la entrada fuera de esa lista.
- **Motivo**: el material es de sus autores y no se redistribuye (constitución IV), y ningún fixture
  contiene material ni datos de un alumno real (III). La estructura es lo único que necesitan las
  pruebas del extractor.
- **Comprobación**: el guardarraíl de datos personales (FR-005) también pasa por las páginas
  sintéticas. Ninguna prueba ni el CI llama a Classroom (constitución VI).

### R9. Configuración por alumno: TOML con plantilla espejo, fuera del repo

- **Decisión**: la plantilla es `config/template.toml` en el repositorio, con todas las claves, valores
  `changeme` y un comentario por clave. La configuración real de cada alumno es
  `~/.alfabeta/<alumno>/config.toml`, copia de la plantilla con los valores rellenos. Lo que escribe
  alfabeta (decisiones, estado, registro, bloqueo, plan, capturas) va en `~/.alfabeta/<alumno>/datos/`.
- **Localización**: `~/.alfabeta/` es la ubicación declarada, no un valor por defecto silencioso: si no
  existe, alfabeta se detiene y lo dice. La opción global `--inicio` la sustituye (pruebas). El alumno
  se elige con `--alumno <id>`, que se resuelve una sola vez en la entrada de la orden.
- **Validación**: el conjunto de claves (con su tipo) de la configuración real debe ser igual al de la
  plantilla; una clave que falta, sobra, cambia de tipo o contiene `changeme` detiene la ejecución
  nombrando la clave (FR-003). Una prueba comprueba además que toda clave que lee el código está en la
  plantilla.
- **Por qué TOML**: admite comentarios (la plantilla documenta cada clave) y se lee con la biblioteca
  estándar (`tomllib`). Lo que escribe alfabeta va en JSON, que también es estándar.
- **Alternativas**: un `.env` por alumno (no expresa listas ni el mapa de asignaturas); JSON también
  para la configuración (sin comentarios); YAML (dependencia nueva). El fichero `config.example.json`
  actual desaparece.

### R10. Código: un paquete con una orden y skills finas

- **Decisión**: un paquete Python `alfabeta` en `src/alfabeta/` con una sola orden
  (`python -m alfabeta <subcomando>`, argparse de la biblioteca estándar) que agrupa lo determinista.
  Las skills (`skills/classroom-sync/`, `skills/sciencebits-a-notebooklm/`) contienen el `SKILL.md`
  que sigue Claude y el JavaScript que corre en el navegador, y llaman a esa orden.
- **Fuentes**: un Protocol `Fuente` con `FuenteClassroom` y `FuenteLibro`; la subcarpeta de cada
  réplica es el nombre de su fuente (`classroom`, o el valor de `libro` de la asignatura).
- **Validación en ejecución**: `captura.py` comprueba a mano las claves imprescindibles de cada captura
  (biblioteca estándar); los esquemas completos se comprueban en las pruebas con `jsonschema`
  (dependencia de desarrollo). Los esquemas viven en `src/alfabeta/esquemas/`, copia de `contracts/`.
- **Motivo**: un solo sitio para las reglas de nombres, estructura y estado que comparten Classroom y
  los libros; `src/` y `tests/` son las dos raíces que esperan el comprobador de tipos y el linter.
- **Dependencias**: ninguna en tiempo de ejecución. Desarrollo: `ruff`, `pyright` (modo estricto, con
  las reglas de anotaciones de ruff), `pytest` y `jsonschema`, gestionados con `uv` (`pyproject.toml`,
  `uv.lock`, `.python-version` = 3.12). Una puerta única `make ci` igual en local y en CI.

### R11. Pruebas del extractor JavaScript

- **Decisión**: `extract.js` se prueba con `node --test` y `jsdom` contra las páginas sintéticas (R8).
  Es la única dependencia de desarrollo de Node, declarada en `package.json`, y la puerta `make ci` la
  ejecuta. Las pruebas comprueban a mano las claves de la salida; el esquema completo se comprueba en
  Python sobre las capturas JSON de prueba.
- **Solo lectura comprobable**: una prueba instala escuchas de clic, envío de formularios y navegación
  en la página sintética y comprueba que el extractor no pulsa ningún botón del panel «Tu trabajo», no
  envía nada y no navega a formularios ni cuestionarios.
- **Diseño**: el extractor solo lee el DOM y devuelve los textos tal como se muestran («Fecha de
  entrega: 13 oct»); toda la interpretación (fechas, estados, categorías) está en Python y se prueba
  allí.

### R12. Del navegador al disco

- **Decisión**: el extractor no devuelve el JSON a la conversación: lo descarga como fichero
  (`alfabeta-captura-<ejecucion>-<clase>-<marca>.json`, con el `ejecucion` que Claude le pasa al inyectarlo) a la carpeta de descargas, igual que la captura de Science
  Bits descarga sus zips, y `python -m alfabeta descargas recoger` lo mueve a `datos/capturas/`.
- **Motivo**: cientos de elementos por clase no deben pasar por el contexto de Claude; un fichero se
  puede guardar, comparar y usar como prueba.

### R13. Guardarraíl de datos personales

- **Decisión**: `python -m alfabeta guardarrail` revisa los ficheros del cambio (gancho de pre-commit) o
  todo el repositorio (CI). Detectores genéricos: correos (salvo `example.org` y `example.com`), rutas
  de usuario e identificadores con forma de Classroom, de Drive o de cuaderno (UUID) (excluidos los ficheros de bloqueo de
  dependencias, `uv.lock` y `package-lock.json`). Los marcadores entre `<…>` y los ids sintéticos
  `sint-<n>` de las páginas de prueba no cuentan. Detectores nominales: los valores identificativos de
  las configuraciones reales presentes en el Mac (el `id` del alumno, `nombre_visible`, `cuenta`,
  `raiz`, `clase_classroom`) y los ids de Classroom y Drive que guardan sus `datos/decisiones.json` y
  `datos/estado.json`, sin mostrarlos nunca; los títulos de temas del libro no son datos
  personales y no se buscan. Como el repositorio es público, lo que está en un commit ya está
  publicado: además del árbol, T000 (a mano, antes de que exista) y T059 (`guardarrail --historia`) pasan los detectores sobre la
  historia (`git log --all -p`).
- **Formas de los ids**: las exactas de Classroom y Drive salen de los patrones de URL que anota S3;
  un identificador de código largo (`snake_case`, `camelCase`, nombres de fichero de prueba) no cuenta.
- **Salidas**: 0 limpio; 1 hallazgo (fichero y línea, sin repetir el dato); 2 los detectores genéricos
  no revisaron ningún fichero; 3 un detector no encuentra el defecto que el propio guardarraíl planta
  en memoria en cada ejecución. Sin configuraciones reales en la máquina (CI, otro colaborador) los
  detectores nominales no corren: se dice en stderr y no cambia la salida.
- **Pruebas**: casos que deben saltar y casos que no, con datos inventados, incluidos un `uv.lock`, rutas con marcador
  `/Users/<alguien>/`, ids `sint-<n>` y claves no identificativas de una configuración
  (`curso_escolar`, `idiomas`).

### R14. Lo que no hace falta en esta épica

- **Llavero**: ningún secreto propio. La sesión de Classroom vive en Chrome y la de Gemini Notebook en
  `nlm`; alfabeta no guarda cookies ni tokens. La capa de secretos queda prevista y vacía.
- **Nota numérica**: no se vio en el detalle de una tarea calificada; `correccion` guarda el estado de
  calificación, la nota si Classroom la muestra al alumno y el comentario (spec, historia 6).
