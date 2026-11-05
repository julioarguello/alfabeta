# Study-pack prompt templates

The prompts are in Spanish because they were measured in Spanish (2026-10-26); a translation is an
untested prompt. `{placeholders}` come from the configuration, from the topic's confirmed blocks
(`notebook/bloques.md`) or, for the exam sheets, from the exam and its announcement, and for the
exam's start note from the title `exam build` gives the theory sheet. Replace every one before
sending; a prompt that still holds a `{` is a bug.

> [!IMPORTANT]
> `exam build` finds its texts by their exact headings: «Theory sheet — for an exam», «Problems sheet
> — for an exam» and «Start note — for an exam», and the same three with « with no announcement» after
> them. Renaming one makes the command refuse (`invalid_prompt`) and ask the notebook for nothing.

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
| `{exam_name}` | with no announcement, `Examen del martes 12 de mayo`, or `Examen sin fecha` with no date |
| `{slot}` | the study slot, `17:00–18:30`, or `90 minutos` when none is given |
| `{pages}` | the theory sheet's pages: four per 90 minutes of slot, rounded up |
| `{topic}` | the topic folder's name after its date, `Tema 02 - La nutrición humana` |
| `{notes_corrections}` | empty, or one sentence per line of «Correcciones a los apuntes» in `bloques.md` for this prompt's blocks (spec 002 FR-046) — never a line of «Preguntas sobre los apuntes» — each ending in a space: the source's fact and «No digas que <the notes' version>.»; in the summary also «En la parte N, añade una línea "Corrige en tus apuntes: <the source's fact>."». Appended at the end of every other prompt of that block; the tutor chat gets every block's, without the summary's sentence. An exam with no announcement fills it itself, with no Claude: empty when the topic's `notebook/bloques.md` is missing or has no lines under «Correcciones a los apuntes», a heading at any level, one per block if need be, up to the next heading of the same or a higher level or any line holding «Preguntas sobre los apuntes»; otherwise «Correcciones ya comprobadas en estos apuntes, que prevalecen sobre lo anterior aunque los apuntes insistan o las fuentes callen; en estos puntos no enseñes su versión y añade en esa sección o junto al problema «Corrige en tus apuntes: …»: », the section's lines verbatim and a space |
| `{scheme}` | empty when `bloques.md` names no scheme for this prompt's blocks. Otherwise the scheme and branch it names (constitution X, spec 002 FR-038), as sentences each ending in a space. For one block: «Esto es la rama «<branch>» del esquema «<scheme>» de sus apuntes (pág. N): síguela con sus subramas, en su orden y con sus palabras, y nómbrala al empezar. Lo que la rama no tiene va al final, diciendo de qué fuente sale, sin llamarlo opcional. ». For several blocks: «Sigue el esquema «<scheme>» de sus apuntes (pág. N): sus ramas, en este orden y con estas palabras: <branch>; <branch>; … Nombra la rama de cada parte. Lo que el esquema no tiene va después de su rama más cercana o aparte, diciendo de qué fuente sale, sin llamarlo opcional. » |
| `{plan}` | the study plan the agent writes for guide 0 (its section below) |
| `{part}` | empty for an exam over one topic; over several subtopics (spec 002 FR-045), «, pero este examen abarca varios subtemas y este cuaderno solo tiene el subtema «<topic>» (parte N de M): haz sección solo de los puntos que tratan tus fuentes y nombra los demás en una línea «En otro subtema o sin material:», sin desarrollarlos», with no final full stop. With no announcement, over several topics of any kind: «; este examen abarca varios temas y este cuaderno solo tiene «<topic>» (parte N de M): cubre solo ese tema» |
| `{theory}` | the theory sheet's title in Studio, `EXAMEN jueves 1 · Teoría para el examen · Tema 02 - …` |

## Video — one per block, plus one per point of the announcement no block covers

`nlm video create <nb> --format explainer --language es-ES --focus "<prompt>" --profile <profile> -y`

```text
Vídeo explicativo de 3 a 4 minutos para un alumno de {grade} que da esta asignatura en {language} y estudia en castellano. Explica en castellano solo esto: {block}. {scheme}Cada vez que aparezca un término clave, dilo también en {language} tal como aparece en el material de clase ({terms}). Resuelve un solo ejemplo paso a paso con datos de las hojas del profesor: {worked_example}. No expliques {exclude}. Termina con tres preguntas cortas para contestar sin mirar.
```

Drop the worked-example sentence for a block with no calculation.

## Practice sheet — in the subject's language

`nlm report create <nb> --format "Create Your Own" --language <language-code> --prompt "<prompt>" --profile <profile> -y`

