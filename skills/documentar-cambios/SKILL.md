---
name: documentar-cambios
description: Al terminar una tarea, documenta lo hecho en el contexto local del proyecto (.claude/docs/) — actualiza los documentos de los módulos afectados y genera un resumen compartible de la tarea en .claude/docs/cambios/<rama>.md (objetivo, qué cambió, archivos, decisiones, cómo probar, pendientes, commits). Úsala cuando el usuario diga "/documentar-cambios", "documenta lo que hicimos", "documenta los cambios de la tarea", "deja el contexto de esta tarea" o similar. No reemplaza a /doc-issue-oas (comentario para la issue de GitHub).
---

# Documentar cambios de la tarea

Deja registro de la tarea actual en el contexto local del proyecto para consultarlo a futuro y compartirlo con compañeros. El trabajo pesado lo hace el agente `contexto-proyecto` en **MODO documentar**; esta skill reúne lo que sólo sabe la sesión actual (el *porqué*) y se lo pasa.

Argumentos opcionales (`$ARGUMENTS`): número/enlace de issue, rama base (`base=main`) o una descripción corta de la tarea.

## Paso 1 — Datos del repo

Ejecuta desde la raíz del repo (`git rev-parse --show-toplevel`):

- `REPO`: raíz del repo.
- `RAMA`: `git branch --show-current`.
- `BASE`: la indicada en argumentos; si no, la primera que exista entre `develop`, `main`, `master` (`git rev-parse --verify -q <rama>`; prueba también `origin/<rama>`).
- Comprueba que haya algo que documentar: `git log --oneline <BASE>...HEAD` y `git status --porcelain`. Si ambos están vacíos, díselo al usuario y termina.

## Paso 2 — Notas de la sesión

Si existe la especificación de la issue en `<UDISTRITAL>/.claude/specs/` (`<UDISTRITAL>` es la carpeta de los repos udistrital: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/oas_config.py" udistrital` (por defecto `~/go/src/github.com/udistrital`)) (cabecera `rama:` igual a `RAMA`), es la fuente principal: toma de ella objetivo, decisiones, fuera de alcance, criterios y pruebas, y complétalas con lo de la conversación. Pasa su ruta al agente en `NOTAS`.

Redacta `NOTAS` a partir de **esta conversación** (el agente no la ve), en viñetas cortas:

- **Objetivo**: qué se pidió y por qué (issue, criterio de aceptación).
- **Decisiones**: qué se eligió, alternativas descartadas y razón, acuerdos con el usuario.
- **Trampas**: bugs o comportamientos raros encontrados y cómo se resolvieron.
- **Pruebas**: qué se probó y cómo (rol, estado, datos).
- **Pendientes**: lo que quedó fuera o por confirmar.
- **Issue**: enlace si se conoce (también revisa la memoria del proyecto).

Si falta información clave (p. ej. el objetivo no está claro en la conversación), pregúntale al usuario en una sola pregunta antes de seguir.

## Paso 3 — Lanzar el agente

Lanza el agente `contexto-proyecto` (en el plugin: `subagent_type: oas:contexto-proyecto`) en primer plano y este prompt:

```
MODO: documentar. REPO: <REPO>. BASE: <BASE>. RAMA: <RAMA>. SCRIPT: ${CLAUDE_PLUGIN_ROOT}/scripts/contexto-proyecto.py.
NOTAS:
<NOTAS>
```

## Paso 4 — Informar

Al terminar, dile al usuario en pocas líneas:

- La ruta del resumen de la tarea (`.claude/docs/cambios/<archivo>.md`) como enlace clicable, y que es un Markdown autocontenido que puede compartir tal cual (copiarlo, pegarlo en un chat o adjuntarlo).
- Qué documentos de módulo se actualizaron.
- Lo que el agente marcó como "(por confirmar)".

No hagas `git add`/`commit`: `.claude/` es local y está excluido del repo.
