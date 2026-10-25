# Data Model: spec 001

Entidades del dominio (dataclasses inmutables en `src/alfabeta/modelo.py`) y los ficheros donde
persisten. Los identificadores de Classroom son opacos: se guardan, en mensajes solo aparecen abreviados y nunca
aparecen en el repositorio.

## Alumno

Configuración privada en `~/.alfabeta/<alumno>/config.toml` (contrato:
[config-template.toml](contracts/config-template.toml)). Los campos usan los nombres de la plantilla.

| Campo | Tipo | Regla |
|---|---|---|
| `id` | texto | Alias opaco que elige la familia, nunca el nombre del alumno; minúsculas ASCII; nombre de su carpeta en `~/.alfabeta/`; se pasa con `--alumno` |
| `alumno.nombre_visible` | texto | Con él se dirige Claude a la familia en el chat; la orden `python -m alfabeta` nunca lo imprime, ni va al registro, a URLs ni al Drive (SC-009) |
| `alumno.curso_escolar` | texto `AAAA-AAAA` | Primer nivel de la estructura |
| `alumno.nivel` | texto | Para los nombres de cuaderno (épica 3): es el `<nivel>` de «`<nivel>. <asignatura>. Tema NN - <título>`» |
| `alumno.idiomas` | lista | Idiomas en que pueden venir títulos y anuncios |
| `classroom.cuenta` | correo | Se compara en local con el botón de cuenta; nunca va en una URL |
| `drive.raiz` | ruta | Carpeta propia de alfabeta dentro del Drive montado; debe existir y no ser la raíz de «Mi unidad»; nunca se muestra |
| `descargas.carpeta` | ruta | Donde Chrome deja las descargas |
| `sincronizacion.revision_completa_dias` | entero ≥ 1 | Cada cuántos días se vuelven a descargar todos los adjuntos |
| `sincronizacion.bloqueo_inactividad_minutos` | entero ≥ 1 | Tras cuántos minutos sin renovar se libera el bloqueo de una ejecución muerta |
| `sincronizacion.capturas_conservadas` | entero ≥ 1 | Capturas que se conservan por clase |
| `herramientas.carpeta` | ruta | Donde las skills copian sus scripts de trabajo; fuera de Dropbox y de la carpeta compartida |
| `herramientas.repositorio` | ruta | Clon de alfabeta desde el que las skills ejecutan `uv run --project <repositorio> python -m alfabeta` en el Mac |
| `sciencebits.url` | URL | Página de clases de Science Bits |
| `sciencebits.idiomas` | lista | Idiomas en que se captura cada tema; el primero da el título de la carpeta |
| `cuaderno.activado` | booleano | Si se crea el cuaderno de cada tema |
| `asignaturas` | lista de `Asignatura` | Al menos una |
| `programacion.diaria` | hora `HH:MM` o vacío | Hora de la tarea programada; vacío = solo a demanda |

## Asignatura

| Campo | Tipo | Regla |
|---|---|---|
| `carpeta` | texto | Nombre de la carpeta de la asignatura (p. ej. `FyQ`) |
| `clase_classroom` | texto | Título de la clase en Classroom; solo para proponer la asociación |
| `libro` | texto o vacío | Proveedor de libro (`sciencebits`) y nombre de su subcarpeta |
| `clase_libro` | texto o vacío | Nombre de la clase en la plataforma del libro (p. ej. la de Science Bits) |

`[sciencebits] url` e `idiomas` admiten `""` y `[]` cuando ninguna asignatura tiene `libro = "sciencebits"`.

Los temas del libro no se configuran: son las carpetas `Tema NN - <título>` de la asignatura que ya
tienen la subcarpeta de su libro en el Drive.

La asociación efectiva entre una asignatura y su clase es una `Decision` de tipo `clase_asociada`,
ligada al id de la clase; el título solo sirve para proponerla.

## Fuente

Protocol en `src/alfabeta/fuentes.py`: `nombre` (la subcarpeta: `classroom` o el valor de `libro`) y
`elementos()` normalizados. Implementaciones: `FuenteClassroom` (capturas del extractor) y
`FuenteLibro` (directorio con el resultado de un proveedor de libro).

## Decisión (en `datos/decisiones.json`)

