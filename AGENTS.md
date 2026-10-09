# Reglas del equipo — repositorios udistrital (OAS)

> **Si eres una IA distinta de Claude Code y estás instalando o configurando estas herramientas, lee y sigue [PORTAR.md](PORTAR.md) antes de hacer cualquier otra cosa.**

Estas reglas aplican a todo el trabajo con IA sobre los repositorios de la Universidad Distrital que viven bajo la carpeta `<UDISTRITAL>` (por defecto `~/go/src/github.com/udistrital`): SISIFO y cualquier otro sistema. Las skills y agentes se usan **por iniciativa propia**, sin esperar a que el usuario los pida. Si una regla no aplica a la tarea, sáltala sin comentarlo; si aplica, no la omitas.

Lineamientos institucionales (fuente de verdad): https://github.com/udistrital/lineamientos_oas

## 1. Stacks

- **MF Angular** (single-spa): `*_mf`, `*_cliente`, `core_mf_cliente`.
- **API NestJS + MongoDB**: `*_crud`, `*_mid` (p. ej. `SISIFO/Backend`).
- **API Go/Beego + PostgreSQL**: repos con `go.mod` (p. ej. `cumplidos_crud`, `cumplidos_mid`).

Antes de proponer código, identifica el stack del repo y sigue el patrón de un módulo existente parecido.

## 2. Skills y agente

| Skill / agente | Para qué |
|---|---|
| `commit-oas` | Ramas GitFlow y commits con etiquetas OAS, siempre con confirmación del usuario |
| `planificar-issue` | Especificación y plan aprobados por el usuario antes de escribir código; conduce la ejecución |
| `endpoint-oas` | Diseñar o revisar rutas REST (nombre, verbo, status, Swagger, consumidores, versión) |
| `crud-oas` | Recursos y modelo de datos en APIs CRUD (Nest+Mongo; anexo Beego+Postgres) |
| `mid-oas` | Lógica de negocio en APIs MID (capas, errores, concurrencia, compensación) |
| `seguridad-oas` | Checklist de seguridad OAS sobre el diff antes del commit/PR |
| `documentar-cambios` | Resumen compartible de la tarea + actualización del contexto del proyecto |
| `doc-issue-oas` | Comentario "Avances issue" para la issue de GitHub |
| agente `contexto-proyecto` | Genera/actualiza el contexto `.claude/docs/` del repo por módulos |

En Claude Code, como plugin, se invocan con prefijo: `/oas:commit-oas`, agente `oas:contexto-proyecto`.

## 3. Contexto del proyecto

- Si el repo tiene `.claude/CLAUDE.md` y `.claude/docs/`, **léelos** (índice y doc del módulo) antes de tocar un módulo.
- Si falta el contexto o se trajeron cambios (pull/merge/checkout con commits de otras personas), lanza el agente `contexto-proyecto` antes de seguir.
- Al cambiar flujos, estados, endpoints o botones, actualiza el documento correspondiente de `.claude/docs/`.
- `.claude/` es local: está en `.git/info/exclude` y nunca se commitea.

## 4. Flujo de una tarea

| Momento | Acción obligatoria |
|---|---|
| Empieza una tarea (issue, feature, bug) | `commit-oas` → proponer y crear la rama GitFlow (con confirmación) |
| Antes de escribir código | `planificar-issue` → especificación + plan **aprobados por el usuario** |
| Crear o cambiar una ruta (`@Controller`/`@Get`/`@Post`/…, `@router` de Beego) | `endpoint-oas` antes de escribirla |
| Tocar un `*_crud` | `crud-oas` |
| Tocar un `*_mid` | `mid-oas` |
| Cambiar un endpoint o campo que consume otro repo | Buscar consumidores en MF/MID y avisar |
| Terminar de implementar, antes del commit | `seguridad-oas` sobre el diff; reportar lo introducido por el cambio |
| Commit | `commit-oas` (siempre con confirmación explícita del usuario) |
| Tarea terminada | Cerrar la especificación (criterios verificados, `estado: implementada`) y `documentar-cambios` |
| Documentar la issue (pedido o "Documentación implementación" en el DoD) | `doc-issue-oas` |

