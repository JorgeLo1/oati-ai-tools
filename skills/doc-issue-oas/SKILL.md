---
name: doc-issue-oas
description: Genera la documentación en Markdown de lo implementado para una issue de SISIFO (udistrital/sisifo_documentacion), con el formato de comentario "Avances issue DD/MM/YYYY" que usa el equipo en sus issues — descripción, cambios por repositorio (CRUD / MID / MF) con archivos y fragmentos antes/después, comportamiento, pruebas con espacios para capturas y commits. Úsala cuando el usuario diga "documenta la issue", "documentación de la issue #N", "genera el avance de la issue", "/doc-issue-oas", o al terminar una tarea cuyo criterio de aceptación sea "Documentación implementación".
---

# Documentación de issue (SISIFO / OAS)

Produce un Markdown listo para pegar como comentario de avance en la issue. El formato replica los comentarios de documentación que ya existen en las issues del proyecto 58 (por ejemplo #846, #790, #730, #639, #624, #565 de `udistrital/sisifo_documentacion`).

## Entradas

- **Número de issue** (obligatorio). Repo por defecto: `udistrital/sisifo_documentacion`. Si el usuario no lo da, pídelo.
- **Fecha del avance**: hoy, en formato `DD/MM/YYYY`, salvo que el usuario indique otra (p. ej. "06 y 09/03/2026").

## Paso 1 — Leer la issue

```bash
gh issue view <N> -R udistrital/sisifo_documentacion --json title,body,comments,url
```

Si `gh` no está instalado o autenticado, pide al usuario que ejecute `gh auth login`. Extrae:

- Título y párrafo inicial ("Se requiere…") → base de la **Descripción**.
- Lista de **Sub Tareas** → cada una puede convertirse en una sección propia.
- **Repositorios** mencionados en el cuerpo.
- Comentarios previos del usuario actual (su login: `gh api user --jq .login`): si ya hay avances documentados, el nuevo comentario documenta **solo lo nuevo** (titúlalo como continuación, p. ej. "Migración del sellado de hallazgos al MID").

## Paso 2 — Reunir lo que se hizo

Si existe la especificación de la issue (`<UDISTRITAL>/.claude/specs/<repo-issue>-<numero>.md`; `<UDISTRITAL>` es la carpeta de los repos udistrital: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/oas_config.py" udistrital` (por defecto `~/go/src/github.com/udistrital`)), úsala como base: objetivo, decisiones, "Fuera de alcance" (pendientes a reportar), tabla de criterios → verificación (pruebas) y commits del plan de tareas.

Los repos locales están en:

- Frontend: `<UDISTRITAL>/SISIFO/Frontend/<repo>` (`plan_anual_auditoria_mf`, `ejecucion_auditoria_mf`, `usuario_rol_mf`, `core_mf_cliente`, `auditoria_plan_mejoramiento_root_mf`)
- Backend: `<UDISTRITAL>/SISIFO/Backend/<repo>` (`plan_anual_auditoria_crud`, `plan_anual_auditoria_mid`, `ejecucion_auditoria_crud`, `ejecucion_auditoria_mid`, `usuario_rol_crud`)

Fuentes, en orden de prioridad:

1. Lo hecho en esta conversación (si la tarea se implementó aquí).
2. En cada repo afectado: `git status`, `git diff`, `git log --oneline develop..HEAD` y `git show <sha>` de la rama de la issue.
3. Lo que el usuario explique.

Para cada repo anota: archivos tocados, métodos/funciones creados o modificados, endpoints nuevos (`MÉTODO /ruta`), campos de modelo/DTO, variables de entorno, y el porqué de cada cambio. Para los commits ya publicados, arma el enlace `https://github.com/udistrital/<repo>/commit/<sha completo>`.

No inventes cambios ni pruebas: si algo no se puede verificar, deja un marcador `<!-- TODO: ... -->` y avísalo.

## Paso 3 — Redactar con este formato

Estilo: español, tercera persona impersonal y pasado ("Se agregó…", "Se corrigió…", "Se implementó…"). Nombres de archivos, métodos, campos y endpoints entre backticks. Separar bloques grandes con `---`. Frases cortas en viñetas; nada de relleno.

~~~markdown
> Avances issue DD/MM/YYYY

# <Título corto de lo implementado>

## Descripción

<1–3 párrafos: qué se pedía, qué se hizo y por qué (decisiones tomadas, p. ej. "Tras la daily se decidió…").>

---

## Cambios realizados

### Backend (<repo_crud>)

- Se agregó el campo `campo` al schema de <entidad>.
- ...

### MID (<repo_mid>)

- Se implementó el método `metodo()` en `archivo.service.ts`.
- Se expuso el endpoint:

```http
PUT /recurso/:id/accion
```

### Frontend (<repo_mf>)

**`archivo.component.ts`**
- <cambio y motivo>

Antes:
```typescript
<código anterior relevante>
```

Después:
```typescript
<código nuevo relevante>
```

<!-- Insertar captura: <qué debe mostrar> -->

### Comportamiento

<Flujo resultante en viñetas (o en bloque ```txt con flechas → si es una cadena de llamadas). Incluir manejo de errores, idempotencia, casos borde.>

---

## Pruebas realizadas

### Prueba 1 — <qué se valida>

<!-- Insertar captura: <qué debe verse> -->

---

### Prueba 2 — <qué se valida>

<!-- Insertar captura -->

---

### Commits:

**Crud:** https://github.com/udistrital/<repo>/commit/<sha>
**Mid:** https://github.com/udistrital/<repo>/commit/<sha>
**Mf:** https://github.com/udistrital/<repo>/commit/<sha>
~~~

### Variantes según la issue

- **Issue con varias subtareas** (como #639, #624): en lugar de agrupar por repo, una sección por subtarea — `# Subtarea N: <texto de la subtarea>` o `## Subtarea N — <texto>` — cada una con **Archivos modificados** (bloque de rutas), cambios, `### Resultado` y su captura.
- **Bugs**: usar tabla `| Ajuste | Antes | Ahora |` cuando haya varias correcciones puntuales.
- **Flags / configuración**: mostrar el valor en `environment` y el flujo "normal" vs "con el flag" en bloques ```txt.
- **Go (CRUD/MID beego)**: fragmentos con comentarios `// Antes` / `// Después` en el mismo bloque ```go.
- Omite las secciones que no apliquen (p. ej. sin cambios en MID → no hay sección MID). No dejes encabezados vacíos.

## Paso 4 — Entregar

1. Guarda el archivo en `~/docs-issues/issue-<N>-<YYYY-MM-DD>.md` (crea la carpeta si no existe). No lo guardes dentro de los repos.
2. Muestra el Markdown completo en la respuesta y la ruta del archivo.
3. Lista los marcadores de captura (`<!-- Insertar captura ... -->`) y los `TODO` pendientes para que el usuario los complete.
4. **Ofrece** publicarlo como comentario en la issue y hazlo **solo si el usuario lo confirma explícitamente**:

```bash
gh issue comment <N> -R udistrital/sisifo_documentacion --body-file ~/docs-issues/issue-<N>-<YYYY-MM-DD>.md
```

Nunca edites el cuerpo de la issue, ni marques casillas, ni cambies el estado en el proyecto sin pedido explícito.
