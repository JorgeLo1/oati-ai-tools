# oati-ai-tools

Herramientas de IA del equipo para trabajar en los repositorios de la Universidad Distrital (OAS) siguiendo los [lineamientos institucionales](https://github.com/udistrital/lineamientos_oas): planificación de issues antes de programar, skills con las reglas de cada tipo de repo, contexto del proyecto por módulos y controles que hacen cumplir el flujo.

Funciona completo en **Claude Code** (como plugin) y se puede portar a **otras IAs** (Cursor, Codex, Gemini CLI, Copilot…) con [PORTAR.md](PORTAR.md). Los **hooks de git** del equipo aplican a cualquier herramienta y a las personas.

---

## Contenido

- [Qué incluye](#qué-incluye)
- [Instalación](#instalación) · [Claude Code](#claude-code) · [Otras IAs](#otras-ias)
- [Cómo se trabaja una issue](#cómo-se-trabaja-una-issue)
- [Skills](#skills)
- [Bloqueos y cómo resolverlos](#bloqueos-y-cómo-resolverlos)
- [Especificaciones](#especificaciones)
- [Contexto del proyecto](#contexto-del-proyecto)
- [Preguntas frecuentes](#preguntas-frecuentes)
- [Actualizar y desinstalar](#actualizar-y-desinstalar)
- [Mantener este repositorio](#mantener-este-repositorio)

---

## Qué incluye

| Pieza | Qué hace | Dónde |
|---|---|---|
| **Reglas del equipo** | Flujo de trabajo, reglas de git y disciplina para la IA | [AGENTS.md](AGENTS.md) → se instala en la carpeta udistrital |
| **8 skills** | Planificar issues, commits/ramas OAS, endpoints, CRUD, MID, seguridad, documentación | [skills/](skills/) |
| **Agente de contexto** | Genera y actualiza la documentación de cada repo por módulos (`.claude/docs/`, local) | [agents/](agents/) |
| **Guardianes (Claude Code)** | Bloquean código sin plan aprobado o sin la skill del dominio, commits sin revisión de seguridad, push/PR, atribución a IA, edición de `.env` | [scripts/](scripts/), [hooks/hooks.json](hooks/hooks.json) |
| **Hooks de git** | Validan rama GitFlow, etiqueta del commit, atribución a IA y secretos **en cualquier herramienta** | [git-hooks/](git-hooks/) |
| **Contrato y pruebas** | Qué debe hacer cada control y sus casos de aceptación; base para portar a otras IAs | [spec/](spec/) |

Nada de esto se commitea en los repositorios institucionales: las reglas viven en la carpeta que agrupa los repos (no es un repo git), el contexto de cada repo en `.claude/` (excluido de git) y las especificaciones en `<udistrital>/.claude/specs/`.

## Instalación

### Requisitos

- Python 3.8+ y git.
- [GitHub CLI](https://cli.github.com) autenticado (`gh auth login`): las skills leen issues y descargan mockups.
- `git config --global user.name` y `user.email` configurados.
- Los repos udistrital en una carpeta común (por defecto `~/go/src/github.com/udistrital`).

### Paso común (todas las herramientas)

```bash
git clone https://github.com/JorgeLo1/oati-ai-tools.git ~/oati-ai-tools
cd ~/oati-ai-tools
bash instalar.sh
```

El instalador:
- pregunta la carpeta de los repos udistrital;
- instala las reglas del equipo (`AGENTS.md` y `CLAUDE.md`) en esa carpeta, con respaldo si ya existían;
- activa los hooks de git;
- detecta tus herramientas de IA;
- corre las pruebas.

No toca ningún repositorio ni hace commits. Opciones: `bash instalar.sh --ayuda`.

### Claude Code

```bash
claude plugin marketplace add JorgeLo1/oati-ai-tools     # o la ruta local del clon
claude plugin install oas@oas-udistrital
```

(Dentro de Claude Code también: `/plugin marketplace add …` y `/plugin install oas@oas-udistrital`.) Abre una sesión nueva. Las skills quedan como `/oas:planificar-issue`, `/oas:commit-oas`, etc.

Si antes tenías estas herramientas copiadas a mano en `~/.claude`, retíralas para no duplicar hooks: `bash instalar.sh --migrar-desde-manual` (las mueve a un respaldo).

### Otras IAs

Abre tu herramienta en la carpeta del clon y pídele:

> Lee PORTAR.md y síguelo para instalar estas herramientas en ti.

La IA identifica qué soporta tu herramienta y propone un plan, que debes aprobar. Después convierte reglas, skills y controles a su formato, se verifica con los casos de prueba y deja un informe en `~/.config/oas-ai-tools/<herramienta>/INFORME-PORTE.md`. Ahí verás qué quedó como **control real** y qué queda como **instrucción** que la IA debe obedecer. Los hooks de git siguen aplicando igual.

## Cómo se trabaja una issue

```
/oas:commit-oas          → rama feature/<nombre> desde develop (te pide confirmar)
/oas:planificar-issue    → lee la issue, mockups y código; te pregunta las decisiones (con una opción recomendada);
                           escribe la especificación y el plan → tú los apruebas
   ├─ por cada tarea:      /oas:crud-oas · /oas:mid-oas · /oas:endpoint-oas (las invoca sola)
   ├─ antes de commitear:  /oas:seguridad-oas → /oas:commit-oas (te pide confirmar)
   └─ al cerrar:           criterios verificados → /oas:documentar-cambios → /oas:doc-issue-oas
git push / PR            → los haces tú
```

En la práctica basta con decir *"vamos con la issue #905"*: la IA sigue el flujo y los guardianes no la dejan saltarse pasos. Las preguntas de decisión vienen con opciones y una recomendada; siempre puedes responder con texto libre.

## Skills

| Skill | Cuándo | Resultado |
|---|---|---|
| `planificar-issue` | Al empezar cualquier issue | Especificación en `<udistrital>/.claude/specs/<repo>-<n>.md` con alcance, fuera de alcance, decisiones, criterios → verificación, diseño técnico y plan de tareas por repo; luego conduce la ejecución |
| `commit-oas` | Crear rama / commitear | Rama GitFlow y commit con etiqueta OAS (`feat`, `fix`, `docs`, `test`, `refactor`, `devops`, `management`), sin atribución a IA |
| `endpoint-oas` | Crear o cambiar una ruta | URI en español y kebab-case sin verbos CRUD, verbo y status correctos, Swagger, consumidores afectados, versión SemVer |
| `crud-oas` | Tocar un `*_crud` | Modelo Mongo según lineamiento, schema/DTO/service/controller/module y pruebas con el patrón del repo (anexo Beego+Postgres) |
| `mid-oas` | Tocar un `*_mid` | Controller delgado, lógica en services, errores, concurrencia controlada, compensación en escrituras de varios pasos |
| `seguridad-oas` | Antes del commit/PR | Checklist institucional de seguridad sobre el diff, hallazgos por severidad; informe en `.claude/docs/seguridad/` |
| `documentar-cambios` | Al cerrar la tarea | Resumen compartible en `.claude/docs/cambios/<rama>.md` y documentación de módulos actualizada |
| `doc-issue-oas` | Documentar la issue | Comentario "Avances issue DD/MM/YYYY" listo para la issue (lo publica sólo si confirmas) |

## Bloqueos y cómo resolverlos

Los bloqueos son intencionales. La IA debe resolverlos sola siguiendo el mensaje; tú solo intervienes cuando te pide una aprobación.

| Mensaje (resumen) | Por qué | Qué pasa / qué haces |
|---|---|---|
| `La rama feature/x no tiene especificación` | No hay plan aprobado | La IA ejecuta `/oas:planificar-issue`; tú respondes las preguntas y apruebas |
| `La especificación sigue en borrador` | Plan no aprobado | Elige "Aprobar plan…" cuando te lo pregunte (una respuesta libre no cuenta) |
| `no incluye el repo … en repos:` | Se amplió el alcance | Elige "Aprobar cambio de alcance" si estás de acuerdo |
| `sin haber cargado /crud-oas` (o mid-oas) | Falta la skill del dominio | La IA la carga y reintenta |
| `agrega o modifica rutas HTTP sin /endpoint-oas` | Ruta sin revisar | La IA pasa por `/oas:endpoint-oas` |
| `Los commits … se hacen con /commit-oas` | Commit directo | La IA usa la skill; tú confirmas el mensaje |
| `no se ha ejecutado /seguridad-oas` | Commit con código sin revisión | La IA corre la revisión y te muestra los hallazgos |
| `git push está bloqueado` / `gh pr create` | Push y PR son tuyos | Ejecútalos tú |
| `--no-verify … bloqueado` | Saltarse los hooks de git | Corregir lo que reporta el hook |
| `contiene atribución a Claude/IA` | Regla 0.8 OAS | Quitar Co-Authored-By/menciones |
| `.env … no se edita desde Claude` | Secretos | La IA te dice qué variable agregar; la pones tú |
| Te pide confirmar editar skills/scripts/AGENTS.md | Configuración de las herramientas | Acepta sólo si tú pediste ese cambio |
| `✖ [oas-git-hooks] …` al commitear | Hook de git (rama, etiqueta, secretos) | Corrige lo indicado; si eres persona y es una emergencia: `OAS_HOOKS_OMITIR=1 git commit …` |

Para desactivar los guardianes en un repo puntual, crea el archivo vacío `<repo>/.claude/.skill-guard-off`. Para el contexto automático, `<repo>/.claude/.contexto-off`.

## Especificaciones

- Una por issue: `<udistrital>/.claude/specs/<repo-issue>-<numero>.md`. Sirve para todos los repos de la issue. Compártela como archivo o adjúntala a la issue.
- Estados: `borrador → aprobada → en-implementacion → implementada` (u `omitida` para fixes triviales, si tú lo eliges).
- Contiene objetivo, alcance, **fuera de alcance** (lo que se reporta como pendiente), decisiones con alternativas, criterios de aceptación → cómo se verifican, diseño técnico, impacto y plan de tareas.
- Si retomas una issue otro día: *"retomemos la issue #905"* y la IA continúa desde donde quedó la especificación.

## Contexto del proyecto

- La primera vez que trabajas en un repo sin contexto, el agente genera `.claude/CLAUDE.md` y `.claude/docs/` por módulos (en segundo plano).
- Cuando traes cambios de otras personas (`git pull`, merge, checkout), el agente actualiza sólo los documentos afectados. Tus propios commits los documentas con `/oas:documentar-cambios`.
- Está organizado por **dominios del negocio** con los mismos nombres y números en MF, MID y CRUD (por ejemplo `05-plan-mejoramiento.md` en los tres), y cada dominio enlaza a su equivalente en los otros repos. El índice (`.claude/docs/README.md`) dice qué leer según la tarea.
- Para llevar un contexto existente a esta estructura: pide *"reorganiza el contexto del proyecto"*.
- Estado: `python3 ~/oati-ai-tools/scripts/contexto-proyecto.py estado` dentro del repo. Calidad: `python3 ~/oati-ai-tools/scripts/verificar_contexto.py <repo>`.

## Preguntas frecuentes

**¿Se sube algo a los repos institucionales?** No. `.claude/` queda en `.git/info/exclude`; las reglas y especificaciones viven fuera de los repos.

**¿Qué pasa en proyectos que no son udistrital?** Los guardianes, el recordatorio y los hooks de git no actúan. Solo el agente de contexto puede ofrecer documentar el proyecto; desactívalo ahí con `.claude/.contexto-off`.

**¿Puedo trabajar sin plan en una rama feature?** Sí, si la tarea es trivial: dile a la IA que no necesita plan. Te preguntará "Omitir planificación" y quedará registrado.

**¿La IA puede aprobar el plan por mí?** No. El guardián exige tu respuesta a una pregunta con opciones que mencione la especificación, y cada respuesta sirve una sola vez.

**¿Y si mi repo ya usa husky u otros hooks de git?** Los hooks del equipo ejecutan después el hook propio del repo (`.git/hooks/<hook>`). Si el repo define `core.hooksPath` local, el instalador te avisa, porque en ese caso los del equipo no corren ahí.

**Los repos están en otra ruta.** Ejecuta `bash instalar.sh --udistrital <ruta>`, o define `UDISTRITAL_DIR`.

## Actualizar y desinstalar

```bash
cd ~/oati-ai-tools && git pull && bash instalar.sh -y     # reglas, hooks de git y pruebas
claude plugin marketplace update oas-udistrital           # Claude Code: trae la nueva versión del plugin
```

Otras IAs: después de `git pull`, pide de nuevo *"sigue PORTAR.md"*; la IA compara contra su informe anterior y aplica solo lo que cambió.

Desinstalar: `bash desinstalar.sh`. Las especificaciones y el contexto de cada repo se conservan.

## Mantener este repositorio

```
.claude-plugin/   plugin.json (versión) y marketplace.json
AGENTS.md         reglas del equipo (fuente única; CLAUDE.md de la plantilla la importa)
PORTAR.md         instrucciones para portar a otras IAs
skills/ agents/   skills y agente (formato abierto SKILL.md)
hooks/hooks.json  hooks del plugin de Claude Code
scripts/          guardianes y avisos (Python, sin dependencias) + tests/run_casos.py
git-hooks/        hooks de git del equipo + tests/test_git_hooks.sh
spec/             contratos.md (R0–R13, A1–A3, H1–H2) y casos.json (casos de aceptación)
plantillas/       CLAUDE.md para la carpeta udistrital
instalar.sh desinstalar.sh
```

Antes de publicar un cambio:

```bash
python3 scripts/tests/run_casos.py            # casos de los guardianes (spec/casos.json)
python3 scripts/tests/test_verificar_contexto.py   # verificador de contexto
bash git-hooks/tests/test_git_hooks.sh        # hooks de git
claude plugin validate --strict .             # catálogo
claude plugin validate --strict .claude-plugin/plugin.json skills agents
```

- Un cambio de comportamiento de un control se documenta primero en `spec/contratos.md` y se cubre con casos nuevos en `spec/casos.json`.
- Sube `version` en `.claude-plugin/plugin.json` (SemVer) y registra el cambio en [CHANGELOG.md](CHANGELOG.md): los usuarios de Claude Code reciben la actualización cuando cambia la versión.
- Commits con las mismas reglas del equipo (los hooks de git aplican si el repo vive en la organización udistrital).
