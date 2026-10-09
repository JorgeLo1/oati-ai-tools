---
name: planificar-issue
description: Planifica y conduce una issue de punta a punta (spec-driven) — lee la issue de GitHub, issues relacionadas, mockups adjuntos, el contexto .claude/docs y el código; hace las preguntas de decisión con opciones y una recomendada (respuesta abierta disponible); diseña con /endpoint-oas, /crud-oas y /mid-oas dentro de la especificación (alcance, fuera de alcance, decisiones, criterios → verificación, impacto); arma el plan de tareas por repo (CRUD → MID → MF); y tras la aprobación del usuario ejecuta tarea por tarea invocando la skill de cada una, con /seguridad-oas y /commit-oas en cada commit, y cierra con /documentar-cambios y /doc-issue-oas. Nada se implementa sin aprobación. Úsala cuando el usuario diga "/planificar-issue", "planifica la issue #N", "vamos con la issue", "empecemos la issue", "analiza la issue", "retomemos la issue", o al iniciar cualquier tarea de desarrollo en un repo udistrital.
---

# Planificar issue (spec-driven)

Ninguna línea de código antes de que la especificación y el plan estén **aprobados por el usuario**. La especificación es el documento compartible de la issue: reemplaza las decisiones sueltas en el chat o en la memoria, y la reutilizan `/documentar-cambios` y `/doc-issue-oas`.

```
0 Entrada → 1 Investigar → 2 Supuestos + preguntas → 3 Especificación (diseño con skills) ⛔ → 4 Plan de tareas ⛔ → 5 Ejecución (skill por tarea) → 6 Cierre
```

## Skills que orquesta

| Fase | Skill / agente | Para qué |
|---|---|---|
| 0 | `/commit-oas` (fase A) | Crear la rama si no existe (con confirmación) |
| 1 | agente `contexto-proyecto` | Generar el contexto de un repo afectado que no lo tenga |
| 3 | `/endpoint-oas` (modo diseñar) | Rutas nuevas o cambiadas, **dentro de la especificación** |
| 3 | `/crud-oas` (§1 Modelado, §3) | Colecciones/campos/índices y datos existentes, **dentro de la especificación** |
| 3 | `/mid-oas` (§1, §4, §5) | Servicios del MID: capas, concurrencia, escrituras en varios pasos |
| 5 | `/crud-oas`, `/mid-oas`, `/endpoint-oas` | Implementar cada tarea con las reglas de su skill |
| 5 | `/seguridad-oas` → `/commit-oas` (fase B) | Antes de cada commit, con confirmación del usuario |
| 6 | `/documentar-cambios`, `/doc-issue-oas` | Documentar a partir de la especificación |

"Invocar una skill" = usar la herramienta `Skill` con su nombre y seguir sus pasos; citarla no basta. Así también queda registrada para el guardián `skill-guard`, que bloquea editar código de un CRUD/MID, agregar rutas o hacer commits si la skill correspondiente no se invocó en la sesión.

## Especificación: ubicación, cabecera y aprobaciones

- Ruta: `<UDISTRITAL>/.claude/specs/<repo-issue>-<numero>.md` (p. ej. `sisifo_documentacion-906.md`), donde `<UDISTRITAL>` es la carpeta de los repos udistrital: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/oas_config.py" udistrital` (por defecto `~/go/src/github.com/udistrital`). Carpeta no versionada, común a todos los repos de la issue, compartible como archivo. Sin issue: `sin-issue-<slug>.md` e `issue: sin-issue`.
- Edítala **sólo con Edit/Write** (el guardián bloquea modificarla por Bash).
- Cabecera YAML obligatoria (el guardián la lee para permitir editar código en `rama` y `repos`):

```yaml
---
issue: udistrital/sisifo_documentacion#906
titulo: <título de la issue>
rama: feature/<nombre>
repos: [plan_anual_auditoria_mf, plan_anual_auditoria_mid]
estado: borrador        # borrador | aprobada | en-implementacion | implementada | omitida
actualizado: AAAA-MM-DD
---
```

- **Aprobaciones validadas por el guardián.** Se piden con `AskUserQuestion`; la **pregunta debe incluir el nombre del archivo sin extensión** (p. ej. `sisifo_documentacion-906`) y la opción, empezar exactamente así:

| Transición | Etiqueta de la opción (primera, recomendada) |
|---|---|
| `borrador` → `aprobada` (aprobar el plan) | `Aprobar plan y empezar (Recomendado)` o `Aprobar plan, sólo dejar planificado` |
| cualquier estado → `omitida` | `Omitir planificación (Recomendado)` |
| cambiar `rama` o `repos` de una especificación aprobada | `Aprobar cambio de alcance (Recomendado)` |

  Cada respuesta autoriza **una** transición. Si el usuario elige otra opción o responde en texto libre, no hay aprobación: ajusta y vuelve a preguntar.