```text
Hoja de ejercicios graduados para practicar el examen, escrita entera en {language}, con los términos del material de clase. Tema: {blocks}. {scheme}Estructura: Nivel 1, un ejemplo resuelto completo paso a paso. Nivel 2, dos ejemplos en los que falta el último paso, y luego dos en los que faltan los dos últimos pasos, para completar. Nivel 3, seis problemas mezclados, sin solución. Todos los datos numéricos tienen que ser nuevos: cambia cada número de cada problema; ninguno puede coincidir con los de las hojas del profesor ni con los ejemplos de las fuentes. Al final, en una sección aparte, la solución de cada problema de los niveles 2 y 3 con el planteamiento. Comprueba cada resultado numérico dos veces; la masa de la disolución es la masa del soluto más la del disolvente, y los volúmenes no siempre se suman.
```

The last sentence is the topic's typical error; replace it with the one that applies.

## Glossary — for the parent, in `notebook/`

```text
Glosario del tema para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Una sola tabla con las columnas: término en {language} tal como aparece en el material de clase | castellano | inglés | definición de una línea en castellano | fórmula o unidad, si la hay. Como máximo 25 términos, solo los que aparecen en las hojas y la presentación del profesor, en el orden en que se estudian: {blocks}. {scheme}Sin introducción ni texto adicional.
```

## Parent guide — for the parent, in `notebook/`

```text
Guía en castellano para un padre o una madre que ayuda en casa y no sabe {language}; el alumno da la asignatura en {language}. {scheme}Secciones: 1) Qué entra en el examen, por bloques: {blocks}. 2) Preguntas para hacerle en casa, por bloque, en una tabla: pregunta en castellano | respuesta esperada | término en {language}. 3) Solucionario de la hoja {answer_sheet}: enunciado traducido al castellano, planteamiento y resultado de cada ejercicio, recalculado por ti. Marca de forma neutra, sin culpar a nadie, los resultados que no coinciden con la hoja: {corrections}; indica también si a algún enunciado le falta un dato. 4) Errores típicos que vigilar.
```

## Quiz and flashcards — in the subject's language

Neither command takes a language; see the account-wide switch in `SKILL.md` before sending these.

`nlm quiz create <nb> --count 10 --difficulty 3 --focus "<prompt>" --profile <profile> -y`

```text
Test para practicar el examen: {blocks}. {scheme}Preguntas de comprensión y de cálculo; en las de cálculo, los distractores son los resultados de los errores típicos.
```

`nlm flashcards create <nb> --focus "<prompt>" --profile <profile> -y`

```text
Tarjetas de vocabulario del tema: en el anverso el término en {language} tal como aparece en el material de clase; en el reverso, el término en castellano y en inglés y una definición de una línea. {scheme}Solo términos de las hojas y la presentación del profesor: {blocks}.
```

## Theory sheet — for an exam

`exam build` sends it (spec 002 FR-029 to FR-033):
`nlm report create <nb> --format "Create Your Own" --language es --prompt "<prompt>" --profile <profile> -y`.
Not measured: the sheet it describes, observed 2026-10-28, was written by an agent, not by the notebook.
Its sections stay the announcement's points (FR-030); the scheme leads inside each one. It has no
`{scheme}`: `exam build` does not read `bloques.md`, so the prompt asks the notebook, which holds the
notes, to find the scheme itself.

```text
Hoja de teoría para estudiar mañana un examen, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · Examen del {exam_day} — Teoría y plan de estudio». Empieza con «Qué entra»: copia tal cual este anuncio del profesor, en su idioma, con su fecha ({scope_date}): {scope}. Las secciones de la hoja son los puntos de ese anuncio, en el mismo orden{part}; di qué partes del tema no entran. Dentro de cada sección, si los apuntes del alumno tienen un esquema de ese punto, sigue sus ramas, en su orden y con sus palabras, y nombra la rama; lo que el esquema no tiene va después, diciendo de qué fuente sale, sin llamarlo opcional. Mandan los apuntes de clase del alumno; las fotocopias de Classroom y el libro solo completan lo que falta en ellos. Cada término va primero en {language}, tal como lo escribe el material de clase, y después en castellano; si los apuntes, las fotocopias y el libro llaman de forma distinta a una misma cosa, o usan una palabra para dos cosas, muestra cada forma y cómo distinguirlas. Después de «Qué entra», un plan para la tarde ({slot}) en una tabla Hora | Qué | Cómo: una fila por sección, un descanso de cinco minutos y una última fila de unos quince minutos de hoja en blanco, para escribir de memoria y en {language} lo que el examen pide reproducir, corregir con esta hoja y rodear lo que falle. Cada sección acaba con una prueba para hacer sin mirar, con sus respuestas. Señala las trampas típicas. Los problemas no van aquí, sino en la hoja «Problemas tipo». Como mucho {pages} páginas A4. Comprueba dos veces cada número.
```

