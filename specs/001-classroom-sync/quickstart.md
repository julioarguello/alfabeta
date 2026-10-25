# Quickstart: validar la spec 001

Escenarios que demuestran que la épica funciona, de lo que no necesita Classroom a lo que sí. Los
contratos están en [contracts/](contracts/) y las entidades en [data-model.md](data-model.md).

## Requisitos previos

- macOS con `uv`, Node y Git.
- Para los escenarios 6 a 9: la app de escritorio de Claude, Chrome con la extensión de Claude con la
  cuenta escolar del alumno iniciada, y Drive para escritorio con la cuenta del Drive familiar montada.

## 1. Puertas de calidad (sin Classroom)

```bash
make setup-python setup-node
make ci
```

Esperado: ruff, Pyright, `pytest` (con más de cero pruebas recogidas), `node --test` del extractor y el
guardarraíl en verde, cada uno nombrado en la salida.

## 2. US1 con un alumno inventado (sin Classroom)

```bash
export ALFABETA_PRUEBA=$(mktemp -d)
uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" prueba preparar
export ALFABETA_EJECUCION=$(uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" bloqueo tomar --alumno prueba --modo interactiva | python3 -c 'import json,sys;print(json.load(sys.stdin)["ejecucion"])')
uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" prueba descargar --alumno prueba --capturas
uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" descargas recoger --alumno prueba
uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" plan --alumno prueba
uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" prueba descargar --alumno prueba
uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" descargas recoger --alumno prueba
uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" aplicar --alumno prueba
uv run python -m alfabeta --inicio "$ALFABETA_PRUEBA" bloqueo soltar --alumno prueba
```

`prueba preparar` deja las capturas inventadas en `capturas-prueba/` y los adjuntos en `adjuntos-prueba/`,
los dos fuera de las descargas. `bloqueo tomar` devuelve el `ejecucion` que exportamos;
`prueba descargar --capturas` deja las capturas en las descargas con ese `ejecucion` (lo que en una
ejecución real deja el extractor) y el primer `descargas recoger` las toma y fija el alcance; `prueba descargar` copia a las descargas, después del
plan, los adjuntos que pide (lo que hace Claude), y el segundo `descargas recoger` los recoge. Si el plan
reparte descargas en tandas, `prueba descargar --tanda N` y `descargas recoger` por cada tanda. Esperado: `2026-2027/<asignatura>/<Tema NN - título | Tema PNN - título | AAAA-MM>/classroom/` con
materiales `AAAA-MM-DD - <título>`, carpetas de tarea con `enunciado - <nombre>` y notas `enlaces.md`;
cada elemento de la captura en su sitio o anotado con enlace y motivo (SC-001).

## 3. US2: la agenda (sin Classroom)

Tras el escenario 2: `2026-2027/agenda.md` abre con «Pendiente» (más próximo primero, sin fecha al
final), sigue con «Hecho» y termina con «Publicado» (material y avisos); el examen anunciado en el tablón de prueba, cuya propuesta siembra `prueba preparar`, aparece como
«detectado» con enlace (SC-004a); `agenda.json` es válido según `contracts/agenda.schema.json`. Con `bloqueo tomar --modo interactiva` (exportando su `ejecucion` como en el escenario 2) /
`bloqueo soltar` alrededor, corregir el examen con `decisiones corregir … --fecha <otra>` y volver a
aplicar: la agenda conserva la corrección.

## 4. US3: repetir sin cambios y con cambios (sin Classroom)

- Repetir sobre el mismo `$ALFABETA_PRUEBA` las órdenes del escenario 2 desde `bloqueo tomar` hasta
  `bloqueo soltar` (`prueba descargar --capturas` vuelve a dejar las capturas con el `ejecucion` nuevo): «sin cambios», el JSON de `aplicar` cuenta
  las clases de prueba (no cero), y `find "$ALFABETA_PRUEBA/drive" -newer <marca>` vacío (SC-002). Las capturas repetidas llevan el
  mismo `capturado`; el caso de otro `capturado` sin fechas entre medias lo prueba T051. Que
  la agenda no dependa del día lo prueba T045 con un «hoy» simulado, sin cambiar el reloj del sistema.
- En la captura de `capturas-prueba/`, mover una fecha de entrega y poner una «Última modificación» posterior en un
  material; sustituir su adjunto en `adjuntos-prueba/` por otro contenido; repetir el escenario 2: la
  agenda muestra la fecha nueva y queda `<nombre> (anterior AAAA-MM-DD)` (SC-003).
- Quitar un elemento de una captura marcada `completa: false`: no se retira nada; con `completa: true`
  se marca retirado y la réplica sigue ahí.

## 5. US5: configuración y guardarraíl (sin Classroom)

- Quitar una clave del `config.toml` de prueba → `config comprobar` sale con 1 y nombra la clave, no su
  valor.
- Crear un segundo alumno inventado con `prueba preparar --alumno prueba2` y sincronizarlo con las órdenes del
  escenario 2 → `git status` sin cambios
  (SC-006) y carpetas separadas.
- Añadir a un fichero preparado un correo y una ruta de usuario de macOS, ambos inventados →
  `uv run python -m alfabeta guardarrail --cambios` sale con 1 y nombra fichero y línea sin repetir el
  dato (SC-007). En un clon sin configuraciones locales el guardarraíl avisa en stderr y sigue con los
  detectores genéricos.

## 6. Spike S1: descarga de un adjunto de Drive

Con un material real del alumno, probar los métodos de research R4 en orden y anotar el primero que
deja el fichero completo en la carpeta de descargas. `descargas recoger` debe moverlo y verificarlo.

## 7. Spike S2: tarea programada con navegador

Crear una tarea programada de prueba en la app que abra Classroom en Chrome, lea el título de la
página y descargue una captura y un adjunto. Anotar si puede usar el navegador y si descarga sin que
nadie apruebe nada. Si no, la ejecución programada queda en el modo reducido de FR-021a.

## 8. Spike S3: estructura real y páginas sintéticas

Guardar las páginas reales de una clase en `datos/capturas-crudas/`, generar sus versiones sintéticas
con `anonimizar`, pasar el guardarraíl sobre ellas antes de añadirlas a `tests/fixtures/classroom/`,
comprobar que leer la página de detalle de una pregunta no cambia nada en «Tu trabajo», y anotar
cuánto tarda una clase completa.

## 9. Sincronización real de una asignatura

Pedir a Claude «sincroniza alfabeta para <alumno>, solo <asignatura>». Comprobar:

- Matar la ejecución a mitad: tras `bloqueo_inactividad_minutos` el bloqueo se libera y el registro
  tiene una línea `detenida` con motivo `inactividad`.
- Ningún cambio de estado en Classroom (SC-008): el panel «Tu trabajo» de las tareas sigue igual.
- Cada elemento de «Trabajo de clase» está en su carpeta o anotado con enlace y motivo (SC-001).
- Los temas del profesor sin emparejar esperan en su carpeta de mes y el resumen pide confirmación.
- Un examen anunciado en el tablón aparece en la agenda como «detectado» con enlace.
- `grep` del nombre y el correo del alumno en `~/.alfabeta/<alumno>/datos/registro.jsonl` no encuentra
  nada (SC-009).
- Con el libro: `libro colocar` deja el tema de Science Bits en `<tema>/sciencebits/` junto a
  `classroom/` (SC-005).
