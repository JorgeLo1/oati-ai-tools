# oati-ai-tools

Herramientas de IA del equipo para trabajar en los repositorios de la Universidad Distrital (OAS) siguiendo los [lineamientos institucionales](https://github.com/udistrital/lineamientos_oas): planificación de issues antes de programar, skills con las reglas de cada tipo de repo, contexto del proyecto por módulos y controles que hacen cumplir el flujo.

Funciona completo en **Claude Code** (como plugin) y se puede portar a **otras IAs** (Cursor, Codex, Gemini CLI, Copilot…) con [PORTAR.md](PORTAR.md). Los **hooks de git** del equipo aplican a cualquier herramienta y a las personas.

---

## Contenido

- [Qué incluye](#qué-incluye)
- [Instalación](#instalación) · [Claude Code](#claude-code) · [Otras IAs](#otras-ias)
- [Cómo se trabaja una issue](#cómo-se-trabaja-una-issue)
- [Skills](#skills)
- [Pruebas funcionales con Playwright](#pruebas-funcionales-con-playwright)
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
| **11 skills** | Planificar issues, commits/ramas OAS, endpoints, CRUD, MID, seguridad, documentación, code review de PR, release y despliegue, pruebas funcionales | [skills/](skills/) |
| **Agente de contexto** | Genera y actualiza la documentación de cada repo por módulos (`.claude/docs/`, local) | [agents/](agents/) |
| **Guardianes (Claude Code)** | Bloquean código sin plan aprobado o sin la skill del dominio, commits sin revisión de seguridad, push/PR, atribución a IA, edición de `.env` | [scripts/](scripts/), [hooks/hooks.json](hooks/hooks.json) |
| **Hooks de git** | Validan rama GitFlow, etiqueta del commit, atribución a IA, secretos y que pasen las pruebas unitarias relacionadas con lo que commiteas, **en cualquier herramienta** | [git-hooks/](git-hooks/) |
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

**Activa la actualización automática.** Claude Code sólo la trae activada para los marketplaces oficiales de Anthropic; para este (de terceros) viene apagada y el plugin se queda en la versión que instalaste. Se activa una sola vez:

1. Abre Claude Code en la terminal (`claude`). Si trabajas en el panel de VS Code y `/plugin` no te muestra la pantalla de marketplaces, abre la terminal integrada y ejecuta `claude`: el ajuste es de tu usuario y vale para los dos.
2. Escribe `/plugin` y Enter.
3. Ve a la pestaña **Marketplaces** (flechas o Tab), selecciona **oas-udistrital** y Enter.
4. Elige **Enable auto-update** (activar la actualización automática).

Con eso, cada vez que abras Claude Code trae la última versión publicada. La sesión que ya estaba abierta sigue con la versión que cargó: reiníciala para ver la nueva. La CLI (`claude plugin …`) no tiene opción para activarla; sólo `claude plugin marketplace update oas-udistrital` y `claude plugin update oas@oas-udistrital` para actualizar a mano.

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
   ├─ antes de commitear:  /oas:seguridad-oas (incluye la suite completa) → /oas:commit-oas (te pide confirmar)
   └─ al cerrar:           /oas:pruebas-funcionales-oas (si hay interfaz) → criterios verificados
                           → /oas:documentar-cambios → /oas:doc-issue-oas
git push / PR            → los haces tú

/oas:code-review-oas <PR>  → revisar el PR de un compañero (sin descargar sus cambios; informe local)
/oas:release-oas          → preparar un release: versión, Swagger OpenAPI 2.0, checklist del ambiente, rollback
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
| `code-review-oas` | Revisar el PR de otra persona | Lee el PR con `gh` (sin checkout, fetch ni pull en tu repo), entiende la implementación de punta a punta y valida sus contratos contra los repos de los que depende (los clona si no los tienes y genera su contexto si falta). Lo mide contra la issue (y la especificación si la tienes), las reglas de endpoint/CRUD/MID, el checklist de seguridad, ramas y commits OAS y bugs de lógica, con tono de compañeros. Informe en `.claude/docs/revisiones/pr-<n>.md` con comentarios listos para copiar. Nunca publica en GitHub |
| `release-oas` | Preparar un release o paso a pruebas/producción | Versión SemVer, rama `release/X.Y.Z`, Swagger actualizado y convertido a OpenAPI 2.0 para el registro en WSO2, checklist del lineamiento de despliegues con responsables, plan de rollback (N y N−1), tag en `master` y limpieza. Informe en `.claude/docs/releases/`. No hace push, PR, tags ni despliegues |
| `pruebas-funcionales-oas` | Validar flujos con interfaz o crear specs e2e | Playwright en el MF: escenarios desde los criterios de aceptación, login automático por rol, `@lectura`/`@escritura`, evidencias para `doc-issue-oas`. Ver [Pruebas funcionales con Playwright](#pruebas-funcionales-con-playwright) |

Unitarias (uso local): el `pre-commit` corre las relacionadas con lo que commiteas y quien cambia un contrato arregla los tests que rompe. Las funcionales tienen su sección: [Pruebas funcionales con Playwright](#pruebas-funcionales-con-playwright). Detalle de las reglas en [AGENTS.md](AGENTS.md) §8.

## Pruebas funcionales con Playwright

Pruebas automatizadas de los flujos de los MF en el navegador, a partir de los criterios de aceptación de cada issue, con Playwright, TypeScript y Page Object Model. Sirven al equipo antes de cada PR y, cuando se autorice, a funcionamiento y al pipeline después de cada despliegue a pruebas. Las conduce la skill `/oas:pruebas-funcionales-oas`, que usa la skill oficial `playwright-cli` de Microsoft y la plantilla [plantillas/e2e/](plantillas/e2e/). Implementación de referencia: `plan_anual_auditoria_mf/e2e/` (SISIFO, udistrital/sisifo_documentacion#939).

### Instalar (una vez por persona)

```bash
npm install -g @playwright/cli@latest                     # herramienta de navegador
npx skills add microsoft/playwright-cli@playwright-cli -g  # su skill para Claude Code
```

En WSL, para ver el navegador (`--ui`, `--headed`, `--debug`) hay que tener la interfaz gráfica: `guiApplications=true` en `C:\Users\<usuario>\.wslconfig` y `wsl --shutdown` (luego `ls /tmp/.X11-unix/` muestra `X0`). Sin ella, `npx playwright test --ui-port=9323` y abrir `http://localhost:9323` en el navegador de Windows.

### Qué queda en el repo de cada MF

La primera vez, la skill copia la plantilla como una tarea más de la issue. `e2e/` es **autocontenido** (su propio `package.json` con npm): no toca las dependencias ni el lockfile del MF.

```
e2e/
  package.json · package-lock.json · tsconfig.json
  playwright.config.ts          # roles del proyecto y opciones de ejecución
  .env.e2e.example              # nombres de las variables (versionado)
  README.md                     # guía para el equipo y funcionamiento
  core/                         # genérico (plantilla del plugin): login WSO2 por rol, bloqueo de
                                #   escrituras en @lectura, simularGet, CORS del core-mf, clase base del POM
  pages/                        # page objects del proyecto (shell.page.ts = menú del root)
  specs/<funcionalidad>.plan.md # plan de pruebas de cada funcionalidad
  tests/<modulo>/<escenario>.spec.ts   # un escenario por archivo
  .env.e2e · .auth/ · playwright-report/ · test-results/   # NO versionados
```

Además, en el MF: entradas en `.gitignore` y exclusión de `e2e/` en Jest y en el `tsconfig.json` raíz.

### Usuarios de prueba y login

- Cuentas **dedicadas** del ambiente de pruebas, una por rol; nunca personales ni de producción.
- Mismas variables en todos los MF, en `e2e/.env.e2e`: `E2E_BASE_URL`, `E2E_<ROL>_USER`, `E2E_<ROL>_PASS` (`jefe-dependencia` ↔ `E2E_JEFE_DEPENDENCIA_*`). La variable dice el rol real de la cuenta.
- `e2e/.env.e2e` lo crea y llena cada persona (los guardianes no dejan a la IA escribirlo) y la IA nunca lee sus valores. En Drone, las mismas variables como secrets.
- El login lo hace `core/global-setup.ts` una vez por rol y reutiliza la sesión mientras siga vigente: sin traza ni video (grabarían la contraseña) y sin reintentos (WSO2 bloquea la cuenta tras varios fallos). Un rol sin usuario se omite. Si no hay usuario para un rol, la persona inicia sesión a mano y la sesión se guarda.

### Etiquetas

Cada escenario lleva el módulo (`@programacion`, el nombre de su carpeta en `src/app/modules/`, o `@navegacion`), el rol (`@auditor`: cada proyecto corre solo los suyos) y si es **`@lectura`** (sólo consulta) o **`@escritura`** (crea o cambia datos). En los `@lectura` el marco **aborta** cualquier escritura a las APIs, por eso pueden correr en el ambiente compartido. **`@simulado`** marca los que preparan un estado reescribiendo una respuesta GET.

### En la planificación

`/oas:planificar-issue` busca en `e2e/` los escenarios y page objects que usan las pantallas que cambia la issue, agrega a la especificación una sección **Pruebas E2E** (escenarios nuevos y existentes a ajustar) y una tarea de escenarios en el plan; el cierre exige todos los escenarios del módulo en verde.

### Comandos

Desde `e2e/`:

```bash
npm test                                   # todo
npx playwright test --grep @<modulo>       # antes del PR: todos los del módulo
npx playwright test --ui                   # modo UI: escenario por escenario, pasos y red
npx playwright test --headed               # el navegador haciendo el flujo
E2E_BASE_URL=<url de pruebas> npm run test:lectura   # funcionamiento, contra el ambiente de pruebas
npm run report                             # reporte HTML con capturas (última corrida)
```

Resultados: consola (✓/✘), `e2e/playwright-report/` (reporte) y `e2e/test-results/` (trazas de los que fallan: `npx playwright show-trace …`). Las trazas y el reporte contienen la sesión de la cuenta de prueba: sólo dentro del equipo.

### Varios en el mismo módulo

| Situación | Qué se hace |
|---|---|
| Issue nueva | Plan propio por funcionalidad y escenarios en archivos propios: dos issues en paralelo no chocan |
| Cambias una pantalla (texto, botón, paso) | Actualizas en el mismo PR el page object y los escenarios que la usan |
| Antes del PR | Corres **todos** los escenarios del módulo, no sólo los tuyos |
| Llegan cambios de otros al módulo (pull) | El aviso del plugin sugiere correr sus escenarios |
| Falla el escenario de otra persona por su cambio | Le pasas el escenario y la traza; decide el autor |
| Cambias `e2e/core/` o un page object compartido | Corres todas las e2e del MF; `core/` se mejora en la plantilla del plugin |

### Evidencias

Cada escenario adjunta la captura del criterio que verifica. La skill deja el informe en `.claude/docs/pruebas/<rama>.md`, que usan `/oas:doc-issue-oas` (sección "Pruebas realizadas") y `/oas:seguridad-oas`.

### Drone y funcionamiento (pendiente de autorización)

Todavía no van en CI. La propuesta es un paso `e2e_pruebas` después del despliegue al ambiente de pruebas (`cd e2e && npm ci && npm run test:lectura`, imagen de Playwright, usuarios como secrets, sólo `@lectura`, detiene el pipeline si falla), y que funcionamiento corra los mismos `@lectura` contra el ambiente de pruebas. La skill deja el borrador de la solicitud; no se edita `.drone.yml` sin autorización.

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
| `✖ [oas-git-hooks] Commit bloqueado: fallan pruebas relacionadas…` | Tu cambio rompe specs relacionados (Jest o `go test`) | Corrige el código o actualiza el test si el cambio de comportamiento es intencional y explícalo en el PR. Si la suite no arranca (configuración rota) sólo avisa y deja pasar. Emergencia de una persona: `OAS_PRUEBAS_OMITIR=1 git commit …` |
| `⚠ [oas-git-hooks] Pruebas relacionadas: la suite no arranca…` | Las pruebas corren con el Node que tengas activo en la terminal; si el repo pide otra versión (`.nvmrc`, p. ej. Node ≥24.9 en los MID con NestJS 12), Jest no arranca | `nvm use` en el repo antes de commitear (o desde VS Code, que la terminal integrada tenga esa versión). Si con la versión correcta sigue sin arrancar, es configuración rota del repo: repórtalo |

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
cd ~/oati-ai-tools && git pull && bash instalar.sh -y     # reglas (AGENTS.md), hooks de git y pruebas
claude plugin marketplace update oas-udistrital           # Claude Code: trae la nueva versión del plugin
```

Son dos actualizaciones distintas:
- **Plugin de Claude Code** (skills, guardianes, agente): con la actualización automática activada (ver [Instalación](#claude-code)) llega solo al abrir Claude Code; si no, `claude plugin marketplace update oas-udistrital && claude plugin update oas@oas-udistrital` (o `/plugin` → *Marketplaces* → `oas-udistrital` → actualizar), y reinicia la sesión. `instalar.sh` avisa si el plugin instalado está atrás de la versión del repo.
- **Reglas y hooks de git** (`<udistrital>/AGENTS.md`, `~/.config/oas-ai-tools/git-hooks`): son copias, **no se actualizan con el plugin**. Cada vez que cambien hay que hacer `git pull` en el clon y volver a correr `bash instalar.sh`.

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
plantillas/       CLAUDE.md para la carpeta udistrital y e2e/ (marco de pruebas Playwright)
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
- Sube `version` en `.claude-plugin/plugin.json` (SemVer) y registra el cambio en [CHANGELOG.md](CHANGELOG.md): los usuarios de Claude Code reciben la actualización cuando cambia la versión, **si tienen activada la actualización automática** del marketplace (o la actualizan a mano). Si el cambio toca `AGENTS.md` o `git-hooks/`, avisa al equipo que vuelva a correr `instalar.sh`.
- Commits con las mismas reglas del equipo (los hooks de git aplican si el repo vive en la organización udistrital).