## Problems sheet — for an exam

`exam build` sends it the same way (spec 002 FR-034 to FR-036). Not measured either. No scheme
instruction: the sheet is laid out by the patterns of the teacher's problems, not by the theory,
and constitution X does not list it among the pieces that name a branch.

```text
Hoja de problemas para un examen de mañana, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · Examen del {exam_day} — Problemas tipo». Usa solo los problemas de las fotocopias que el profesor ha puesto en Classroom, ejemplos resueltos incluidos. 1) Nombra cada fotocopia con su fecha. 2) Reparte todos los problemas en el menor número de patrones posible: una fórmula es un patrón, y usarla al derecho o al revés, despejando otra incógnita, es el mismo patrón; un patrón también puede ser una cadena de fórmulas o una clasificación sin fórmula. Pon una tabla Patrón | Problemas | El más difícil en la que cada problema esté en un solo patrón; señala los problemas que se repiten en dos fotocopias y marca con ★ los que el profesor mandó hacer. 3) Di en qué orden repasarlos, unos diez minutos por patrón. 4) Para cada patrón, el problema más difícil, uno de los mandados si lo hay: su enunciado copiado tal cual en su idioma, su traducción al castellano y por qué es el más difícil; puedes añadir otro del mismo patrón para si sobra tiempo. 5) Después, bajo el título «Soluciones», cada uno de esos problemas resuelto con su planteamiento. 6) Al final, bajo el título «Soluciones impresas que no cuadran», recalcula cada resultado que imprimen las fotocopias, compáralo con la precisión con que está impreso y pon en una tabla Problema | Impreso | Calculado | Qué pasa cada uno que no coincida, y cada enunciado al que le falte un dato con el resultado de cada lectura. Si la diferencia solo viene de redondear antes del final, dilo junto a su solución y no lo pongas en la tabla. No culpes ni nombres a nadie. Cada término, primero en {language} y después en castellano. Comprueba dos veces cada número.
```

## Study guide — 0, the entry point

The pack's first piece: `0 · Guía de estudio · Empieza aquí`, a report, so every viewer sees it. It
is **only the plan** — order, sessions, minutes, breaks, what the student can do at the end — and
points at the other pieces by number. **No theory**: the operator found the first version, plan plus
content, "muy densa" (2026-10-29). It replaces the ordinary start note below; `exam build` writes its
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
  — always, whether the notebook shows the video or not (spec 002 FR-039); each video's «Para qué»
  names the branch of the scheme it covers, as `bloques.md` names it (FR-038). The prompt itself has
  no `{scheme}`: it copies `{plan}` as it is, so the plan carries the branches;
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
It has no `{scheme}`: the prompt already tells the notebook to follow the notes' schemes in their
words, and `{blocks}` are the branches' names when there is a scheme.

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

A fixed text, not a request to the notebook: it produces no material, so it carries no scheme.

```text
1. Mira los vídeos en orden: uno por tarde.
2. Después de cada vídeo, haz la parte de la hoja de ejercicios de ese bloque, en papel.
3. El día antes del examen: el test y las tarjetas. Si una respuesta tuya no coincide con una hoja, fíate de tu cuenta y pregunta en el chat.
```

## Start note — for an exam

`exam build` writes it once the theory sheet is in Studio, as the note `EXAMEN <weekday> · Empieza
aquí`, rewritten by a second run for the same exam; a note «0 · …» is the pack's and stays as it
is (spec 002 FR-015, FR-029): `{theory}` is that sheet's title. Like the start note, it produces
no material; it points at the theory sheet, whose sections name the branches.

```text
Hoy, para el examen del {exam_day}: «{theory}» ({slot}). Sigue el plan con el que empieza la hoja.
```

## Theory sheet — for an exam with no announcement

`exam build` sends it the same way when the exam has no captured announcement and the family named the
topics (spec 007 FR-025 to FR-029). Not measured: the family reads the first real run (spec 007 SC-010).
It holds constitution X's last bullet itself, because this run has no Claude to check the facts.

