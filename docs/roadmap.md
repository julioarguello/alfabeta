# Roadmap

## classroom-sync (prueba de concepto)

Objetivo: que Classroom alimente sola la carpeta y el cuaderno de cada tema, y que las fechas lleguen al calendario.

Vías, de más a menos oficial:

1. **API de Google Classroom** (OAuth). Lo ideal (tareas, fechas, materiales, anuncios), pero en cuentas de
   Google Workspace for Education de **menores de 18** las apps de terceros están bloqueadas salvo que el
   administrador del centro las autorice. Hay que probarlo por centro.
2. **Resúmenes por email para tutores legales** (oficial, sin riesgos): tareas pendientes, próximas entregas
   y anuncios, diarios o semanales, al Gmail del padre/madre. El centro o el profesorado debe invitar al tutor.
   No incluye adjuntos.
3. **Navegador integrado con la cuenta del alumno** (solo lectura): recorrer las clases, leer la pestaña
   *Trabajo de clase* y descargar los materiales a la carpeta del tema.

Prueba de concepto en marcha con la vía 3 (lectura de clases, tareas, fechas y materiales).

## plan-de-estudio

- Fuente: entregas y exámenes de `classroom-sync`.
- Salida: eventos en Google Calendar (entrega/examen) y bloques de repaso espaciado antes de cada examen,
  enlazando al cuaderno del tema.

## Otras ideas

- Generar automáticamente en el cuaderno: resumen en audio, tarjetas y cuestionario por tema.
- Más plataformas de libro digital (Santillana, Anaya, Edelvives, Vicens Vives…).
- Versión en inglés de los temas que la plataforma no ofrece, traduciendo el Markdown.