- `estado: omitida` sólo si el usuario dice que la tarea no necesita plan (fix trivial): crea la especificación mínima (cabecera con `estado: borrador` + motivo), pregunta con `Omitir planificación` y luego cambia el estado.

## Fase 0 — Entrada

1. Referencia: `#N` (repo por defecto `udistrital/sisifo_documentacion`), URL o descripción.
2. Si ya existe la especificación, **retómala**: muestra estado, tareas pendientes y último Historial, y continúa desde la fase que corresponda.
3. Rama: si no existe, invoca `/commit-oas` (fase A) para proponerla y crearla con confirmación; si depende de agrupar issues, decídelo en la Fase 2 y créala antes de la Fase 5. Registra el nombre en `rama:`.

## Fase 1 — Investigar (sin preguntar todavía)

- **Issue**: `gh issue view <N> -R <repo> --json title,body,labels,comments,milestone` → descripción, subtareas, criterios de aceptación, DoR/DoD, comentarios (pueden traer cambios de alcance).
- **Issues relacionadas** mencionadas (diseño, hermanas): léelas igual. Revisa también sus especificaciones en `.claude/specs/`.
- **Mockups/imágenes adjuntas**: descárgalas y míralas:
  ```bash
  curl -sSL -H "Authorization: token $(gh auth token)" -o <scratchpad>/mockup-<n>.png <url de user-attachments>
  ```
  y ábrelas con Read. Si la issue menciona un zip/carpeta local o un `DESIGN.md` sin ruta, pídela en la Fase 2.
- **Contexto**: `.claude/CLAUDE.md` y `.claude/docs/` de cada repo afectado. Si un repo afectado no tiene contexto, lanza el agente `contexto-proyecto` (en el plugin: `oas:contexto-proyecto`) con `MODO: generar. REPO: <repo>. SCRIPT: ${CLAUDE_PLUGIN_ROOT}/scripts/contexto-proyecto.py` y espera.
- **Código**: componentes/servicios/endpoints a tocar, quién más los usa (compartidos), IDs en `environment`/`config`, y si el **backend ya soporta** lo que piden la issue o el mockup (busca el campo/endpoint en CRUD y MID). Esto decide qué entra y qué no.
- **Repos afectados** y orden (CRUD → MID → MF).

## Fase 2 — Supuestos y preguntas

1. En texto, lista los **supuestos** tomados del código (con `archivo:línea`) para que el usuario corrija los falsos.
2. Pregunta **sólo lo que cambia el resultado y el código no responde**, con `AskUserQuestion`:
   - Hasta 4 preguntas por llamada; varias rondas si hace falta.
   - 2–4 opciones excluyentes. **La primera es tu recomendación** y termina en `(Recomendado)`; su descripción dice por qué, con evidencia ("el CRUD no tiene el campo `version`; implementarlo exige backend").
   - Las demás opciones, con su consecuencia real (esfuerzo, riesgo, repos).
   - `preview` para comparar layouts (mockup ASCII) o fragmentos de código.
   - No agregues "Otro": la herramienta siempre permite **respuesta abierta**; intégrala y repregunta sólo si queda ambigua.
   - `multiSelect: true` cuando no se excluyen (p. ej. qué elementos del mockup se omiten).
   - Lo obvio o con convención en el repo no se pregunta: se decide y se anota como supuesto.
3. Temas típicos (los que apliquen): elementos sin soporte en backend (omitir y reportar / simular / ampliar a CRUD-MID); componentes compartidos (modificar / aislar con input o flag / duplicar); roles y permisos; estados y transiciones; datos (campos, obligatoriedad, paginado, datos existentes); estilo visual en issues de mockups; agrupación de rama/PR; criterios de aceptación ambiguos.

## Fase 3 — Especificación ⛔

**Diseño con las skills de dominio** (sólo si la issue toca backend; aquí no se implementa nada):

- Rutas nuevas o cambiadas → invoca `/endpoint-oas` en modo **diseñar**; su tabla, consumidores y versión van a "Diseño técnico → Endpoints".
- Colecciones/tablas o campos → invoca `/crud-oas` y aplica **sólo** §1 (Modelado) y §3 (modificar existente); van a "Diseño técnico → Modelo de datos".
- Lógica en el MID → invoca `/mid-oas` y aplica §1, §4 y §5; va a "Diseño técnico → MID".
- Si alguna regla de esas skills genera una decisión de negocio, pregúntala (formato de la Fase 2).

Escribe el archivo (`estado: borrador`):