```text
Hoja de teoría para estudiar un examen, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · {exam_name} — Teoría y plan de estudio». Empieza con esta frase, tal cual: «Sin anuncio del profesor: esta hoja cubre todo «{topic}» y el alcance no está confirmado.». No inventes ni cites ningún anuncio, y no dejes fuera ninguna parte del tema{part}. Si los apuntes del alumno tienen un esquema del tema, las secciones de la hoja son sus ramas, en su orden y con sus palabras, y nombras la rama; lo que el esquema no tiene va después de su rama más cercana o aparte, diciendo de qué fuente sale, sin llamarlo opcional. Si no tienen esquema, las secciones siguen el orden de los apuntes, y luego el de las fotocopias de Classroom y el del libro. Los apuntes de clase del alumno mandan en la estructura y las palabras, no en los hechos; las fotocopias de Classroom y el libro completan lo que falta en ellos. Si una fotocopia o el libro contradicen un hecho de los apuntes y no se contradicen entre sí, enseña lo que dicen y añade en esa sección «Corrige en tus apuntes: …». No lo hagas si los apuntes insisten en ese hecho (repetido en otra página, en un recuadro, subrayado, marcado como importante o escrito como palabras del profesor), ni si las fotocopias y el libro no coinciden entre sí: deja lo que dicen los apuntes, sin decir nada en contra en la sección, y ponlo en una última parte de la hoja titulada «Para la familia», con las dos versiones. Donde las fotocopias y el libro callan, se queda lo que dicen los apuntes. Una rama que ninguna fuente explica se nombra sin desarrollarla y va también a «Para la familia». Cada término va primero en {language}, tal como lo escribe el material de clase, y después en castellano; si los apuntes, las fotocopias y el libro llaman de forma distinta a una misma cosa, o usan una palabra para dos cosas, muestra cada forma y cómo distinguirlas. Después de esa frase, un plan ({slot}) en una tabla Hora | Qué | Cómo: una fila por sección, un descanso de cinco minutos y una última fila de unos quince minutos de hoja en blanco, para escribir de memoria y en {language} lo que el examen pide reproducir, corregir con esta hoja y rodear lo que falle. Cada sección acaba con una prueba para hacer sin mirar, con sus respuestas. Señala las trampas típicas. Los problemas no van aquí, sino en la hoja «Problemas tipo». Como mucho {pages} páginas A4. Comprueba dos veces cada número. {notes_corrections}
```

## Problems sheet — for an exam with no announcement

The text of «Problems sheet — for an exam», with its own opening and `{notes_corrections}` at its end.
Not measured either.

```text
Hoja de problemas para un examen, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · {exam_name} — Problemas tipo». Empieza con esta frase, tal cual: «Sin anuncio del profesor: esta hoja cubre todo «{topic}» y el alcance no está confirmado.». Si las fuentes no tienen fotocopias con problemas, dilo en una frase y no inventes ninguno. Usa solo los problemas de las fotocopias que el profesor ha puesto en Classroom, ejemplos resueltos incluidos. 1) Nombra cada fotocopia con su fecha. 2) Reparte todos los problemas en el menor número de patrones posible: una fórmula es un patrón, y usarla al derecho o al revés, despejando otra incógnita, es el mismo patrón; un patrón también puede ser una cadena de fórmulas o una clasificación sin fórmula. Pon una tabla Patrón | Problemas | El más difícil en la que cada problema esté en un solo patrón; señala los problemas que se repiten en dos fotocopias y marca con ★ los que el profesor mandó hacer. 3) Di en qué orden repasarlos, unos diez minutos por patrón. 4) Para cada patrón, el problema más difícil, uno de los mandados si lo hay: su enunciado copiado tal cual en su idioma, su traducción al castellano y por qué es el más difícil; puedes añadir otro del mismo patrón para si sobra tiempo. 5) Después, bajo el título «Soluciones», cada uno de esos problemas resuelto con su planteamiento. 6) Al final, bajo el título «Soluciones impresas que no cuadran», recalcula cada resultado que imprimen las fotocopias, compáralo con la precisión con que está impreso y pon en una tabla Problema | Impreso | Calculado | Qué pasa cada uno que no coincida, y cada enunciado al que le falte un dato con el resultado de cada lectura. Si la diferencia solo viene de redondear antes del final, dilo junto a su solución y no lo pongas en la tabla. No culpes ni nombres a nadie. Cada término, primero en {language} y después en castellano. Comprueba dos veces cada número. {notes_corrections}
```

## Start note — for an exam with no announcement

With or without a date: the note above says «Hoy», which is false for a preparation days ahead.

```text
Para este examen ({exam_name}): «{theory}» ({slot}). Sigue el plan con el que empieza la hoja.
```

## Tutor chat

`nlm chat configure <nb> --goal custom --prompt "<prompt>" --profile <profile>`

```text
Eres un tutor para un alumno de {grade}. Explica en castellano y da cada término clave también en {language}. Antes de dar una solución, da una pista y espera a que el alumno lo intente. {scheme}{notes_corrections}En lo demás, cuando las fuentes no coinciden, prima los apuntes del alumno sobre el material del profesor, y el material del profesor sobre el libro. No atribuyas a nadie la autoría de una fuente ni de una nota.
```
