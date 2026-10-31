# Study-pack prompt templates

The prompts are in Spanish because they were measured in Spanish (2026-10-26); a translation is an
untested prompt. `{placeholders}` come from the configuration, from the topic's confirmed blocks
(`notebook/bloques.md`) or, for the exam sheets, from the exam and its announcement, and for the
exam's start note from the title `exam prep` gives the theory sheet. Replace every one before
sending; a prompt that still holds a `{` is a bug.

> [!IMPORTANT]
> `exam prep` finds its three texts by their exact headings: «Theory sheet — for an exam»,
> «Problems sheet — for an exam» and «Start note — for an exam». Renaming one makes the command
> refuse (`invalid_prompt`) and ask the notebook for nothing.

| Placeholder | Source |
|---|---|
| `{grade}` | `student.grade_level` |
| `{language}` | the subject's `language` in words (`euskera`, `inglés`) |
| `{block}` | one confirmed block: what it covers, in Spanish |
| `{terms}` | the block's key terms as the class material writes them, comma-separated |
| `{exclude}` | what the video must not explain: the other blocks' titles, and what a source says is out of the exam (the announcement, the teacher), each sourced in `bloques.md`. Never a textbook lesson, a notes page or a Classroom item on its own: the handouts' silence is not exclusion (SKILL.md step 1) |
| `{worked_example}` | one solved example taken from the teacher's sheets, with its recomputed result |
| `{blocks}` | the confirmed blocks, in study order |
| `{answer_sheet}` | the name of the teacher's sheet whose answers are recomputed |
| `{corrections}` | the recomputed results that differ from the teacher's key, one per exercise |
| `{subject}` | the subject's `folder` |
| `{exam_day}` | the exam's date in words, `martes 12 de mayo` |
| `{scope}` | the text of the teacher's announcement of the exam, verbatim, as spec 001 captured it |
| `{scope_date}` | that announcement's date, `8 de mayo` |
| `{slot}` | the study slot, `17:00–18:30`, or `90 minutos` when none is given |
| `{pages}` | the theory sheet's pages: four per 90 minutes of slot, rounded up |
| `{topic}` | the topic folder's name after its date, `Tema 02 - La nutrición humana` |
| `{notes_corrections}` | empty, or one sentence per line of «Correcciones a los apuntes» in `bloques.md` for this prompt's blocks (spec 002 FR-046) — never a line of «Preguntas sobre los apuntes» — each ending in a space: the source's fact and «No digas que <the notes' version>.»; in the summary also «En la parte N, añade una línea "Corrige en tus apuntes: <the source's fact>."». Appended at the end of every other prompt of that block; the tutor chat gets every block's, without the summary's sentence |
| `{plan}` | the study plan the agent writes for guide 0 (its section below) |
| `{part}` | empty for an exam over one topic; over several subtopics (spec 002 FR-045), «Este examen abarca varios subtemas y este cuaderno solo tiene el subtema «<topic>» (parte N de M): las secciones son solo los puntos del anuncio que tratan tus fuentes; nombra los demás en una línea «En otro subtema:» y no los desarrolles. », ending in a space |
| `{theory}` | the theory sheet's title in Studio, `EXAMEN jueves 1 · Teoría para el examen · Tema 02 - …` |

## Video — one per block, plus one per point of the announcement no block covers

`nlm video create <nb> --format explainer --language es-ES --focus "<prompt>" --profile <profile> -y`

```text
Vídeo explicativo de 3 a 4 minutos para un alumno de {grade} que da esta asignatura en {language} y estudia en castellano. Explica en castellano solo esto: {block}. Cada vez que aparezca un término clave, dilo también en {language} tal como aparece en el material de clase ({terms}). Resuelve un solo ejemplo paso a paso con datos de las hojas del profesor: {worked_example}. No expliques {exclude}. Termina con tres preguntas cortas para contestar sin mirar.
```

Drop the worked-example sentence for a block with no calculation.