Una tarea que abarca varios repos aplica cada skill en el repo que corresponde.

## 5. Especificaciones de issues

- Viven en `<UDISTRITAL>/.claude/specs/<repo-issue>-<numero>.md` (no versionadas; se comparten como archivo).
- Son la fuente de verdad de alcance, decisiones y pendientes: consúltala antes de implementar y actualízala si algo cambia. No guardes esas decisiones en la memoria de la IA.
- Cabecera YAML obligatoria (`issue`, `titulo`, `rama`, `repos`, `estado`, `actualizado`); estados `borrador → aprobada → en-implementacion → implementada` (u `omitida`).
- **Aprobaciones**: sólo el usuario aprueba. Se le pregunta con opciones; la pregunta menciona el nombre del archivo y la opción empieza por `Aprobar plan…`, `Aprobar cambio de alcance…` u `Omitir planificación…`. Una respuesta libre ("sí, dale") no es aprobación. Cada respuesta autoriza una sola transición.
- Preguntas de decisión: opción recomendada primero con `(Recomendado)` y su porqué; la respuesta abierta siempre está disponible.

## 6. Git (reglas no negociables)

- Ramas: sólo `feature/<nombre>` (desde develop), `hotfix/<nombre>` (desde master), `release/X.Y.Z`; nombres en minúsculas con guiones. Nada de `fix/`, `bugfix/`, `feat/`, `chore/`…
- Commits: primera línea `<etiqueta>: <descripción en español>`, con etiqueta `feat`, `fix`, `docs`, `test`, `refactor`, `devops` o `management`; issue al final si aplica (`udistrital/sisifo_documentacion#900`).
- **Prohibido** en commits, ramas, PR y tags: `Co-Authored-By`, "Generated with…", 🤖 o cualquier mención a Claude, Anthropic, IA, AI o LLM. El autor es siempre el usuario configurado en git.
- Ramas y commits siempre con `commit-oas` y **confirmación explícita** del usuario antes de `git checkout -b`, `git add` o `git commit`. "Procede hasta finalizar" no autoriza commitear sin confirmar.
- **No ejecutar** `git push`, `gh pr create`, `git pull`, `git rebase`, `git reset --hard`, `git commit --amend` ni `--no-verify` sin que el usuario lo pida. El push y los PR los hace el usuario: al terminar, sólo indicar los comandos y el texto del PR.
- Los hooks de git del equipo (`pre-commit`, `commit-msg`) validan ramas, etiquetas, atribución y secretos para cualquier herramienta. No se saltan.

## 7. Disciplina de trabajo

- **Alcance**: haz sólo lo pedido. Nada de refactors, renombres, reformateos, dependencias nuevas ni "mejoras" que nadie pidió. Lo que encuentres fuera del alcance (bugs, deuda) se **reporta en una línea**, no se corrige.
- **Antes de cambios en varios archivos**: plan breve y espera confirmación si hay decisiones de negocio o de modelo de datos.
- **No inventes**: endpoints, campos, IDs de estado/rol, colecciones y variables se verifican en el código, `environment`/`config` o el CRUD. Si no existe, pregunta.
- **Ambigüedad**: si la petición admite dos lecturas que cambian el resultado, una sola pregunta concreta antes de implementar; si no, decide con el patrón del repo y dilo.
- **Terminado = verificado**: build (y lint/test del módulo si funcionan) antes de decir que algo está listo; reporta el resultado real, incluidos fallos.
- **Edición de archivos** sólo con las herramientas de edición de la IA, nunca con `sed -i`/`echo >`/scripts por terminal.
- **Nada de secretos** en el código ni en `environment.ts` de los MF; no leer ni editar `.env` sin permiso del usuario.
- **Respuestas**: en español, concisas, sin repetir lo ya dicho; referencias `archivo:línea` a lo tocado.
- **Bloqueos de los guardianes** (`[skill-guard]`, hooks de git): no son errores a esquivar. Haz lo que indican (invocar la skill, pedir la aprobación, corregir el mensaje) y reintenta. No intentes rodearlos.