| Campo | Tipo | Regla |
|---|---|---|
| `tipo` | `clase_asociada` · `emparejamiento_tema` · `emparejamiento_elemento` · `examen_detectado` (propuesta de Claude) · `candidato_descartado` (Claude juzga que un candidato a examen no anuncia ninguno; origen = el elemento) · `correccion_examen` (de la familia) · `numero_tema_profesor` (lo escribe `aplicar` en la ejecución que coloca por primera vez algo de un tema `Tema PNN`: en una asignatura con libro, tras rechazarse su emparejamiento; en una sin libro, sin confirmación) | `emparejamiento_elemento` lo propone Claude para cada elemento de un tema del profesor que abarca varios temas del libro, y prevalece sobre la decisión de su tema |
| `origen` | id de Classroom (clase, tema o elemento); para `examen_detectado` y `correccion_examen`, `<elemento>#examen-<k>`, donde Claude asigna `k` = 1, 2… al proponer (el clasificador da un solo candidato por elemento) | Clave única por `(tipo, origen)` entre las no sustituidas; una propuesta repetida no escribe |
| `destino` | asignatura, carpeta de tema, examen (`fecha`, `motivo`), corrección (`fecha`, `categoria`, `descartado`) o el `NN` de un tema `Tema PNN` | |
| `motivo` | texto | Lo que llevó a la propuesta o a la corrección |
| `seguridad` | `alta` · `media` · `baja` | Solo en propuestas |
| `estado` | `propuesta` → `confirmada` · `rechazada`; `confirmada` o `rechazada` → `sustituida` | Solo `confirmada` cuenta, salvo `examen_detectado` (aparece en la agenda como detectado) y `candidato_descartado` (el candidato deja de estar pendiente), que cuentan desde que son `propuesta`; la familia puede rechazar un `candidato_descartado` y el candidato vuelve a pendientes. Un `(tipo, origen)` con una decisión no sustituida no se vuelve a proponer; una `rechazada`, solo si su origen muestra una modificación posterior al rechazo. `examen_detectado` no se rechaza: se descarta con una `correccion_examen` |
| `fecha` | fecha | De la última transición |
| `huella_origen` | SHA-256 o vacío | Del texto del que se dedujo un `examen_detectado` o un `candidato_descartado`; si el texto cambia, el candidato vuelve a pendientes y la decisión anterior pasa a `sustituida`, salvo que la familia la corrigiera (`correccion_examen`) |

## Elemento de Classroom

| Campo | Tipo | Regla |
|---|---|---|
| `id` | id de Classroom | De la URL de detalle; estable |
| `clase` | id de Classroom | |
| `tema` | id de tema o vacío | Vacío o sin emparejar confirmado → carpeta de mes |
| `tipo` | `tarea` · `material` · `pregunta` · `anuncio` | |
| `titulo` | texto | Tal como lo escribe el profesor |
| `publicado` | fecha | De «Fecha de creación»; nunca de «Última modificación» |
| `modificado` | fecha o vacío | De «Última modificación»; dispara una nueva descarga de sus adjuntos |
| `entrega` | fecha-hora o vacío | Resuelta por `ResolvedorFechas` respecto al momento de la captura |
| `estado` | `pendiente` · `entregada` · `devuelta` · `vencida` · `falta_segun_profesor` · vacío | Del detalle (tabla de abajo); solo tareas y preguntas |
| `descripcion` | texto | Instrucciones o texto del anuncio |
| `adjuntos` | lista de `Adjunto` | |
| `entrega_alumno` | lista de `Adjunto` | Ficheros que entregó el alumno |
| `correccion` | `Correccion` o vacío | |

### Estado desde los textos del detalle

| Texto de «Tu trabajo» | Aviso del detalle | `estado` |
|---|---|---|
| «Asignado» o «Falta» y fecha de entrega futura o sin fecha | — | `pendiente` |
| «Asignado» o «Falta» y fecha de entrega pasada | — | `vencida` |
| «Entregado» o «Entregado con retraso» | — | `entregada` |
| «Calificado» o «Devuelto» | — | `devuelta` |
| cualquiera | «El profesor ha indicado que falta esto» | `falta_segun_profesor` (gana a todo lo anterior) |
| otro texto | — | la ejecución lo registra como desconocido y deja `estado` vacío |

La comparación «pasada/futura» usa el momento de la captura.

## Adjunto

| Campo | Tipo | Regla |
|---|---|---|
| `id` | id de Drive, URL de YouTube o URL | Estable |
| `clase_adjunto` | `fichero` · `documento_google` · `video` · `enlace` · `formulario` | Los tres últimos no se descargan |
| `nombre` | texto | Nombre mostrado |
| `papel` | `enunciado` · `entrega` · `material` | |

## Réplica (en `datos/estado.json`)

| Campo | Tipo | Regla |
|---|---|---|
| `fuente` | nombre de la fuente | `classroom` o el del libro |
| `elemento`, `adjunto` | ids | Clave única |
| `papel` | `enunciado` · `entrega` · `correccion` · `enlaces` · `descripcion` · `material` · `aviso` | Prefijo del nombre en carpetas de tarea |
| `ruta` | ruta relativa a `drive.raiz` | Calculada por `Ubicador`; nombre de 255 bytes UTF-8 como máximo |
| `huella` | SHA-256 | Cambia → versión nueva; la anterior pasa a `<nombre> (anterior AAAA-MM-DD)` |
| `version` | entero | Empieza en 1 |
| `modificado_visto` | fecha o vacío | La marca de modificación del elemento cuando se hizo la réplica |
| `retirado` | fecha o vacío | El elemento ya no está en una captura completa de su clase; la réplica se conserva |