## Practice sheet — in the subject's language

`nlm report create <nb> --format "Create Your Own" --language <language-code> --prompt "<prompt>" --profile <profile> -y`

```text
Hoja de ejercicios graduados para practicar el examen, escrita entera en {language}, con los términos del material de clase. Tema: {blocks}. Estructura: Nivel 1, un ejemplo resuelto completo paso a paso. Nivel 2, dos ejemplos en los que falta el último paso, y luego dos en los que faltan los dos últimos pasos, para completar. Nivel 3, seis problemas mezclados, sin solución. Todos los datos numéricos tienen que ser nuevos: cambia cada número de cada problema; ninguno puede coincidir con los de las hojas del profesor ni con los ejemplos de las fuentes. Al final, en una sección aparte, la solución de cada problema de los niveles 2 y 3 con el planteamiento. Comprueba cada resultado numérico dos veces; la masa de la disolución es la masa del soluto más la del disolvente, y los volúmenes no siempre se suman.
```

The last sentence is the topic's typical error; replace it with the one that applies.

## Glossary — for the parent, in `notebook/`

```text
Glosario del tema para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Una sola tabla con las columnas: término en {language} tal como aparece en el material de clase | castellano | inglés | definición de una línea en castellano | fórmula o unidad, si la hay. Como máximo 25 términos, solo los que aparecen en las hojas y la presentación del profesor, en el orden en que se estudian: {blocks}. Sin introducción ni texto adicional.
```

## Parent guide — for the parent, in `notebook/`

```text
Guía en castellano para un padre o una madre que ayuda en casa y no sabe {language}; el alumno da la asignatura en {language}. Secciones: 1) Qué entra en el examen, por bloques: {blocks}. 2) Preguntas para hacerle en casa, por bloque, en una tabla: pregunta en castellano | respuesta esperada | término en {language}. 3) Solucionario de la hoja {answer_sheet}: enunciado traducido al castellano, planteamiento y resultado de cada ejercicio, recalculado por ti. Marca de forma neutra, sin culpar a nadie, los resultados que no coinciden con la hoja: {corrections}; indica también si a algún enunciado le falta un dato. 4) Errores típicos que vigilar.
```

## Quiz and flashcards — in the subject's language

Neither command takes a language; see the account-wide switch in `SKILL.md` before sending these.

`nlm quiz create <nb> --count 10 --difficulty 3 --focus "<prompt>" --profile <profile> -y`

```text
Test para practicar el examen: {blocks}. Preguntas de comprensión y de cálculo; en las de cálculo, los distractores son los resultados de los errores típicos.
```

`nlm flashcards create <nb> --focus "<prompt>" --profile <profile> -y`

```text
Tarjetas de vocabulario del tema: en el anverso el término en {language} tal como aparece en el material de clase; en el reverso, el término en castellano y en inglés y una definición de una línea. Solo términos de las hojas y la presentación del profesor: {blocks}.
```

## Theory sheet — for an exam

`exam prep` sends it (spec 002 FR-029 to FR-033):
`nlm report create <nb> --format "Create Your Own" --language es --prompt "<prompt>" --profile <profile> -y`.
Not measured: the sheet it describes, observed 2026-10-28, was written by an agent, not by the notebook.

```text
Hoja de teoría para estudiar mañana un examen, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · Examen del {exam_day} — Teoría y plan de estudio». Empieza con «Qué entra»: copia tal cual este anuncio del profesor, en su idioma, con su fecha ({scope_date}): {scope}. Las secciones de la hoja son los puntos de ese anuncio, en el mismo orden; {part}di qué partes del tema no entran. Mandan los apuntes de clase del alumno; las fotocopias de Classroom y el libro solo completan lo que falta en ellos. Cada término va primero en {language}, tal como lo escribe el material de clase, y después en castellano; si los apuntes, las fotocopias y el libro llaman de forma distinta a una misma cosa, o usan una palabra para dos cosas, muestra cada forma y cómo distinguirlas. Después de «Qué entra», un plan para la tarde ({slot}) en una tabla Hora | Qué | Cómo: una fila por sección, un descanso de cinco minutos y una última fila de unos quince minutos de hoja en blanco, para escribir de memoria y en {language} lo que el examen pide reproducir, corregir con esta hoja y rodear lo que falle. Cada sección acaba con una prueba para hacer sin mirar, con sus respuestas. Señala las trampas típicas. Los problemas no van aquí, sino en la hoja «Problemas tipo». Como mucho {pages} páginas A4. Comprueba dos veces cada número.
```

