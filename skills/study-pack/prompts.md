# Study-pack prompt templates

The prompts are in Spanish because they were measured in Spanish (2026-10-26); a translation is an
untested prompt. `{placeholders}` come from the configuration or from the topic's confirmed blocks
(`docente/bloques.md`). Replace every one before sending; a prompt that still holds a `{` is a bug.

| Placeholder | Source |
|---|---|
| `{grade}` | `student.grade` |
| `{exam_language}` | the subject's exam language in words (`euskera`, `inglés`) |
| `{block}` | one confirmed block: what it covers, in Spanish |
| `{terms}` | the block's key terms as the class material writes them, comma-separated |
| `{exclude}` | what the video must not explain: the other blocks and anything out of the exam |
| `{worked_example}` | one solved example taken from the teacher's sheets, with its recomputed result |
| `{blocks}` | the confirmed blocks, in study order |
| `{answer_sheet}` | the name of the teacher's sheet whose answers are recomputed |
| `{corrections}` | the recomputed results that differ from the teacher's key, one per exercise |

## Video — one per block, at most three per topic

`nlm video create <nb> --format explainer --language es-ES --focus "<prompt>" --profile <profile> -y`

```text
Vídeo explicativo de 3 a 4 minutos para un alumno de {grade} que da esta asignatura en {exam_language} y estudia en castellano. Explica en castellano solo esto: {block}. Cada vez que aparezca un término clave, dilo también en {exam_language} tal como aparece en el material de clase ({terms}). Resuelve un solo ejemplo paso a paso con datos de las hojas del profesor: {worked_example}. No expliques {exclude}. Termina con tres preguntas cortas para contestar sin mirar.
```

Drop the worked-example sentence for a block with no calculation.

## Practice sheet — in the exam language

`nlm report create <nb> --format "Create Your Own" --language <exam-lang-code> --prompt "<prompt>" --profile <profile> -y`

```text
Hoja de ejercicios graduados para practicar el examen, escrita entera en {exam_language}, con los términos del material de clase. Tema: {blocks}. Estructura: Nivel 1, un ejemplo resuelto completo paso a paso. Nivel 2, dos ejemplos en los que falta el último paso, y luego dos en los que faltan los dos últimos pasos, para completar. Nivel 3, seis problemas mezclados, sin solución. Todos los datos numéricos tienen que ser nuevos: cambia cada número de cada problema; ninguno puede coincidir con los de las hojas del profesor ni con los ejemplos de las fuentes. Al final, en una sección aparte, la solución de cada problema de los niveles 2 y 3 con el planteamiento. Comprueba cada resultado numérico dos veces; la masa de la disolución es la masa del soluto más la del disolvente, y los volúmenes no siempre se suman.
```

The last sentence is the topic's typical error; replace it with the one that applies.

## Glossary — for the parent, in `docente/`

```text
Glosario del tema para un alumno de {grade} que da la asignatura en {exam_language} y estudia en castellano. Una sola tabla con las columnas: término en {exam_language} tal como aparece en el material de clase | castellano | inglés | definición de una línea en castellano | fórmula o unidad, si la hay. Como máximo 25 términos, solo los que aparecen en las hojas y la presentación del profesor, en el orden en que se estudian: {blocks}. Sin introducción ni texto adicional.
```

## Parent guide — for the parent, in `docente/`

```text
Guía en castellano para un padre o una madre que ayuda en casa y no sabe {exam_language}; el alumno da la asignatura en {exam_language}. Secciones: 1) Qué entra en el examen, por bloques: {blocks}. 2) Preguntas para hacerle en casa, por bloque, en una tabla: pregunta en castellano | respuesta esperada | término en {exam_language}. 3) Solucionario de la hoja {answer_sheet}: enunciado traducido al castellano, planteamiento y resultado de cada ejercicio, recalculado por ti. Marca de forma neutra, sin culpar a nadie, los resultados que no coinciden con la hoja: {corrections}; indica también si a algún enunciado le falta un dato. 4) Errores típicos que vigilar.
```

## Quiz and flashcards — in the exam language

Neither command takes a language; see the account-wide switch in `SKILL.md` before sending these.

`nlm quiz create <nb> --count 10 --difficulty 3 --focus "<prompt>" --profile <profile> -y`

```text
Test para practicar el examen: {blocks}. Preguntas de comprensión y de cálculo; en las de cálculo, los distractores son los resultados de los errores típicos.
```

`nlm flashcards create <nb> --focus "<prompt>" --profile <profile> -y`

```text
Tarjetas de vocabulario del tema: en el anverso el término en {exam_language} tal como aparece en el material de clase; en el reverso, el término en castellano y en inglés y una definición de una línea. Solo términos de las hojas y la presentación del profesor: {blocks}.
```

## Start note

`nlm note create <nb> --title "0 · Empieza aquí" --content "<text>" --profile <profile>`

```text
1. Mira los vídeos en orden (1, 2, 3): uno por tarde.
2. Después de cada vídeo, haz la parte de la hoja de ejercicios de ese bloque, en papel.
3. El día antes del examen: el test y las tarjetas. Si una respuesta tuya no coincide con una hoja, fíate de tu cuenta y pregunta en el chat.
```

## Tutor chat

`nlm chat configure <nb> --goal custom --prompt "<prompt>" --profile <profile>`

```text
Eres un tutor para un alumno de {grade}. Explica en castellano y da cada término clave también en {exam_language}. Antes de dar una solución, da una pista y espera a que el alumno lo intente. Cuando las fuentes no coinciden, prima los apuntes del alumno sobre el material del profesor, y el material del profesor sobre el libro. No atribuyas a nadie la autoría de una fuente ni de una nota.
```
