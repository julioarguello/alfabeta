---
name: sciencebits-a-notebooklm
description: Convierte un tema de un libro digital de Science Bits (learning-bits.com) en PDFs navegables + Markdown (ES/EU/EN), los guarda en la nube del usuario y crea su cuaderno en Gemini Notebook (NotebookLM). Usar con "el siguiente tema" o "hazme el tema N de física/bio".
---

# Science Bits → PDF + Markdown → nube → Gemini Notebook

Parte del proyecto [alfabeta](https://github.com/julioarguello/alfabeta).

## Configuración
Lee `~/.alfabeta/config.json` (ver `config.example.json` del repo) con Desktop Commander. De ahí salen:
`student.name`, `student.grade`, `storage.base_dir`, `storage.tools_dir` (`$H`), `storage.topic_folder_pattern`,
`subjects` (clase de Science Bits → nombre corto), `languages`, `notebook.enabled`, `notebook.title_pattern`.
Si no existe, pregunta esos datos una vez y créalo. Nunca escribas datos personales fuera de ese fichero.

Resultado por tema:
- `TemaNN_<LANG>.pdf` y `.md` en `base_dir/<topic_folder_pattern>`. Cada PDF: portada, índice clicable
  (lecciones y apartados), marcadores, una captura por pantalla (y por cada botón que cambia el contenido) y
  debajo el texto seleccionable. El `.md` lleva el mismo texto estructurado (lección → apartado → pantalla).
- Si `notebook.enabled`: un cuaderno de Gemini Notebook con esos archivos como fuentes.

Trabaja de principio a fin sin pedir confirmación en cada paso. Solo pregunta si el tema es ambiguo o hay que
iniciar sesión (Science Bits o Google).

## Herramientas (en `$H`, copiadas de `scripts/`)
- `discover_lessons.js` — en la página de la unidad: `sem`, `rest` y `lessonId` de cada lección.
- `orchestrator.js` — captura en segundo plano una cola de lecciones/idiomas; descarga un zip por lección.
- `watch.py` — en el Mac, copia cada zip descargado a `raw/` (las descargas del navegador integrado a veces
  quedan como temporales ocultos `.…claudefordesktop.…` que la app borra en minutos).
- `build.py` — genera PDF + `.md` por idioma desde `raw/`.

Entornos: navegador integrado (`…Claude_Browser__*`; carga antes la skill `built-in-browser`); Desktop
Commander para comandos en el Mac; `device_bash` (VM con python3, reportlab, bs4, pypdf, fuentes DejaVu) con
`~/Downloads` conectado, donde se ejecuta `build.py`; CLI `nlm` (`notebooklm-mcp-cli`) para el cuaderno.

## Nombres
- Curso escolar desde `school_year_starts_month` → p. ej. `2026-2027`.
- Asignatura: `subjects[<clase en Science Bits>]`; si falta, pregunta el nombre corto una vez y guárdalo en la config.
- "El siguiente tema" = el siguiente al mayor `Tema NN` existente en esa asignatura (y el orden de unidades en
  la clase de Science Bits).

## Pasos

1. **Preparar.** `WORK=~/Downloads/alfabeta_work/<Asig>_TemaNN` con `raw/`, `out/`, `tools/`. Copia `$H/*` a
   `$WORK/tools`. Arranca el recolector y déjalo corriendo:
   `start_process("python3 -u $WORK/tools/watch.py $WORK/raw", timeout_ms=3000)`.
2. **Abrir Science Bits.** `preview_start(sciencebits.url)` (si pide permiso: `request_access` scope "site").
   Si sale el login o "Your session has expired": pide al usuario que inicie sesión en el panel del navegador
   marcando "Remember me on this device" y espera su "listo". Nunca escribas credenciales.
3. **Localizar el tema.** `get_page_text` lista clases y unidades. Con `find` localiza "Acceder a la unidad" y
   navega a esa URL. Anota el título en cada idioma (misma URL con `/intranet/eu/` y `/intranet/en/`).
4. **Descubrir lecciones.** En la página de la unidad ejecuta `discover_lessons.js` con `javascript_tool`.
   Hazlo antes de capturar: no navegues mientras corre la captura (`preview_start` puede reutilizar la pestaña).
5. **Capturar.** Vuelve a la página de clases y aplica `resize_window(width=1280, height=800)`. Cola: idiomas en
   orden, ids `L1…Ln`, sin lecciones de evaluación. Ejecuta en una sola llamada
   `window.__SB={sem, rest, queue:[{lang, id, lessonId},…]};` + el contenido de `orchestrator.js`.
   Sondea `window.__orch` con llamadas cortas (<40 s): `results`, `current`, `stopped`,
   `document.getElementById('__fr')?.contentWindow.__job?.n`; entre sondeos, `device_bash "sleep 170; ls …/raw"`.
   ~3–5 min por lección. Avisa de la duración y de que nadie abra Science Bits en otro dispositivo.
   - `SESSION_EXPIRED` → pide volver a entrar y relanza lo que falta.
   - `NOT_AVAILABLE` → ese idioma no existe para la unidad (unidades editadas por el docente); se salta.
   - **Evaluaciones**: nunca las abras ni inicies; quedan fuera.
   - Otros `n:0`/errores → relánzalos al final. Comprueba un zip con `items` por lección e idioma.
6. **Construir.** `$WORK/unit.json`:
   `{"prefix":"TemaNN","langs":{"es":{"unit":"Tema N · …","course":"Física y Química · <grade>"},"eu":{…},"en":{…}}}`.
   En `device_bash`: `python3 tools/build.py raw out --config unit.json <idiomas capturados>`.
7. **Verificar.** pypdf: páginas, marcadores, enlaces del índice, texto extraíble. Revisa el `.md`. Si una lección
   tiene pocas pantallas frente a su índice (`menu` en meta.json), recaptúrala.
8. **Guardar.** `mkdir -p` de la carpeta del tema y copia `out/*`.
9. **Gemini Notebook** (si `notebook.enabled`):
   - `nlm login --check`; si falla, `nlm login --storage protected` en segundo plano (Chrome aparte, sin perfil:
     es normal). Pide al usuario iniciar sesión, confirmar la verificación en dos pasos y **no cerrar la ventana**.
   - `nlm notebook list`; reutiliza el cuaderno del tema o créalo con `title_pattern` (`--json`).
   - `nlm source add <id> --file "<archivo>" --wait --wait-timeout 300` para cada PDF y `.md`.
   - Prueba: `nlm notebook query <id> "<pregunta corta>"`.
   - Si `nlm` falla: `uv tool upgrade notebooklm-mcp-cli` una vez; si sigue, deja los archivos y avisa.
10. **Cerrar.** Detén el recolector, `resize_window preset desktop`, y resume: carpeta, enlace del cuaderno,
    pantallas por idioma y lo que quedó fuera.

## Límites
- No descifres los XML de `/seculogged/` ni fuerces la "Versión PDF" desactivada: se captura lo que ve el alumno.
- Los vídeos no se capturan (quedan como "[Vídeo (ver en la plataforma)]").
- Uso personal y educativo; no redistribuyas el material.