## Problems sheet — for an exam

`exam prep` sends it the same way (spec 002 FR-034 to FR-036). Not measured either.

```text
Hoja de problemas para un examen de mañana, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · Examen del {exam_day} — Problemas tipo». Usa solo los problemas de las fotocopias que el profesor ha puesto en Classroom, ejemplos resueltos incluidos. 1) Nombra cada fotocopia con su fecha. 2) Reparte todos los problemas en el menor número de patrones posible: una fórmula es un patrón, y usarla al derecho o al revés, despejando otra incógnita, es el mismo patrón; un patrón también puede ser una cadena de fórmulas o una clasificación sin fórmula. Pon una tabla Patrón | Problemas | El más difícil en la que cada problema esté en un solo patrón; señala los problemas que se repiten en dos fotocopias y marca con ★ los que el profesor mandó hacer. 3) Di en qué orden repasarlos, unos diez minutos por patrón. 4) Para cada patrón, el problema más difícil, uno de los mandados si lo hay: su enunciado copiado tal cual en su idioma, su traducción al castellano y por qué es el más difícil; puedes añadir otro del mismo patrón para si sobra tiempo. 5) Después, bajo el título «Soluciones», cada uno de esos problemas resuelto con su planteamiento. 6) Al final, bajo el título «Soluciones impresas que no cuadran», recalcula cada resultado que imprimen las fotocopias, compáralo con la precisión con que está impreso y pon en una tabla Problema | Impreso | Calculado | Qué pasa cada uno que no coincida, y cada enunciado al que le falte un dato con el resultado de cada lectura. Si la diferencia solo viene de redondear antes del final, dilo junto a su solución y no lo pongas en la tabla. No culpes ni nombres a nadie. Cada término, primero en {language} y después en castellano. Comprueba dos veces cada número.
```

## Study guide — 0, the entry point

The pack's first piece: `0 · Guía de estudio · Empieza aquí`, a report, so every viewer sees it. It
is **only the plan** — order, sessions, minutes, breaks, what the student can do at the end — and
points at the other pieces by number. **No theory**: the operator found the first version, plan plus
content, "muy densa" (2026-10-29). It replaces the ordinary start note below; `exam prep` writes its
own under its moment. Write the plan yourself, with the real numbers and the notes' pages, and check
after downloading that it came back unchanged, or regenerate.

`nlm report create <nb> --format "Create Your Own" --language es --prompt "<prompt>" --profile <profile> -y`

```text
Copia TAL CUAL el bloque de texto en Markdown de abajo, sin cambiar ni una palabra, ni un número, ni el orden, y sin añadir nada antes ni después: ni título, ni introducción, ni teoría, ni explicaciones, ni despedida.

{plan}
```

`{plan}` is Markdown the agent writes, in Spanish, short. It is built from **blocks of 45 minutes
at most, two a day at most, with a 15-minute break between them** (spec 002 FR-042). A videos
block holds three videos at most, about 15 minutes each; the checking block comes after the last
videos block. Up to three videos is one day (block A, break, block B); five videos is two days:
day 1 block A1 (three videos), break, block A2 (two videos); day 2 the checking block. Each block
says its day. Nothing is marked optional to make it fit:

- a table `Nº | Pieza | Para qué`, 0 first, **every video linked straight to its copy in Drive**
  (`https://drive.google.com/file/d/<id>/view`; Drive for desktop gives the id as the file's
  `com.google.drivefs.item-id#S` extended attribute), and the topic's `notebook/` folder linked once
  — always, whether the notebook shows the video or not (spec 002 FR-039);
- **block A, the videos**: for each one, the student draws his own scheme while watching (branches
  and short sentences, with the word in the subject's language), then compares its branches with the
  notebook's mind map (it carries no text) and its text with that block's part of the summary,
  correcting only the essentials in another colour;
- the 15-minute break, away from screens;
- **block B, checking**: practice, quiz, flashcards, each with its minutes, and five minutes to mark
  in his scheme what he got wrong;
- **what he can do when it ends**: draw his schemes without looking and explain each branch in one
  sentence, with the word in the subject's language.

## Summary of the notes

`N · Resumen de tus apuntes · <topic>`, numbered after the videos and the mind map: what the student studies from. The notes condensed on their
own schemes (constitution X), one part per content block (`{blocks}`), each studied with its video, half a page each at most.

`nlm report create <nb> --format "Create Your Own" --language es --prompt "<prompt>" --profile <profile> -y`

```text
Resumen para estudiar, corto y fácil de leer, para un alumno de {grade} que da la asignatura en {language}. Título: «Resumen de tus apuntes · {topic}». Condensa SOLO lo que dicen los apuntes del alumno, siguiendo sus esquemas y con sus mismas palabras; usa el libro solo para aclarar o corregir una rama, nunca para añadir temas nuevos. Una parte por bloque, cada una de media página como máximo, en este orden: {blocks}. Formato de cada parte: el esquema como lista con sangría, en el orden de sus apuntes; cada rama con UNA sola línea corta de explicación y el término en {language} entre paréntesis. Al final de cada parte, una línea «Lo que más se confunde:» con la confusión típica de esa parte. {notes_corrections}Sin introducción, sin conclusiones, sin preguntas, sin tablas largas.
```

`{notes_corrections}`: see the placeholder table. Example for this summary, 2026-10-31: «La
hemoglobina está dentro del glóbulo rojo (Wikipedia en euskera, «Hemoglobina»). No digas que está en
la superficie. En la parte 5, añade una línea "Corrige en tus apuntes: la hemoglobina está dentro
del glóbulo rojo." »; the other prompts and the chat get the first two sentences only.

First used 2026-10-29 for one biology topic; whether these times and this length suit the student
is a hypothesis.

## Start note

`nlm note create <nb> --title "0 · Empieza aquí" --content "<text>" --profile <profile>`

```text
1. Mira los vídeos en orden: uno por tarde.
2. Después de cada vídeo, haz la parte de la hoja de ejercicios de ese bloque, en papel.
3. El día antes del examen: el test y las tarjetas. Si una respuesta tuya no coincide con una hoja, fíate de tu cuenta y pregunta en el chat.
```

## Start note — for an exam

`exam prep` writes it once the theory sheet is in Studio, as the note `EXAMEN <weekday> · Empieza
aquí`, rewritten by a second run for the same exam; a note «0 · …» is the pack's and stays as it
is (spec 002 FR-015, FR-029): `{theory}` is that sheet's title.

```text
Hoy, para el examen del {exam_day}: «{theory}» ({slot}). Sigue el plan con el que empieza la hoja.
```

## Tutor chat

`nlm chat configure <nb> --goal custom --prompt "<prompt>" --profile <profile>`

```text
Eres un tutor para un alumno de {grade}. Explica en castellano y da cada término clave también en {language}. Antes de dar una solución, da una pista y espera a que el alumno lo intente. {notes_corrections}En lo demás, cuando las fuentes no coinciden, prima los apuntes del alumno sobre el material del profesor, y el material del profesor sobre el libro. No atribuyas a nadie la autoría de una fuente ni de una nota.
```
