# alfabeta Constitution

alfabeta reúne el material de estudio de un alumno de secundaria que hoy está repartido entre el
libro digital del centro y Google Classroom. Lo deja por asignatura y tema en una carpeta del
alumno que se sincroniza con su nube, crea un cuaderno de Gemini Notebook por tema y lleva
entregas y exámenes a un calendario que comparten el alumno y su familia. Lo opera una familia en su
propio Mac, con la app de escritorio de Claude. El repositorio es público.

## Core Principles

### I. El alumno es configuración (NON-NEGOTIABLE)

- Ningún alumno, centro, curso concreto ni cuenta MUST aparecer en el código, en los tests ni en
  ramas lógicas. Solo existen en su configuración.
- Dar de alta un segundo alumno (un hermano, por ejemplo) MUST requerir solo crear otra
  configuración, sin tocar código.
- Los datos y las salidas de un alumno (carpeta, cuadernos, calendario, registro de
  sincronización) MUST quedar separados de los de cualquier otro.

Razón: el primer alumno es el primer *tenant*, no el producto.

### II. Tres capas que nunca se mezclan

| Capa | Qué es | Dónde | ¿Repo? |
|---|---|---|---|
| **Plantilla** | Estructura y valores de ejemplo (`changeme`) que documentan todas las claves | Repo (`template.*`) | Sí, la única |
| **Configuración del alumno** | Nombre, curso, centro, asignaturas, rutas, calendario, cuentas | Fuera del repo o ignorada por git | Nunca |
| **Datos y secretos** | Descargas, capturas, PDF, sesiones y cookies, tokens, ids de cuadernos y de eventos | Carpeta de datos local y llavero del sistema | Nunca |

- La plantilla MUST reflejar línea a línea cada configuración real (*template mirroring*): toda
  clave que lea el código MUST estar declarada en la plantilla, y una clave sin declarar es un error
  al arrancar, no un valor por defecto silencioso.
- Los secretos (cookies, tokens) MUST vivir en el llavero del sistema o en la carpeta de datos con
  permisos de usuario, nunca en la configuración.
- Un guardarraíl automático (hook de pre-commit y test en CI) MUST impedir subir nombres, correos,
  rutas personales o ids reales. El guardarraíl MUST tener casos que demuestren que salta.

Razón: con un repo público, lo que no separa la estructura impide que un despiste publique los datos
de un menor.

### III. Datos de menores (NON-NEGOTIABLE)

- El alumno es menor. alfabeta MUST guardar solo lo imprescindible para su función: nombre para
  mostrar, curso, asignaturas, las cuentas con las que opera y su propio material de estudio (lo que
  entregó y las correcciones y notas que el centro le devuelve), que va solo a la carpeta de la
  familia.
- Su nombre, su correo o cualquier dato que lo identifique MUST NOT aparecer en una URL, un log, un
  mensaje de error, una issue, un PR ni un commit. Los registros usan ids opacos.
- Los datos MUST ir solo a los servicios que la propia familia usa y configura (la cuenta de Google
  del alumno o de la familia, su nube, la app de Claude). Ningún otro tercero.
- Los datos de prueba MUST ser inventados. Ningún fixture contiene material ni datos de un alumno
  real.
- El alumno o su familia inician sesión en cada plataforma. Ninguna herramienta MUST escribir
  credenciales.

Razón: la cuenta escolar es de un menor y el centro la gestiona; la familia responde de lo que
alfabeta hace con ella.

### IV. Solo lectura en las plataformas del centro (NON-NEGOTIABLE)

- En Google Classroom ninguna herramienta MUST entregar, comentar, marcar como hecho ni abrir
  evaluaciones o cuestionarios. Abrir un cuestionario es responderlo o seguir su formulario; leer la
  página de detalle de Classroom que lo describe no lo es.
- En el libro digital (Science Bits y los que vengan) las lecciones de evaluación MUST NOT abrirse:
  gastan intentos y pueden cambiar notas.
- Solo se captura lo que la plataforma ya muestra al alumno con su cuenta, para su estudio. El
  material es de sus autores: uso personal y educativo, sin redistribución.
- El acceso MUST ser el de un alumno navegando: una plataforma cada vez, sin ráfagas. MUST NOT
  usarse evasión: resolución de CAPTCHAs, proxies ni falseo de huellas. Si una plataforma responde
  con un challenge, la sincronización de esa fuente se detiene y se avisa.
- La API de Classroom queda fuera mientras el centro no autorice un cliente OAuth para alfabeta
  (`docs/classroom-investigacion.md`).

Razón: un clic de más puede entregar una tarea en blanco o consumir un intento de examen, y eso no
se deshace.

### V. Sincronización idempotente e incremental

- Cada elemento sincronizado (material, adjunto, tarea, anuncio, fuente de un cuaderno, evento de
  calendario) MUST tener un identificador estable derivado de su origen, y repetir una
  sincronización MUST NOT duplicar nada.
- Dos sincronizaciones seguidas sin cambios en el origen MUST producir cero escrituras en la
  segunda (salvo su propio registro).