Además de las réplicas, `estado.json` guarda de cada elemento su última versión normalizada (`Elemento`,
con su categoría), que solo se reescribe si cambia. El `capturado` de la última captura de cada clase no
se guarda en el estado: se lee de la más reciente de `datos/capturas/` (siempre queda al menos una,
`capturas_conservadas` ≥ 1), que es registro propio de la ejecución (FR-025). De los dos salen la agenda
y las reglas de FR-020c.

## Corrección

`estado_calificacion` (`calificado`, `devuelto`), `nota` (texto o vacío: solo si Classroom la muestra al
alumno), `puntos_maximos`, `comentario_profesor`, `fecha_devolucion` (de `texto_devolucion` de la
captura, o vacía si Classroom no la muestra). Describe la devolución; el estado
de la tarea sigue siendo el de `Elemento.estado`. Se escribe como `correccion.md` en la carpeta de la
tarea.

## Entrada de agenda

Contrato: [agenda.schema.json](contracts/agenda.schema.json).

| Campo | Tipo | Regla |
|---|---|---|
| `elemento` | id | Un examen detectado es `<elemento>#examen-<k>`; su elemento de origen conserva su propia entrada |
| `asignatura` | texto | Carpeta de la asignatura |
| `lista` | `pendiente` · `hecho` · `publicado` | Según la tabla de FR-020c; material y aviso van a `publicado` |
| `solo_fecha` | booleano | `true` si Classroom no da hora |
| `categoria` | `examen` · `entrega` · `cuestionario` · `material` · `aviso` | Exactamente una; precedencia examen > cuestionario > entrega > material > aviso |
| `titulo` | texto | |
| `fecha` | fecha-hora, fecha o vacío | Vacío → al final de «Pendiente» |
| `estado` | como en Elemento, o vacío para material y aviso | |
| `detectado` | booleano | `true` si el examen sale de un texto |
| `origen` | id del elemento del que se dedujo | Solo si `detectado` |
| `corregido` | booleano | `true` si la familia lo corrigió |
| `enlace_classroom` | URL | Sin `/u/<n>` (el índice no es estable); la agenda legible indica abrirlo con la cuenta escolar |
| `carpeta` | ruta relativa o vacío | Vacío si el elemento no tiene réplica |

## Ejecución (en `datos/registro.jsonl`)

Una línea por ejecución: `inicio`, `fin`, `modo` (`interactiva` · `programada`, de `bloqueo tomar --modo`), índice `/u/<n>` usado (de `indice_cuenta` en la captura de clases),
`clases` recorridas, contadores `anadidos`, `cambiados`, `retirados`, `no_traidos` (con motivo por
elemento, sin datos del alumno), `estados_desconocidos`, `decisiones_pendientes`, `revision_completa`
(booleano: la próxima revisión completa se cuenta desde la última línea que la tiene), `resultado` (`ok` ·
`parcial` · `detenida`) y `motivo` (de la detención o de una `parcial`. Una parada en el navegador —sesión caducada, desafío o interfaz inesperada— antes de capturar ninguna clase deja la ejecución `detenida` sin escribir en la carpeta del alumno; después de capturar al menos una, `aplicar` aplica las ya capturadas, deja sin aplicar la de la captura `parada` y el resultado es `parcial` con ese motivo. Igual en los dos modos. Drive sin montar, bloqueo ocupado o configuración inválida siempre detienen antes de escribir) (`sesion_caducada`, `desafio`,
`interfaz_inesperada`, `drive_no_montado`, `bloqueo_ocupado`, `bloqueo_no_tomado`,
`configuracion_invalida`, `inactividad`). Cada línea lleva el `ejecucion` de su bloqueo. `libro colocar` escribe una línea
más corta: `tipo: libro`, `instante`, `ejecucion`, `fuente`, `tema` y `resultado` (`colocado` · `sin_cambios`).
`registro cuaderno` escribe otra: `tipo: cuaderno`, `instante`, `ejecucion`, `tema` y `resultado` (`creado` ·
`sin_cambios` · `fallo` · `desactivado`), con `motivo` si falla (texto corto, sin datos del alumno). `sin_cambios`: el cuaderno ya existía y
no faltaba ninguna fuente.

## Transiciones

- Decisión: `propuesta` → `confirmada` | `rechazada`; `confirmada` o `rechazada` → `sustituida`
  cuando la familia la cambia. Una rechazada genera una propuesta nueva solo si su origen muestra una
  modificación posterior al rechazo; para un tema, si cambia su título o aparece en el Drive un tema
  del libro nuevo.
- Réplica: `nueva` → `vigente` → (`sustituida` → `anterior`) | (`retirada`). Nunca `borrada`. Un
  cambio de emparejamiento mueve la réplica sin cambiar su versión.
- Entrada de agenda: el estado se recalcula en cada ejecución desde el detalle de Classroom; una
  corrección de la familia sobre un examen detectado prevalece sobre lo detectado.
