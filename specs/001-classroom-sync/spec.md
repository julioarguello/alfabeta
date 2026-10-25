# Feature Specification: Los contenidos de cada asignatura, de Classroom al Drive de la familia, con configuración por alumno

**Feature Branch**: `docs/1-spec-001-classroom-sync` (spec dir `001-classroom-sync`)

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "Épica 1 de alfabeta: classroom-sync + estructura de carpetas + configuración por alumno. Problema: el material de estudio de un alumno de secundaria está repartido entre Google Classroom (materiales, adjuntos de tareas, enlaces, anuncios y tareas con fechas, organizados por cada profesor en temas dentro de «Trabajo de clase») y el libro digital (Science Bits). Nada está donde el alumno estudia, y la familia no ve de un vistazo qué hay pendiente. (1) Configuración por alumno: plantilla en el repo → configuración privada fuera del repo → datos y secretos en una carpeta de datos local y el llavero; un segundo alumno solo requiere otra configuración; guardarraíl que impida subir datos reales. (2) Vía de acceso: navegador integrado de la app de escritorio, en solo lectura, con la sesión del alumno; la API está descartada. (3) Reglas: solo lectura en Classroom, datos del menor al mínimo, ninguna herramienta escribe credenciales." Cambio de enfoque del operador (2026-10-25): "No sincronizamos Classroom, sincronizamos los contenidos de la asignatura: primer nivel el curso, luego la asignatura y luego tema o mes; dentro, `classroom` o `sciencebits`, y el nombre del archivo de Classroom incluye la fecha. El scraper recorre Classroom; me interesan sobre todo los recordatorios de lo pendiente y que se descarguen los problemas y ejercicios que les van poniendo y se ubiquen en el sitio correcto del Drive. Quiero una réplica del documento que publica el profesor en nuestro Drive, para combinarla con los libros que vayamos descargando (de momento Science Bits) y que todo junto vaya al cuaderno. Lo hacemos con el Drive familiar; el alumno tiene cuenta personal de Gmail."

## Contexto y alcance

Esta épica es la primera de tres:

1. **Esta**: los contenidos de cada asignatura llegan al Drive de la familia con una estructura común
   a todas las fuentes (Classroom y los libros), más una agenda con exámenes, entregas y lo que se
   publica.
2. **Recordatorios**: la agenda pasa a un calendario con avisos, con un color por categoría (FR-020a;
   colores propuestos en Assumptions),
   y se valora Google Tasks para que el alumno marque como hechas sus entregas desde el calendario.
   Se alimenta de la agenda de esta épica.
3. **«Prepárame el tema»**: todo lo que hay en la carpeta de un tema, de todas las fuentes, va a su
   cuaderno de Gemini Notebook.