- Un cambio en el origen (fecha movida, material nuevo o editado) MUST detectarse y propagarse a
  la carpeta, al cuaderno y al calendario.
- Cada sincronización MUST dejar registro de qué se sincronizó, de dónde y cuándo.
- MUST NOT borrarse nada del alumno ni de la familia porque haya desaparecido del origen: se marca y
  se avisa.

### VI. Una fuente, un proveedor aislado y probado

- Cada origen de contenido (un libro digital, Classroom) MUST implementarse como un proveedor
  detrás de una interfaz común. Science Bits es el primer proveedor de libro; añadir otro MUST NOT
  cambiar el resto.
- El fallo de un proveedor o de una asignatura MUST NOT abortar los demás: se registra, se reporta
  y se sigue.
- Cada extractor MUST tener tests contra páginas guardadas con datos inventados. Los tests y el CI
  MUST NOT llamar a plataformas reales.

### VII. Cada salida es opcional y se degrada sola

- La carpeta del alumno en el disco del Mac es la salida base. Con qué nube se sincroniza (el Drive
  de la familia mediante Drive para escritorio, u otra) y con quién se comparte es configuración;
  alfabeta solo escribe en la carpeta. El cuaderno de Gemini Notebook y el calendario son salidas que se activan por
  configuración.
- Gemini Notebook no tiene API pública y se usa a través de `notebooklm-mcp-cli`, que puede
  romperse. Si una salida falla, las demás MUST completarse y el fallo MUST verse en el registro.

Razón: una herramienta no oficial no puede dejar al alumno sin sus apuntes.

### VIII. Hora local, siempre `Europe/Madrid`

- Las fechas de Classroom y de las plataformas se interpretan como `Europe/Madrid` y se guardan
  como instantes absolutos o fechas sin hora, según el origen. Al escribir en el calendario se usa
  `timeZone: "Europe/Madrid"`.
- El código MUST NOT calcular offsets a mano, y los recordatorios MUST probarse en los cambios de
  horario.

### IX. Simplicidad

- Todo se ejecuta en el Mac de la familia. Sin servidores ni nube propia mientras no haya una
  necesidad medida.
- Una dependencia nueva MUST justificar en el plan por qué no basta la biblioteca estándar o lo que
  ya hay.

## Restricciones técnicas

- **Entorno**: app de escritorio de Claude con acceso al Mac y un navegador con la sesión del alumno
  (Chrome con la extensión de Claude, o el navegador integrado de la app). Python 3.12
  para los scripts; JavaScript solo dentro del navegador para extraer páginas.
- **Configuración**: patrón `*-env` con *template mirroring* (`template.*` → configuración del
  alumno), o su equivalente en un formato estructurado (TOML, que admite comentarios por clave, YAML
  o JSON).
- **Almacenamiento**: una carpeta por alumno en el disco, sincronizada con la nube que fije su
  configuración. Estructura común a todas las fuentes:
  `<curso>/<asignatura>/<Tema NN - título | Tema PNN - título del profesor | AAAA-MM>/<fuente>/`
  (`classroom`, `sciencebits`…); `Tema PNN` es un tema del profesor que no está en el libro.
- **Cuadernos**: uno por tema, con el nombre `<nivel>. <Asig>. Tema NN - <título>` (`<nivel>` es el
  nivel educativo del alumno, no el curso escolar de la carpeta); solo se añaden
  fuentes nuevas.
- **Idioma**: documentación, issues y PR en castellano.

## Flujo de desarrollo

- Cada funcionalidad nace como spec de Spec Kit: `/speckit-specify` → `/speckit-clarify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze`, corrigiendo y repitiendo el análisis
  hasta que no quede ningún hallazgo crítico ni alto.
- La spec se aprueba en un PR solo de documentación. Después se abren las issues de sus tareas, y
  cada issue va en su rama desde `main` y en su propio PR.
- Nada se construye antes de que la spec esté aprobada.
- El plan de cada spec MUST pasar el "Constitution Check" contra estos principios. Cualquier
  excepción MUST quedar justificada en la tabla de complejidad del plan.
- Puertas antes de cada PR: `ruff`, `pyright`, `pytest` y el guardarraíl de datos personales (II).
  Una puerta omitida MUST nombrarse en el PR.
- Lo que `/speckit-plan` añada a `CLAUDE.md` es efímero: ese fichero se regenera.

## Governance

- Esta constitución prevalece sobre cualquier otra práctica del proyecto.
- Toda enmienda MUST hacerse por PR que actualice este fichero y suba la versión, con su Sync Impact
  Report en la descripción del PR (el bloque del fichero se borra antes del commit):
  - MAJOR: se elimina o redefine un principio.
  - MINOR: se añade un principio o una sección, o se amplía de forma material lo que uno admite.
  - PATCH: aclaraciones.
- Las revisiones de PR MUST verificar el cumplimiento. La complejidad que se aparte de IX MUST
  justificarse por escrito.

**Version**: 1.1.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-25