```markdown
# <Título corto> — <issue>

## Objetivo
## Contexto
## Alcance
## Fuera de alcance
| Elemento | Motivo | Se reporta en la issue |
|---|---|---|
## Decisiones
| # | Decisión | Alternativas descartadas | Por qué |
|---|---|---|---|
## Supuestos
## Criterios de aceptación → verificación
| Criterio (de la issue) | Cómo se cumple | Cómo se verifica (rol, estado, pasos) | Resultado |
|---|---|---|---|
## Diseño técnico
### Endpoints (de /endpoint-oas)
| Verbo | Ruta | Params / Query | Body | Respuesta `Data` | Status | Repo |
|---|---|---|---|---|---|---|
### Modelo de datos (de /crud-oas)
| Colección.campo | Tipo | Obligatorio | Referencia | Descripción |
|---|---|---|---|---|
### MID (de /mid-oas)
### MF
## Impacto
(compartidos y cómo se aíslan; consumidores; permisos, estados, notificaciones; docs de .claude/docs; versión de API)
## Riesgos y preguntas abiertas
## Plan de tareas
## Historial
- AAAA-MM-DD: creación (borrador)
```

(Omite las subsecciones de "Diseño técnico" que no apliquen.) Muestra un resumen (objetivo, alcance, fuera de alcance, decisiones clave) con enlace al archivo y pregunta con `AskUserQuestion` (mencionando el nombre del archivo): `Aprobar especificación (Recomendado)` · `Ajustar` · `Replantear alcance`. Itera hasta que la apruebe; el estado sigue en `borrador`.

## Fase 4 — Plan de tareas ⛔

Completa "Plan de tareas":

```markdown
### <repo> (en orden: CRUD → MID → MF)
- [ ] T1 — <qué> · Archivos: <≤5> · Skill: /crud-oas + /endpoint-oas · Verificación: <build/test/prueba manual> · Depende de: —
- [ ] T2 — …
### Commits
- <cómo se agrupan: por tarea o por grupo lógico>
### Cierre
- [ ] /seguridad-oas sobre el diff de cada repo
- [ ] /commit-oas
- [ ] Criterios de aceptación verificados
- [ ] /documentar-cambios
- [ ] /doc-issue-oas (si la issue lo exige)
```

Reglas: cada tarea deja el sistema compilando y es verificable sola; ≤5 archivos (si no, divídela); dependencias explícitas; la skill que la gobierna; verificación concreta.

Pregunta con `AskUserQuestion` (mencionando el nombre del archivo): `Aprobar plan y empezar (Recomendado)` · `Aprobar plan, sólo dejar planificado` · `Ajustar plan`. Con cualquiera de las dos primeras: `estado: aprobada` + línea en Historial (el guardián valida esa respuesta). Si eligió sólo dejar planificado, termina aquí.

## Fase 5 — Ejecución (tarea por tarea)

`estado: en-implementacion` y ejecuta **en orden** (respetando dependencias):

1. **Invoca la skill de la tarea antes de tocar su código** (`/crud-oas` en el CRUD, `/mid-oas` en el MID, `/endpoint-oas` si crea o cambia rutas) y sigue sus pasos usando el diseño aprobado (no lo rediseñes; si la skill revela un problema, punto 5).
2. Implementa sólo lo de la tarea (≤5 archivos), con herramientas de edición (no `sed`/`echo >` por Bash).
3. Verifica como dice la tarea y reporta el resultado real.
4. Marca `[x]` en la especificación y avisa en una línea: tarea, verificación, siguiente.
5. **Desvíos**: si algo cambia alcance, decisiones, diseño o plan, **para**, pregunta (formato de la Fase 2), actualiza la especificación (Decisiones / Diseño técnico / Fuera de alcance / Historial) y sigue. Agregar un repo o cambiar la rama exige `Aprobar cambio de alcance`. Cambios grandes → volver a la Fase 3.
6. **Commits** (según lo acordado en "Commits"): invoca `/seguridad-oas` sobre el diff, reporta lo introducido por el cambio, y luego `/commit-oas` (fase B) con confirmación. Nunca un commit directo.
7. Si el usuario pausa, deja la especificación al día (tareas marcadas y siguiente paso en Historial) para retomarla con `/planificar-issue <issue>`.

## Fase 6 — Cierre

1. Completa la columna "Resultado" de "Criterios de aceptación → verificación" con lo comprobado (o "por confirmar" si no se pudo).
2. `estado: implementada`, Historial actualizado.
3. Invoca `/documentar-cambios`.
4. Si el DoD incluye "Documentación de issue realizada" o el usuario lo pide, invoca `/doc-issue-oas` (los pendientes salen de "Fuera de alcance").
5. Recuerda que push y PR los hace el usuario; entrega el texto del PR si lo pide.

## Reglas

- Fases 1–4: no escribas código ni crees archivos fuera de la especificación (las skills de dominio sólo diseñan).
- Ramas y commits sólo con `/commit-oas`; sin push ni PR.
- Si la issue no trae criterios de aceptación o son vagos, propónlos en la especificación y confírmalos.
- No guardes decisiones de la issue en la memoria: van en la especificación.