Quedan fuera de esta épica los recordatorios, los cuadernos, la sincronización sin la app de Claude
(MCP local, issue #2) y los proveedores de libro distintos de Science Bits.

## Clarifications

### Session 2026-10-25

- Q: ¿El documento de pendientes incluye también los exámenes que el profesor anuncia en el tablón o
  en un material, o solo las tareas con fecha de Classroom? → A: Incluye los exámenes. Todo elemento
  con fecha se clasifica en una categoría cerrada (examen, entrega, cuestionario, material, aviso)
  para que la épica de recordatorios lo distinga a simple vista en el calendario; el documento pasa
  a ser una agenda.
- Q: ¿Qué trae la primera sincronización de una asignatura: todo lo publicado desde el inicio del
  curso o solo desde una fecha reciente? → A: Todo lo del curso escolar en curso, con carácter
  retrospectivo. Lo ya entregado o devuelto aparece como hecho según el estado que muestra Classroom,
  y la agenda abre con una lista de comprobación de lo pendiente, empezando por lo más próximo, para
  que el alumno la revise al llegar a casa (FR-020c).
- Q: ¿Se replican también los ficheros que el propio alumno entregó en cada tarea? → A: Sí, junto al
  enunciado y a la corrección, y bien diferenciados en el Drive: cada tarea es una carpeta con
  `enunciado`, `entrega` y `correccion` (FR-015a).
- Q: ¿Dónde se escribe el material: solo en el Drive familiar o también en la nube anterior
  (Dropbox)? → A: Solo en el Drive familiar, que es el destino de la sincronización. Dropbox queda
  fuera de esta épica: no se lee, no se escribe y no se migra lo que ya hay allí.

## User Scenarios & Testing *(mandatory)*

Los actores son **la familia** (el padre o la madre que configura y lanza alfabeta), **el alumno**
(inicia sesión en Classroom y estudia con lo que queda en su carpeta compartida) y **el profesorado**
(publica en Classroom; nunca interactúa con alfabeta).

### User Story 1 - Lo que publica el profesor, replicado en la carpeta de su tema o de su mes (Priority: P1)

La familia pide sincronizar una asignatura. Con la sesión de Classroom que el alumno ya inició,
alfabeta recorre el «Trabajo de clase» de esa clase y deja una réplica de cada material y de cada
adjunto de tarea (los problemas y ejercicios que manda el profesor) en la subcarpeta `classroom` de su
tema o, si el profesor no le puso tema, de su mes. Cada fichero lleva delante la fecha en que se
publicó. Lo que no es un fichero (un vídeo, un enlace web, un cuestionario) queda anotado con su
enlace. Al terminar, la familia ve un resumen de lo que se ha guardado y de lo que no, y por qué.

**Why this priority**: es lo que el operador pide en primer lugar: el material del profesor en el
sitio correcto, listo para estudiar y para juntarlo con el libro.

**Independent Test**: con una configuración de alumno de prueba y una clase con dos temas, un material
sin tema y adjuntos de los tipos habituales (PDF, documento de Google, presentación, vídeo, enlace,
formulario), sincronizar la asignatura y comprobar elemento a elemento, contra lo que ve el alumno en
«Trabajo de clase», que cada uno está en su carpeta con la fecha delante o anotado con su enlace.

**Acceptance Scenarios**:

1. **Given** una asignatura configurada y la sesión del alumno iniciada, **When** la familia pide
   sincronizarla, **Then** los materiales y los adjuntos de tareas de cada tema están en
   `<tema>/classroom/`, cada elemento con nombre `AAAA-MM-DD - <título>` (fichero o carpeta según
   FR-015), donde la fecha es la de publicación.
2. **Given** un material sin tema publicado en marzo, **When** se sincroniza, **Then** queda en
   `<AAAA-03>/classroom/` de su asignatura.
3. **Given** un adjunto que es un documento, una presentación o una hoja de cálculo de Google,
   **When** se sincroniza, **Then** su réplica queda guardada como PDF.
4. **Given** un elemento con un vídeo, un enlace web o un formulario, **When** se sincroniza,
   **Then** queda una nota con su título, su fecha y sus enlaces, sin descargar nada ni abrir el
   formulario.
5. **Given** la sesión de Classroom caducada o sin iniciar, **When** la familia pide sincronizar,
   **Then** alfabeta se detiene antes de leer nada y pide al alumno que inicie sesión.

---

### User Story 2 - La agenda del alumno: exámenes, entregas y lo que se publica, en un solo documento (Priority: P1)

La familia quiere ver de un vistazo qué tiene el alumno por delante y qué se ha publicado. Tras
sincronizar, hay en la carpeta del curso una agenda con todo lo que tiene fecha en las asignaturas
configuradas, cada cosa con su categoría: exámenes (también los que el profesor solo anuncia en el
tablón o en un material), entregas, cuestionarios, material nuevo y avisos. Lo pendiente lleva su
estado y todo lleva el enlace a su carpeta. El mismo contenido existe en un formato que pueda leer una
herramienta: es la entrada de la épica de recordatorios, que pintará cada categoría de un color.

**Why this priority**: es lo que más interesa al operador (los recordatorios, y los exámenes antes
que nada) y la base de la épica 2.

**Independent Test**: con elementos de prueba de cada categoría (una tarea con fecha esta semana,
otra sin fecha, otra vencida, un cuestionario, un examen que es una tarea, un examen anunciado solo en
el tablón, un material y un aviso), sincronizar y comprobar que la agenda los lista todos, en orden,
cada uno con su categoría y, lo pendiente, con su estado.

**Acceptance Scenarios**:

1. **Given** tareas pendientes en varias asignaturas, **When** se sincroniza, **Then** la agenda las
   lista ordenadas por fecha, con asignatura, categoría, título, fecha, estado, enlace a Classroom y
   enlace a su carpeta.
2. **Given** un anuncio del tablón que dice que hay examen de un tema en una fecha, **When** se
   sincroniza, **Then** la agenda tiene un examen en esa fecha, marcado como «detectado» y con enlace
   al anuncio del que sale.
3. **Given** un examen detectado que la familia corrige (otra fecha, o que no era un examen), **When**
   se vuelve a sincronizar, **Then** la agenda conserva la corrección.
4. **Given** una tarea sin fecha de entrega, **When** se sincroniza, **Then** aparece en un apartado
   «sin fecha» de la agenda.
5. **Given** una tarea cuya fecha ya pasó y que Classroom muestra sin entregar, **When** se sincroniza,
   **Then** aparece marcada como vencida.
6. **Given** un material o un aviso publicado hoy, **When** se sincroniza, **Then** aparece en la
   agenda en su fecha de publicación con su categoría.
7. **Given** exámenes, entregas y cuestionarios, unos ya entregados y otros no, **When** se sincroniza,
   **Then** la agenda abre con la lista «Pendiente», ordenada empezando por lo más próximo y con lo
   sin fecha al final, seguida de «Hecho» con lo entregado marcado.
8. **Given** una agenda generada, ningún cambio en Classroom y ninguna fecha de entrega o de examen
   entre las dos capturas, **When** se vuelve a sincronizar otro día, **Then** los ficheros de la agenda
   no se reescriben. Si una fecha quedó entre las dos, solo cambia la lista de esa entrada (FR-020c).

---

### User Story 3 - Volver a sincronizar sin duplicar y enterándose de los cambios (Priority: P2)

Pasados unos días la familia vuelve a sincronizar. alfabeta solo trae lo nuevo o lo cambiado: un
material nuevo, un adjunto que el profesor ha editado, una fecha de entrega movida. No duplica nada y
no borra nada. Al terminar, la familia ve qué ha cambiado desde la última vez, y queda registro de
cada sincronización.

**Why this priority**: sin esto la carpeta se degrada con cada uso y la familia deja de fiarse de
ella. Depende de la historia 1.

**Independent Test**: sincronizar dos veces seguidas sin cambios y comprobar que la segunda no escribe
nada en la carpeta; después cambiar una fecha, editar un adjunto, añadir y retirar un material en la
clase de prueba, sincronizar y comprobar cada efecto.

**Acceptance Scenarios**:

1. **Given** una sincronización completa reciente, ningún cambio en Classroom y ninguna fecha de
   entrega o de examen entre las dos capturas, **When** se sincroniza
   otra vez, **Then** no se crea, modifica ni borra ningún fichero de la carpeta del alumno y el
   resumen dice «sin cambios».
2. **Given** una fecha de entrega movida por el profesor, **When** se sincroniza, **Then** la agenda
   muestra la nueva fecha y el resumen lo menciona.
3. **Given** un adjunto de un elemento que Classroom muestra modificado después de la última réplica,
   **When** se sincroniza, **Then** su carpeta tiene la versión nueva y la anterior se conserva al lado,
   identificada como anterior. Un adjunto editado solo en Drive, sin marca en Classroom, llega en la
   revisión completa periódica (FR-026).
4. **Given** un material que el profesor retiró de Classroom, **When** se sincroniza, **Then** su réplica
   se conserva, queda marcada como retirada en el registro y el resumen lo menciona.
5. **Given** cualquier sincronización, **When** termina, **Then** el registro guarda cuándo empezó y
   acabó, qué asignaturas recorrió y qué elementos añadió, cambió, marcó como retirados o no pudo
   traer.

---

### User Story 4 - El libro, en la misma estructura (Priority: P2)

La skill de Science Bits deja sus ficheros en la subcarpeta `sciencebits` del mismo tema en el que
Classroom deja los suyos, dentro del Drive familiar.

**Why this priority**: el operador quiere juntar el material del profesor con los libros para
llevarlos al cuaderno (épica 3). Sin una carpeta de tema común, esa combinación no es posible.

**Independent Test**: capturar un tema de prueba con la skill y comprobar que queda en
`<curso>/<asignatura>/<tema>/sciencebits/` del Drive familiar, junto a `classroom/` si existe.

**Acceptance Scenarios**:

1. **Given** la configuración por alumno, **When** se captura un tema de Science Bits, **Then** sus
   ficheros quedan en la subcarpeta `sciencebits` de la carpeta de ese tema.

---

### User Story 5 - Un segundo alumno sin tocar el código, y nada personal en el repositorio (Priority: P2)

La familia quiere usar alfabeta también con el hermano. Copia la plantilla, rellena su configuración
privada y sincroniza: su carpeta, su registro y sus datos quedan separados de los del primer alumno.
Mientras, cualquiera que contribuya al repositorio público tiene un guardarraíl que le impide subir
por despiste un nombre, un correo, una ruta personal o un identificador real.

**Why this priority**: es un principio de la constitución (I, II y III). Se prueba sola, con alumnos
inventados, sin Classroom.

**Independent Test**: dar de alta dos alumnos inventados desde la plantilla y comprobar que el diff del
repositorio está vacío y que sus salidas no se mezclan; plantar datos reales de prueba en un commit y
comprobar que el guardarraíl lo rechaza.

**Acceptance Scenarios**:

1. **Given** la plantilla del repositorio, **When** la familia crea la configuración de un segundo
   alumno, **Then** puede sincronizarlo sin modificar ningún fichero del repositorio.
2. **Given** dos alumnos configurados, **When** se sincroniza uno, **Then** solo se escriben su carpeta,
   su registro y sus datos.
3. **Given** una configuración a la que le falta una clave o que conserva un valor de ejemplo,
   **When** se lanza alfabeta, **Then** se detiene antes de hacer nada y nombra la clave, nunca su
   valor.
4. **Given** un cambio que contiene un valor de la configuración real de un alumno (nombre, correo,
   ruta o título de clase), **When** se intenta hacer commit en un Mac con esa configuración, **Then**
   el gancho de pre-commit, instalado al preparar el entorno, lo rechaza y dice qué fichero y qué
   línea, sin repetir el dato.
5. **Given** un cambio que contiene un correo, una ruta de usuario o un identificador con forma real,
   **When** pasa por la integración continua, **Then** el guardarraíl lo rechaza igual.

---

### User Story 6 - Tablón, entregas del alumno y correcciones (Priority: P3)

Los profesores también publican avisos en el tablón (cambios de examen, material extra) y devuelven
las tareas corregidas con nota y comentario. alfabeta guarda cada anuncio con su fecha, su texto y sus
adjuntos; y en la carpeta de cada tarea, junto al enunciado, guarda lo que entregó el alumno y la
corrección (nota y comentario del profesor), para repasar lo que falló con todo a la vista.

**Why this priority**: útil para los recordatorios y para estudiar, pero el material y las fechas de
entrega viven en «Trabajo de clase». Puede esperar a que lo demás funcione.

**Independent Test**: con dos anuncios de prueba, uno con adjunto, una tarea entregada sin corregir y
otra devuelta con nota y comentario, sincronizar y comprobar que cada cosa está en su sitio y con su
papel reconocible por el nombre, y que no se ha guardado ningún comentario ni nombre de compañeros.

**Acceptance Scenarios**:

1. **Given** anuncios en el tablón, **When** se sincroniza, **Then** cada uno queda en la carpeta de su
   mes con su fecha, su texto y sus adjuntos, sin comentarios de alumnos ni nombres de otras personas.
2. **Given** una tarea que el alumno entregó con ficheros, **When** se sincroniza, **Then** su carpeta
   tiene esos ficheros como `entrega - <nombre>`, junto a los `enunciado - <nombre>` del profesor.
3. **Given** una tarea devuelta con nota y comentario, **When** se sincroniza, **Then** su carpeta tiene
   un `correccion` con el estado de calificación, la nota si Classroom la muestra al alumno, el
   comentario del profesor y la fecha de devolución.
4. **Given** una tarea que el alumno volvió a entregar, **When** se sincroniza, **Then** la entrega
   nueva queda como `entrega` y la anterior se conserva como anterior.

### Edge Cases

- Una clase de Classroom que no corresponde a ninguna asignatura configurada: no se sincroniza, y el
  resumen la lista para que la familia decida si la añade.
- Los temas del profesor y los del libro no van de la mano: otra numeración, otro idioma, un tema del
  profesor que junta dos del libro o uno que no existe en el libro. alfabeta propone y la familia
  confirma (FR-013); hasta entonces, lo de ese tema espera en la carpeta de su mes.
- Un emparejamiento confirmado que resulta equivocado: la familia lo cambia con la orden de
  decisiones y la siguiente sincronización mueve las réplicas a su carpeta correcta, sin duplicarlas
  ni perderlas.
- Dos elementos con el mismo título y la misma fecha en la misma carpeta, o títulos con caracteres no
  válidos o muy largos: el nombre se sanea y, si choca, se desambigua sin perder ninguno.
- Un adjunto de Drive al que el alumno no tiene acceso, borrado o demasiado grande: se anota con su
  enlace y el motivo, y la sincronización sigue.
- Una descarga que no llega o llega incompleta: no se da por guardada; se reintenta en la siguiente
  sincronización.
- Ficheros ajenos en la carpeta de descargas del Mac: alfabeta solo recoge lo que ha pedido.
- La sesión caduca a mitad de la sincronización: se detiene, se registra hasta dónde llegó y la
  siguiente continúa sin duplicar.
- Classroom responde con un desafío anti-robot o un bloqueo: la sincronización de esa fuente se
  detiene y se avisa; no se intenta evitar.
- La carpeta del Drive no está montada o Drive para escritorio está desconectado: alfabeta no escribe
  en ningún otro sitio; se detiene y lo dice.
- Drive para escritorio todavía está subiendo ficheros de la sincronización anterior: no afecta,
  porque alfabeta escribe en la carpeta del disco.
- Dos sincronizaciones del mismo alumno a la vez: la segunda no arranca mientras la primera siga.
- Fechas en los cambios de horario de verano e invierno: la fecha mostrada es la que muestra
  Classroom.

## Requirements *(mandatory)*

### Functional Requirements

**Configuración por alumno**

- **FR-001**: El repositorio MUST contener una plantilla de configuración que documente cada clave con
  un valor de ejemplo (`changeme` en los textos; un número razonable en los números). Sustituye al
  `config.example.json` actual.
- **FR-002**: La configuración de cada alumno MUST vivir fuera del repositorio, y sus datos y secretos
  (registro, estado de sincronización, sesiones, identificadores) en una carpeta de datos local del
  alumno y en el llavero del sistema, fuera de la carpeta que se comparte.
- **FR-003**: Al arrancar, alfabeta MUST validar la configuración contra la plantilla: una clave que
  falta, sobra, cambia de tipo o contiene `changeme` (en cualquier parte del valor) detiene la
  ejecución con un mensaje que nombra la clave y no muestra su valor.
- **FR-004**: Dar de alta otro alumno MUST requerir solo crear su configuración. Cada ejecución MUST
  operar sobre un único alumno, elegido explícitamente.
- **FR-005**: Un guardarraíl MUST rechazar, en cada commit hecho en un Mac con configuraciones de
  alumnos, cualquier fichero que contenga sus valores reales (nombres, correos, rutas personales) o los
  identificadores de Classroom, Drive o cuadernos guardados en sus datos (decisiones y estado); y, en
  cada commit y en la integración continua (que no tiene configuraciones), patrones genéricos de correo, de ruta de
  usuario o de identificador con forma de Classroom, de Drive o de cuaderno (UUID). Los dominios reservados para ejemplos (`example.org`, `example.com`) no cuentan como
  correos reales. MUST tener casos de prueba que demuestren que salta y que la plantilla pasa.

**Lectura de Classroom, en solo lectura**

- **FR-006**: alfabeta MUST leer Classroom con la sesión que el propio alumno inicia en Chrome con la
  extensión de Claude. El navegador integrado de la app queda para una épica posterior, cuando se
  pruebe en él la descarga de adjuntos. Ninguna herramienta MUST escribir credenciales.
- **FR-007**: alfabeta MUST NOT entregar, comentar, marcar como hecho, cambiar ningún estado ni abrir
  un cuestionario o un formulario en Classroom. Las únicas páginas a las que navega son: la página de
  inicio (lista de clases), «Trabajo de clase», el tablón y la página de detalle de cada tarea,
  material o pregunta, que solo se lee. Nunca sigue un enlace a un formulario o a un cuestionario
  (Google Forms o similares) y nunca pulsa un botón del panel «Tu trabajo». Si la interfaz de
  Classroom no muestra las etiquetas esperadas (por ejemplo, porque está en otro idioma), se detiene
  y lo dice en vez de adivinar.
- **FR-008**: alfabeta MUST leer la lista de clases (visibles, ocultas y archivadas) y, por cada clase
  activa del curso escolar en curso y desde su inicio (las archivadas quedan fuera): los temas de
  «Trabajo de clase» y sus elementos (materiales, tareas y preguntas, con título, tipo, tema, fecha de
  publicación, fecha de entrega si la tiene, y adjuntos), el detalle de cada elemento y los anuncios
  del tablón. Las clases ocultas por el alumno se listan en el resumen y solo se sincronizan si la
  familia las asocia a una asignatura.
- **FR-008a**: El estado de una tarea MUST leerse de su página de detalle, no del listado de
  «Trabajo de clase», porque pueden discrepar (un listado que dice «Completada» mientras el detalle
  dice que el profesor la marca como no entregada).
- **FR-009**: alfabeta MUST NOT guardar comentarios de alumnos ni nombres de otras personas: el extractor
  descarta los comentarios de clase y privados y los campos de autor. El texto libre que escribe el
  profesor (instrucciones, anuncios, comentario de corrección) se guarda tal cual; si nombra a alguien,
  alfabeta no lo detecta (límite conocido).
- **FR-010**: El acceso MUST ser el de un alumno navegando: una clase cada vez, al menos 2 segundos
  (con variación aleatoria) entre dos páginas o descargas, y sin evasión. Ante un desafío anti-robot
  (CAPTCHA, página intermedia de verificación, error de demasiadas peticiones), la sincronización de
  esa fuente deja de navegar y se avisa a la familia; la ejecución termina `detenida` con motivo
  `desafio` si aún no había capturado ninguna clase, o `parcial` con ese motivo, aplicando las ya
  capturadas, si ya las había (data-model, «Ejecución»).

**Estructura de la carpeta del alumno**

- **FR-011**: Cada alumno MUST tener una carpeta raíz propia de alfabeta dentro del Drive de la
  familia, nunca la raíz de «Mi unidad», que ya tiene contenido del alumno. Vive en la carpeta que
  Drive para escritorio monta en el Mac; alfabeta solo escribe en esa carpeta del disco y la
  sincronización con la nube la hace Drive para escritorio.
- **FR-012**: Dentro de la raíz, la estructura MUST ser común a todas las fuentes:
  `<curso>/<asignatura>/<Tema NN - título | Tema PNN - título del profesor | AAAA-MM>/<fuente>/`, con
  `classroom` y `sciencebits`
  como fuentes de esta épica. El primer nivel es el curso escolar (`2026-2027`), como hoy en
  Science Bits.
- **FR-013**: Solo se sincroniza una clase asociada a una asignatura configurada: alfabeta propone
  la asociación por el título de la clase que figura en la configuración, la familia la confirma una
  vez y desde entonces vale el identificador de la clase, no su título. Las carpetas de tema MUST
  llamarse como el tema del libro (`Tema NN - <título>`) cuando la asignatura tiene libro (los temas
  del libro son las carpetas `Tema NN - <título>` que ya tienen la subcarpeta de su libro en el Drive), y cada tema
  del profesor MUST emparejarse con ellas así:
  - alfabeta propone el emparejamiento a partir de todo lo que tiene: el número, el título en
    cualquiera de los idiomas del alumno, el contenido de los elementos y el orden en que se publican.
    Cada propuesta dice por qué y con qué seguridad (alta, media o baja).
  - La familia confirma o rechaza cada emparejamiento nuevo una vez, y puede cambiar uno confirmado.
    Rechazar un emparejamiento significa que ese tema del profesor no está en el libro: pasa a su
    propia carpeta `Tema PNN`. Un tema rechazado se vuelve a proponer solo si cambia su título o
    aparece en el Drive un tema del libro nuevo; la familia también puede cambiar una decisión
    rechazada.
    Las decisiones se guardan en la carpeta de datos del alumno, ligadas al identificador del tema en
    Classroom, de modo que si el profesor lo renombra el emparejamiento se mantiene.
  - Varios temas del profesor MAY ir al mismo tema del libro.
  - Si un tema del profesor abarca varios del libro, alfabeta propone el tema de cada elemento por su
    contenido, y la familia lo confirma igual.
  - Un tema del profesor sin equivalente en el libro (repaso, proyecto, introducción) y cualquier tema
    de una asignatura sin libro tienen su propia carpeta `Tema PNN - <título del profesor>`, donde `NN`
    es el orden del tema en «Trabajo de clase» en la ejecución que coloca por primera vez algo de ese
    tema (se guarda en las decisiones y no se recalcula si el profesor reordena) y la `P` lo distingue
    de los temas del libro. En una asignatura sin libro no hay nada que confirmar.
  - Mientras un emparejamiento esté sin confirmar, sus elementos no se mueven de sitio: se sincronizan
    en la carpeta de su mes y el resumen pide la confirmación.
- **FR-014**: Un elemento sin tema y un anuncio MUST ir a la carpeta del mes de su fecha de
  publicación (`AAAA-MM`).
- **FR-015**: Dentro de `classroom/`, cada elemento MUST llevar delante su fecha de publicación,
  `AAAA-MM-DD - <título del elemento>`, y su forma MUST depender de su tipo:
  - un **material** con un solo fichero, sin enlaces y sin descripción es ese fichero; con varios
    ficheros, con enlaces o con descripción, es una carpeta con sus ficheros, una nota `descripcion`
    con su texto si lo tiene y una nota `enlaces` si tiene enlaces;
  - un **aviso** es una nota `.md` con su texto o, si tiene adjuntos, una carpeta con la nota y los
    adjuntos; lleva `aviso` tras la fecha (`AAAA-MM-DD - aviso - <resumen>`), donde `<resumen>` son
    las primeras palabras del anuncio, saneadas y cortadas a 60 caracteres;
  - una **tarea** o una **pregunta** (también una que es examen o cuestionario) es siempre una carpeta,
    aunque solo tenga un adjunto, para que su entrega y su corrección se añadan sin mover nada; sus
    instrucciones o el texto de la pregunta van en `enunciado.md`;
  - un **material** sin ficheros ni enlaces, solo con texto, es una nota `AAAA-MM-DD - <título>.md`
    (esta regla gana a la del material con descripción).
- **FR-015a**: Dentro de la carpeta de una tarea, cada fichero MUST llevar delante su papel, con
  nombres fijos sin acentos: `enunciado - <nombre>` (lo que adjunta el profesor), `entrega - <nombre>`
  (lo que entregó el alumno), `correccion` (nota, comentario del profesor y fecha de devolución) y
  `enlaces` (vídeos, enlaces y formularios, con título y enlace).
- **FR-015b**: Una versión sustituida (un adjunto que el profesor editó, una entrega repetida) MUST
  conservarse junto a la vigente como `<nombre> (anterior AAAA-MM-DD)`.
- **FR-015c**: Los nombres MUST ser válidos en el sistema de ficheros y en Drive, de 255 bytes UTF-8
  como máximo, y únicos en su carpeta sin perder ningún elemento; los títulos del profesor conservan
  sus acentos.

Ejemplo de la estructura resultante (nombres inventados):

```text
2026-2027/
├── agenda.md   agenda.json
└── <asignatura>/
    ├── Tema 02 - <título del libro>/
    │   ├── sciencebits/
    │   └── classroom/
    │       ├── 2026-10-14 - Ficha de gases.pdf
    │       ├── 2026-10-16 - Vídeos y apuntes/
    │       │   ├── Apuntes.pdf
    │       │   └── enlaces.md
    │       └── 2026-10-20 - Problemas tema 2/
    │           ├── enunciado - Problemas.pdf
    │           ├── entrega - Respuestas.pdf
    │           └── correccion.md
    └── 2026-11/
        └── classroom/
            └── 2026-11-03 - aviso - Cambio de fecha del examen.md
```

**Réplica de lo que publica el profesor y de lo que entrega el alumno**

- **FR-016**: Un adjunto que es un fichero (PDF, documento de Office, imagen) MUST replicarse tal cual;
  un documento, una presentación o una hoja de cálculo de Google MUST replicarse como PDF.
- **FR-016a**: alfabeta MUST replicar los ficheros que el alumno entregó en cada tarea, descargándolos
  como cualquier otro adjunto y sin tocar la entrega en Classroom.
- **FR-017**: Un vídeo, un enlace web o un formulario MUST anotarse en la nota `enlaces` del elemento
  con título, fecha y enlace, sin descargarse.
- **FR-018**: Una réplica solo MUST darse por guardada cuando el fichero completo está en su carpeta.
  alfabeta recoge de la carpeta de descargas del Mac solo los ficheros que ha pedido.
- **FR-019**: Un adjunto que no se puede traer MUST anotarse con su enlace y el motivo en la nota
  `enlaces` de su elemento (y en el registro), sin detener la sincronización.

**Agenda**

- **FR-020**: Cada sincronización MUST actualizar, en la carpeta del curso, una agenda legible y otra
  para herramientas con todo elemento con fecha de las asignaturas configuradas: asignatura,
  categoría, título, fecha (de entrega, de examen o de publicación) o «sin fecha», estado si es algo
  pendiente (pendiente, entregada, devuelta, vencida sin entregar, falta según el profesor), enlace a
  Classroom y a la carpeta donde está su réplica. El contenido de la agenda MUST depender solo de lo
  sincronizado y de las decisiones de la familia, nunca del día en que se genera, y los ficheros de la
  agenda MUST reescribirse solo si su contenido cambia (FR-025).
- **FR-020a**: Cada elemento de la agenda MUST tener exactamente una categoría de esta lista cerrada:
  - **examen**: una prueba, sea una tarea de Classroom o algo que el profesor anuncia en el tablón o
    en un material;
  - **entrega**: una tarea a entregar que no es examen;
  - **cuestionario**: una pregunta de Classroom, o una tarea cuyo único adjunto es un formulario
    (`clase_adjunto` = `formulario`). Su página de detalle de
    Classroom solo se lee (FR-007); nunca se responde ni se sigue el formulario o cuestionario
    enlazado (constitución IV: eso es abrir un cuestionario);
  - **material**: lo publicado sin entrega (apuntes, ejercicios de práctica), en su fecha de
    publicación;
  - **aviso**: un anuncio del tablón que no es examen.

  Si un elemento encaja en varias, gana la primera de este orden: examen, cuestionario, entrega,
  material, aviso (una pregunta o una tarea que es un examen es `examen`).
- **FR-020b**: Un examen que alfabeta deduce de un texto (anuncio, título o descripción de un
  material, en cualquiera de los idiomas del alumno) MUST marcarse como «detectado», con su fecha
  resuelta respecto a la de publicación y el enlace al elemento del que sale. Aparece en la agenda en
  cuanto Claude lo propone, sin esperar confirmación. Es una entrada propia de la agenda (un elemento
  que anuncia varios exámenes da una entrada por examen): el elemento de origen conserva su propia
  entrada y su categoría. Descartarlo es una corrección de la familia. Si no puede resolver
  la fecha, aparece sin fecha. La familia MAY corregir un examen detectado (fecha, categoría o
  descartarlo), y la corrección MUST conservarse en las sincronizaciones siguientes.
- **FR-020c**: El estado de lo pendiente MUST ser el que muestra Classroom en cada sincronización, de
  modo que lo publicado antes de la primera sincronización y ya entregado aparezca como hecho. La
  agenda legible MUST abrir con una lista de comprobación «Pendiente», ordenada por fecha empezando por
  la más próxima y con lo «sin fecha» al final, y seguir con «Hecho», con lo entregado marcado,
  ordenado por fecha de entrega o de examen de la más reciente a la más antigua, con lo sin fecha al
  final:

  | Estado o caso | Lista |
  |---|---|
  | `pendiente`, `vencida`, `falta_segun_profesor` | Pendiente |
  | `entregada`, `devuelta` | Hecho |
  | entrega, cuestionario o examen sin `estado` (texto de estado desconocido, o sin entrega en Classroom) | Pendiente |
  | examen detectado, mientras no exista una captura de su clase posterior a su fecha | Pendiente |
  | examen detectado sin fecha, hasta que la familia lo corrija o lo descarte | Pendiente |
  | examen detectado con una captura de su clase posterior a su fecha | Hecho |
  | examen detectado que la familia descarta | ninguna |
  | examen que es una tarea o una pregunta de Classroom, en `pendiente`, `vencida` o sin `estado`, con una captura de su clase posterior a su fecha (gana a las filas anteriores; `falta_segun_profesor` sigue en Pendiente) | Hecho |
  | `material`, `aviso` | Publicado (apartado informativo por fecha de publicación, de la más reciente a la más antigua, tras «Hecho») |

  «Posterior a su fecha» compara con el instante del examen o, si solo tiene fecha, con el final de ese
  día en `Europe/Madrid`. Ninguna regla usa el día en que se genera la agenda: todas dependen de las capturas y de las
  decisiones (FR-020).
- **FR-021**: Las fechas MUST mostrarse como las muestra Classroom, en hora de `Europe/Madrid`.
  Classroom no muestra el año y usa fechas relativas («Mañana, 8:00»): el año se deduce del curso
  escolar (septiembre a diciembre, el primer año; enero a agosto, el segundo; una captura hecha fuera de
  ese curso escolar detiene la ejecución con `configuracion_invalida`) y las relativas se
  resuelven respecto al momento en que se capturó la página, no al de la ejecución que la aplica. La
  fecha de publicación MUST salir de la fecha de creación (tablón o detalle), nunca de la «última
  modificación» que a veces muestra el listado.

**Repetible y programable**

- **FR-021a**: La sincronización completa de un alumno MUST lanzarse con una sola petición a Claude que
  invoca la skill `classroom-sync` (p. ej. «sincroniza alfabeta para <alumno>») y MUST poder
  programarse (p. ej. a diario) en el Mac de la familia. Una ejecución programada que encuentra la
  sesión del alumno caducada, un desafío anti-robot o el Drive sin montar deja de navegar y avisa a la
  familia, con la misma regla que una interactiva: antes de capturar ninguna clase (o con el Drive sin
  montar), sin escribir en la carpeta del alumno; a mitad, aplica las clases ya capturadas como
  `parcial`. El aviso es el resultado de la tarea programada en la app
  de escritorio de Claude, más una línea en el registro. Si una tarea programada no puede usar el
  navegador o descargar ficheros sin aprobación (spike S2), la ejecución programada se limita a ese
  aviso («toca sincronizar») y la familia lanza la sincronización con la orden única; ese modo
  reducido también cumple este requisito.
- **FR-021b**: Lo que no requiere juicio (estado, identificadores, nombres, estructura, agenda,
  recogida de descargas) MUST dar el mismo resultado en cada repetición. Lo que sí lo requiere
  (proponer emparejamientos de temas, detectar exámenes en un texto) MUST quedar registrado con su
  motivo, y una vez confirmado por la familia no se vuelve a decidir. Un candidato a examen que Claude
  juzga que no anuncia ninguno también queda registrado (`candidato_descartado`) y no se vuelve a juzgar
  salvo que su texto cambie.

**Libros en la misma estructura**

- **FR-022**: La skill de Science Bits MUST leer la configuración por alumno y dejar sus ficheros en
  la subcarpeta `sciencebits` de la carpeta del tema.
- **FR-023**: alfabeta MUST NOT leer ni escribir en la nube anterior (Dropbox). Lo capturado allí antes
  de esta épica queda como está; si se quiere en la estructura nueva, se vuelve a capturar.

**Sincronización incremental y registro**

- **FR-024**: Cada elemento y cada adjunto MUST tener un identificador estable derivado de Classroom.
  Repetir una sincronización MUST NOT duplicar nada.
- **FR-025**: Una sincronización sin cambios MUST NOT escribir nada en la carpeta del
  alumno ni en su estado ni en sus decisiones. «Sin cambios» quiere decir que no cambia Classroom y
  que ninguna fecha de entrega o de examen queda entre la captura anterior y esta: si una queda, la
  entrada cambia de lista (FR-020c) y eso es un cambio. Solo escribe lo que es el registro propio de esa
  ejecución: su línea de registro, sus capturas, su plan, su fichero de bloqueo, los adjuntos que
  recoge en la carpeta de datos (que `aplicar` borra una vez colocados o comprobados idénticos) y el
  borrado de sus capturas más antiguas que `capturas_conservadas` (nunca en la carpeta del alumno).
- **FR-026**: alfabeta MUST detectar y aplicar elementos nuevos, adjuntos editados, entregas nuevas o
  repetidas, devoluciones y fechas movidas. Un adjunto ya replicado se vuelve a descargar solo si
  Classroom muestra que su elemento se modificó después de la última réplica, si cambia su nombre o
  su tipo, o en la revisión completa periódica (`revision_completa_dias`; valor de la plantilla: 7). La
  revisión completa se cuenta desde la última ejecución del registro que la hizo (la primera
  sincronización lo es); si encuentra los
  mismos bytes no escribe nada fuera de su registro propio (FR-025). La versión sustituida se conserva
  según FR-015b.
- **FR-027**: Un elemento retirado de Classroom MUST conservarse, marcarse como retirado en el registro
  y mencionarse en el resumen. Solo se marca como retirado si la captura de su clase está completa:
  una captura cortada (sesión caducada, error) no retira nada. alfabeta MUST NOT borrar nada de la
  carpeta del alumno.
- **FR-028**: Cada sincronización MUST dejar un registro con inicio, fin, asignaturas recorridas y
  elementos añadidos, cambiados, retirados o no traídos, y terminar con un resumen para la familia.
- **FR-029**: El fallo de una asignatura o de un adjunto MUST NOT abortar el resto. Si se interrumpe,
  la siguiente sincronización continúa sin duplicar.
- **FR-030**: Dos sincronizaciones del mismo alumno MUST NOT ejecutarse a la vez: el bloqueo se toma
  al empezar y se mantiene durante toda la ejecución, también la parte del navegador. Cada paso de la
  ejecución lo renueva; si pasan `bloqueo_inactividad_minutos` sin renovarlo (la ejecución murió), se
  libera solo y queda una línea `detenida` en el registro. Como todos los alumnos comparten un
  navegador y una carpeta de descargas, la parte del navegador y las descargas de dos alumnos, o de
  dos skills de alfabeta (la de Classroom y la de un libro), tampoco MUST ejecutarse a la vez. Si la carpeta del Drive no está disponible, alfabeta MUST detenerse sin
  escribir réplicas en ningún otro sitio (solo su línea de registro, FR-021a).

**Privacidad**

- **FR-031**: El nombre, el correo o cualquier dato que identifique al alumno MUST NOT aparecer en una
  URL que construya alfabeta, en el registro ni en un mensaje de error. Las rutas se muestran
  relativas a la carpeta raíz del alumno, y la ruta absoluta de la raíz nunca se muestra, porque la
  ruta de montaje de Drive para escritorio lleva el correo de la cuenta.

### Key Entities *(include if feature involves data)*

- **Alumno**: un *tenant*. Su configuración privada (nombre para mostrar, curso, carpeta raíz en el
  Drive de la familia, asignaturas, cuenta de Classroom) y su carpeta de datos local (registro, estado
  de sincronización, decisiones de la familia).
- **Asignatura**: una materia del alumno, con su nombre de carpeta y la clase de Classroom que le
  corresponde.
- **Carpeta de tema o de mes**: el tercer nivel de la estructura. La de tema lleva el emparejamiento
  con el tema del profesor; la de mes recoge lo que no tiene tema.
- **Fuente**: el origen de un contenido (`classroom`, `sciencebits`) y su subcarpeta.
- **Elemento de Classroom**: material, tarea, pregunta o anuncio. Identificador estable, asignatura,
  tema o mes, título, fechas y adjuntos.
- **Réplica**: la copia de un adjunto (fichero o PDF), de una entrega del alumno, de una corrección o
  la nota con sus enlaces, con su papel (`enunciado`, `entrega`, `correccion`, `enlaces`) y su huella
  para detectar cambios.
- **Entrada de agenda**: un elemento con fecha (o sin ella) y su categoría (examen, entrega,
  cuestionario, material, aviso); si es algo pendiente, su estado; si se dedujo de un texto, la marca
  «detectado», su origen y la corrección de la familia si la hay.
- **Sincronización**: una ejecución sobre un alumno, con su registro y su resumen.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras la primera sincronización de una asignatura, el 100 % de los elementos de su
  «Trabajo de clase» está replicado en su carpeta o anotado con enlace y motivo, comprobado elemento a
  elemento contra lo que ve el alumno en Classroom.
- **SC-002**: Una segunda sincronización sin cambios (FR-025) modifica cero ficheros de la carpeta del alumno.
- **SC-003**: Una fecha de entrega movida, un material nuevo o un adjunto de un elemento que Classroom
  muestra modificado aparecen en la carpeta y en el resumen en la primera sincronización posterior al
  cambio; un adjunto editado solo en Drive, o de un elemento que no muestra marca de modificación (una
  tarea con fecha de entrega), como tarde en la revisión completa periódica.
- **SC-004**: La familia ve todos los exámenes y entregas de todas las asignaturas en una única agenda
  ordenada por fecha, cada uno con su categoría, sin abrir Classroom.
- **SC-004a**: En el conjunto de prueba, el 100 % de los exámenes anunciados solo en el tablón o en un
  material aparece en la agenda como examen detectado, con enlace a su origen.
- **SC-005**: Para cualquier tema con material de Classroom y del libro, las dos fuentes están en la
  misma carpeta de tema.
- **SC-006**: Dar de alta un segundo alumno deja el repositorio sin ningún cambio.
- **SC-007**: El guardarraíl rechaza el 100 % de los casos de prueba con datos reales plantados (nombre,
  correo, ruta, identificador) y acepta la plantilla.
- **SC-008**: Cero cambios de estado en Classroom durante cualquier sincronización: ninguna entrega,
  comentario, tarea marcada ni cuestionario abierto.
- **SC-008a**: En el conjunto de prueba, en el 100 % de las carpetas de tarea se distingue por el
  nombre qué es del profesor, qué entregó el alumno y qué es la corrección.
- **SC-009**: Buscar el nombre y el correo del alumno en el registro y en los mensajes de una
  sincronización completa da cero coincidencias. La orden nunca imprime `nombre_visible`: solo Claude
  lo usa al hablar con la familia en el chat.

## Assumptions

- La sincronización corre en el Mac de la familia desde la app de escritorio de Claude, a demanda o
  programada (FR-021a), con la sesión de Classroom que el alumno inicia en el navegador. Una
  sincronización sin la app de Claude es la épica del MCP local (issue #2).
- Observado el 2026-10-25 en el Classroom del alumno, en solo lectura: los temas del profesor no
  coinciden con los del libro (un tema del profesor agrupa material de varios temas del libro y otro
  no existe en el libro), hay asignaturas con temas numerados y una carpeta de exámenes guardados,
  los exámenes se anuncian en el tablón en el idioma de la clase, hay clases ocultas, y el Drive
  personal del alumno ya tiene carpetas propias.
- El Drive familiar está montado en el Mac con Drive para escritorio. Qué cuenta personal de Google
  es (la familia confirma cuál al montarlo en el plan), y en qué carpeta vive la raíz de cada alumno,
  es configuración.
- Si el alumno no es el dueño de esa cuenta, la familia comparte una vez, desde Drive, su carpeta raíz
  con la cuenta personal de Gmail del alumno. alfabeta no gestiona permisos de Drive.
- La API de Classroom no está disponible para la cuenta escolar del alumno
  (`docs/classroom-investigacion.md`); todo se lee de lo que el alumno ve.
- Los títulos de temas y elementos se conservan en el idioma en que los escribe el profesor.
- Qué va al cuaderno de cada tema lo decide la épica 3; la propuesta es el material del profesor y
  los libros, sin las entregas ni las correcciones del alumno.
- El «Trabajo de clase» de dos asignaturas se observó en solo lectura (research del plan); el del
  resto de clases se recorre en la primera sincronización y FR-013 se contrasta con lo que haya.
- La interfaz de Classroom de la cuenta del alumno está en castellano; los textos de fechas y estados
  se interpretan en ese idioma. Otro idioma de interfaz detiene la sincronización (FR-007) hasta que
  se añada.
- La ubicación exacta de la configuración privada y de la carpeta de datos local la fija el plan,
  siempre fuera del repositorio y fuera de la carpeta compartida.
- La cuenta del alumno para el calendario y los avisos se decide en la épica de recordatorios. Allí
  se fija también el color de cada categoría; la propuesta es examen rojo, entrega naranja,
  cuestionario morado, material azul y aviso verde, con la asignatura en el título del evento, porque
  un evento de calendario admite un solo color. También se valora allí Google Tasks para las entregas
  (el alumno las marca como hechas y aparecen en el calendario), comprobando en qué cuenta viven, si
  admiten color y si la familia puede verlas. Esa épica es también la que muestra «hoy» y «esta
  semana», que dependen del día.

## Dependencies

- La app de escritorio de Claude con acceso a los ficheros del Mac.
- Chrome con la extensión de Claude y la sesión de Classroom del alumno en él.
- Drive para escritorio con la cuenta de la familia, ya instalado en el Mac.
- La skill `sciencebits-a-notebooklm`, que pasa a leer la configuración por alumno y a escribir en la
  estructura común (FR-022).
