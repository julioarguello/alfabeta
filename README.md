# alfabeta

**Skills de Claude para que la generación Alfa estudie con IA, y para que sus familias les ayuden sin perder la tarde.**

Convierte los libros digitales del cole en material de estudio de verdad (PDF navegables + Markdown en
castellano, euskera e inglés), lo ordena en tu nube por curso, asignatura y tema, y crea un cuaderno de
[Gemini Notebook](https://notebook.google.com) (antes NotebookLM) por tema para preguntarle, generar
resúmenes en audio, tarjetas o cuestionarios. Próximamente: sincronización con Google Classroom y un plan de
estudio en el calendario.

## ¿Por qué «alfabeta»?

Es un juego de palabras con cuatro capas:

| | |
|---|---|
| **alfabeto** | Va de aprender. Lo primero que se aprende es el alfabeto; esto es el alfabeto del estudio con IA. |
| **generación Alfa** | Para quien se hace: los nacidos desde 2010, la primera generación que estudia con IA desde el instituto. |
| **beta** | Siempre en pruebas. Es un proyecto vivo que se rehace con cada tema, cada asignatura y cada curso. |
| **poda alfa-beta** | Un guiño friki: el algoritmo clásico de IA con el que las máquinas aprendieron a jugar al ajedrez descartando lo que no merece la pena mirar. Justo lo que queremos: estudiar lo que importa. |

## Qué hay

| Skill | Estado | Qué hace |
|---|---|---|
| [`sciencebits-a-notebooklm`](skills/sciencebits-a-notebooklm/SKILL.md) | ✅ funciona | Captura un tema de Science Bits (cada pantalla y cada botón), genera PDF con índice clicable + Markdown por idioma, lo guarda en tu nube y crea el cuaderno de Gemini Notebook. |
| `classroom-sync` | 🧪 prueba de concepto | Tareas, fechas y materiales de Google Classroom → carpeta del tema + cuaderno. Ver [roadmap](docs/roadmap.md). |
| `plan-de-estudio` | 💡 idea | Entregas y exámenes → Google Calendar con sesiones de repaso. |

## Requisitos

- [Claude](https://claude.ai) con la **app de escritorio** (navegador integrado y acceso a tu Mac).
- Conector **Desktop Commander** (comandos en el Mac).
- Para Gemini Notebook: [`notebooklm-mcp-cli`](https://github.com/jacob-bd/notebooklm-mcp-cli)
  (`uv tool install notebooklm-mcp-cli` y `nlm login`).
- Python 3 con `reportlab`, `beautifulsoup4` y `pypdf` (la VM de Claude ya los trae).

## Instalación

1. Copia `config.example.json` a `~/.alfabeta/config.json` y rellénalo (nombre, curso, carpetas, asignaturas).
2. Copia la carpeta `skills/sciencebits-a-notebooklm/scripts/` a la ruta `storage.tools_dir` de tu config.
3. En Claude, añade la skill subiendo `skills/sciencebits-a-notebooklm/` (o pídele a Claude «instala la skill
   sciencebits-a-notebooklm de github.com/julioarguello/alfabeta»).
4. Pídele: **«hazme el siguiente tema de física»**.

## Avisos importantes

- **Uso personal y educativo.** Captura solo lo que la plataforma ya muestra al alumno con su propia
  cuenta, para que estudie. No redistribuyas el material: es de sus autores (Science Bits, el profesorado…).
- **No toca exámenes.** Las lecciones de evaluación nunca se abren, para no gastar intentos ni alterar notas.
- **Gemini Notebook no tiene API pública.** `notebooklm-mcp-cli` usa APIs internas y las cookies de tu cuenta
  de Google; puede romperse y su uso puede no encajar con los términos de Google. Úsalo bajo tu
  responsabilidad (o desactívalo con `notebook.enabled: false` y añade los archivos a mano).
- **Privacidad.** Ningún dato del alumno va al repo: todo lo personal vive en `~/.alfabeta/config.json`.

## Licencia

[MIT](LICENSE).
