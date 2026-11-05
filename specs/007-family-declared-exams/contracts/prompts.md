# Contract: the prompts of an exam with no announcement

These join `skills/study-pack/prompts.md` in slice 1, as three new sections. The three texts of an announced exam do
not change. Not measured: the family reads the first real run (plan, gate 1; spec SC-010).

## The new placeholder

| Placeholder | Source |
|---|---|
| `{exam_name}` | `Examen del martes 12 de mayo` with a date, `Examen sin fecha` with none |

## Theory sheet — for an exam with no announcement

```text
Hoja de teoría para estudiar un examen, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · {exam_name} — Teoría y plan de estudio». Empieza con esta frase, tal cual: «Sin anuncio del profesor: esta hoja cubre todo «{topic}» y el alcance no está confirmado.». No inventes ni cites ningún anuncio, y no dejes fuera ninguna parte del tema{part}. Si los apuntes del alumno tienen un esquema del tema, las secciones de la hoja son sus ramas, en su orden y con sus palabras, y nombras la rama; lo que el esquema no tiene va después de su rama más cercana o aparte, diciendo de qué fuente sale, sin llamarlo opcional. Si no tienen esquema, las secciones siguen el orden de los apuntes, y luego el de las fotocopias de Classroom y el del libro. Mandan los apuntes de clase del alumno; las fotocopias de Classroom y el libro solo completan lo que falta en ellos. Cada término va primero en {language}, tal como lo escribe el material de clase, y después en castellano; si los apuntes, las fotocopias y el libro llaman de forma distinta a una misma cosa, o usan una palabra para dos cosas, muestra cada forma y cómo distinguirlas. Después de esa frase, un plan ({slot}) en una tabla Hora | Qué | Cómo: una fila por sección, un descanso de cinco minutos y una última fila de unos quince minutos de hoja en blanco, para escribir de memoria y en {language} lo que el examen pide reproducir, corregir con esta hoja y rodear lo que falle. Cada sección acaba con una prueba para hacer sin mirar, con sus respuestas. Señala las trampas típicas. Los problemas no van aquí, sino en la hoja «Problemas tipo». Como mucho {pages} páginas A4. Comprueba dos veces cada número.
```

## Problems sheet — for an exam with no announcement

The text of «Problems sheet — for an exam», with its opening replaced by this one, and identical from «Usa solo los
problemas de las fotocopias» on:

```text
Hoja de problemas para un examen, para un alumno de {grade} que da la asignatura en {language} y estudia en castellano. Título: «{subject} · {exam_name} — Problemas tipo». Empieza con esta frase, tal cual: «Sin anuncio del profesor: esta hoja cubre todo «{topic}» y el alcance no está confirmado.». 
```

## Start note — for an exam with no date

An exam with a date and no announcement uses the note of an announced exam, since it needs only the day.

```text
Para este examen sin fecha: «{theory}» ({slot}). Sigue el plan con el que empieza la hoja.
```
