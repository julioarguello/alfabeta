# classroom-sync: investigación (octubre 2026)

Prueba hecha con la cuenta de un alumno de 3º ESO (menor de 18) en un centro con Google Workspace for Education.

| Vía | Resultado | Notas |
|---|---|---|
| **API de Classroom vía OAuth Playground** | ❌ `Servicio no permitido` | El centro desactiva las herramientas de desarrollador de Google para alumnos. |
| **API de Classroom con cliente OAuth propio** (cliente estándar de Google Cloud, scopes de solo lectura) | ❌ `Error 400: access_not_configured` | «El administrador de tu institución debe revisar» la app. Política de Google para menores: las apps de terceros no configuradas por el centro quedan bloqueadas. Solo se desbloquea si el centro autoriza explícitamente un cliente OAuth concreto. |
| **Navegador integrado con la cuenta del alumno** (solo lectura) | ✅ funciona | Se leen las clases, *Tareas pendientes* con fechas (esta semana / próxima / más tarde / sin fecha) y *Trabajo de clase* organizado por temas, con los enlaces de Drive de cada material. Falta resolver la descarga fiable de adjuntos de Drive. |
| **Resúmenes por email para tutores** | ⏳ sin probar | Requiere que el centro invite al padre/madre como tutor. Da tareas pendientes, próximas y anuncios; no da adjuntos. Se leería con el conector de Gmail. |

## Conclusión

Para centros que no autorizan apps de terceros (lo habitual con alumnos menores), la API no es una opción
sin la colaboración del centro. `classroom-sync` se construye sobre:

1. **Navegador en solo lectura** → tareas, fechas y materiales por tema.
2. **Resúmenes de tutor por Gmail** → respaldo para fechas y anuncios, si el centro da de alta al tutor.
3. **API** solo si el centro aprueba un cliente OAuth propio de alfabeta (petición formal al responsable TIC).

Reglas: nunca entregar tareas, ni abrir evaluaciones, ni modificar nada en Classroom.
