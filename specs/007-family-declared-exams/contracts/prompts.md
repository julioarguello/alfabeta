# Contract: the prompts of an exam with no announcement

These join `skills/study-pack/prompts.md` in slice 1, as three new sections. The three texts of an announced exam do
not change. Not measured: the family reads the first real run (plan, gate 1; spec SC-010).

## The placeholders

| Placeholder | Source |
|---|---|
| `{exam_name}` | `Examen del martes 12 de mayo` with a date, `Examen sin fecha` with none |
| `{notes_corrections}` | Empty when the topic's `notebook/bloques.md` is missing or has no «Correcciones a los apuntes». Otherwise «Correcciones ya comprobadas en estos apuntes, que prevalecen sobre lo anterior aunque los apuntes insistan o las fuentes callen; en estos puntos no enseñes su versión y añade en esa sección o junto al problema «Corrige en tus apuntes: …»: » and that section's lines verbatim, then a space. A section is a heading holding those words, in any case and at any level, up to the next heading of the same or a higher level, or any line holding «Preguntas sobre los apuntes»; a file may hold one per block. Those words with no line read give a warning on stderr that names the folder. `exam build` reads the file itself, with no Claude in the run |
| `{part}` | Empty for one topic. Over several, with no announcement: «; este examen abarca varios temas y este cuaderno solo tiene «<topic>» (parte N de M): cubre solo ese tema», with no final full stop. It replaces the announced variant, which refers to points of an announcement |

## Theory sheet — for an exam with no announcement

```text
Hoja de teoría para estudiar un examen, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · {exam_name} — Teoría y plan de estudio». Empieza con esta frase, tal cual: «Sin anuncio del profesor: esta hoja cubre todo «{topic}» y el alcance no está confirmado.». No inventes ni cites ningún anuncio, y no dejes fuera ninguna parte del tema{part}. Si los apuntes del alumno tienen un esquema del tema, las secciones de la hoja son sus ramas, en su orden y con sus palabras, y nombras la rama; lo que el esquema no tiene va después de su rama más cercana o aparte, diciendo de qué fuente sale, sin llamarlo opcional. Si no tienen esquema, las secciones siguen el orden de los apuntes, y luego el de las fotocopias de Classroom y el del libro. Los apuntes de clase del alumno mandan en la estructura y las palabras, no en los hechos; las fotocopias de Classroom y el libro completan lo que falta en ellos. Si una fotocopia o el libro contradicen un hecho de los apuntes y no se contradicen entre sí, enseña lo que dicen y añade en esa sección «Corrige en tus apuntes: …». No lo hagas si los apuntes insisten en ese hecho (repetido en otra página, en un recuadro, subrayado, marcado como importante o escrito como palabras del profesor), ni si las fotocopias y el libro no coinciden entre sí: deja lo que dicen los apuntes, sin decir nada en contra en la sección, y ponlo en una última parte de la hoja titulada «Para la familia», con las dos versiones. Donde las fotocopias y el libro callan, se queda lo que dicen los apuntes. Una rama que ninguna fuente explica se nombra sin desarrollarla y va también a «Para la familia». Cada término va primero en {language}, tal como lo escribe el material de clase, y después en castellano; si los apuntes, las fotocopias y el libro llaman de forma distinta a una misma cosa, o usan una palabra para dos cosas, muestra cada forma y cómo distinguirlas. Después de esa frase, un plan ({slot}) en una tabla Hora | Qué | Cómo: una fila por sección, un descanso de cinco minutos y una última fila de unos quince minutos de hoja en blanco, para escribir de memoria y en {language} lo que el examen pide reproducir, corregir con esta hoja y rodear lo que falle. Cada sección acaba con una prueba para hacer sin mirar, con sus respuestas. Señala las trampas típicas. Los problemas no van aquí, sino en la hoja «Problemas tipo». Como mucho {pages} páginas A4. Comprueba dos veces cada número. {notes_corrections}
```

## Problems sheet — for an exam with no announcement

The text of «Problems sheet — for an exam», with its opening replaced by this one, identical from «Usa solo los
problemas de las fotocopias» on, and with `{notes_corrections}` at its end:

```text
Hoja de problemas para un examen, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · {exam_name} — Problemas tipo». Empieza con esta frase, tal cual: «Sin anuncio del profesor: esta hoja cubre todo «{topic}» y el alcance no está confirmado.». Si las fuentes no tienen fotocopias con problemas, dilo en una frase y no inventes ninguno. 
```

## Start note — for an exam with no announcement

The announced note says «Hoy», which is false for a preparation days ahead, for the reason the theory text drops
«mañana». This one holds with or without a date.

```text
Para este examen ({exam_name}): «{theory}» ({slot}). Sigue el plan con el que empieza la hoja.
```
