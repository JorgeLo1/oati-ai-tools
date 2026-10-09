# Contratos de comportamiento — oas-ai-tools

Describe **qué** hace cada pieza, sin depender de una herramienta de IA concreta. La implementación de referencia es la de Claude Code (`scripts/`, `hooks/hooks.json`); una IA que porte estas herramientas (ver [PORTAR.md](../PORTAR.md)) debe reproducir estos contratos con los mecanismos que tenga y verificarse contra [casos.json](casos.json).

Decisiones posibles de un control: **permitir**, **confirmar** (pedir confirmación explícita al usuario antes de ejecutar) y **bloquear** (impedir y explicar a la IA qué hacer; en el fin de turno, obligarla a continuar). Si varias reglas aplican a la misma acción, gana la más estricta (bloquear > confirmar > permitir). Si un control falla internamente o no puede analizar la acción, **confirma**; nunca permite en silencio.

## Definiciones

- **`<UDISTRITAL>`**: carpeta raíz de los repos udistrital. Prioridad: variable `UDISTRITAL_DIR` → `~/.config/oas-ai-tools/config.json` (`udistrital_dir`) → `~/go/src/github.com/udistrital`.
- **Repo udistrital**: repo git dentro de `<UDISTRITAL>`. **Tipo** del repo: `mf` si tiene `angular.json`; `crud` si su nombre termina en `_crud` o depende de `@nestjs/mongoose`; `mid` si termina en `_mid` o depende de `@nestjs/axios`.
- **Archivo de código**: extensiones `.ts .js .mjs .cjs .go .html .scss .css .json .sql .yml .yaml .conf .py .sh`.
- **Sesión**: la conversación actual con la IA. "Skill usada en la sesión" = la IA la cargó/invocó (o el usuario la ejecutó como comando) en algún momento de esta conversación.
- **Especificación**: archivo `<UDISTRITAL>/.claude/specs/*.md` con cabecera YAML (`issue`, `titulo`, `rama`, `repos: [..]`, `estado`, `actualizado`). Estados: `borrador`, `aprobada`, `en-implementacion`, `implementada`, `omitida`.
- **Aprobación del usuario**: respuesta del usuario a una pregunta de opciones (no texto libre) cuya **pregunta menciona el nombre del archivo** de la especificación sin extensión y cuya **opción elegida empieza** por el prefijo requerido. Cada aprobación se consume en una sola transición.
- **Commit real**: comando git cuyo subcomando efectivo es `commit` (contando `git -C`, opciones globales, variables antepuestas, `bash -c`, `eval` y alias de git), ejecutado sin error y cuya salida contiene `[<rama> <hash>]`.

## Controles sobre acciones de la IA (guardián)

### R0 — Alcance
Los controles R1–R8 y R13 sólo aplican a rutas y directorios dentro de `<UDISTRITAL>`. R5 aplica siempre. R9–R12 aplican a comandos git en repos udistrital (R10–R12 a cualquier repo).

### R1 — Contexto local libre
Editar `.claude/` de un repo (docs, cambios, seguridad, estado del contexto) → **permitir**. Excepción: R5 y R7.

### R2 — Skill de dominio
Editar o escribir un archivo de código de un repo `crud` sin `crud-oas` usada en la sesión → **bloquear** ("invoca la skill crud-oas, sigue sus pasos y reintenta"). Igual para `mid` con `mid-oas`. Repos `mf` y otros: sin skill de dominio exigida.

### R3 — Rutas HTTP
En repos `crud`/`mid`, si el contenido nuevo tiene más decoradores de ruta que el viejo (`@Controller(`, `@Get(`, `@Post(`, `@Put(`, `@Patch(`, `@Delete(`, `@All(` o `// @router`) y `endpoint-oas` no se usó en la sesión → **bloquear**.

### R4 — Archivos protegidos
- Escribir/editar `.env` o `.env.*` (salvo `.example`) → **bloquear** (la IA dice qué variable agregar; la pone el usuario).
- Editar a mano `pnpm-lock.yaml`, `package-lock.json`, `yarn.lock`, `go.sum`, o cualquier cosa bajo `node_modules/` o `dist/` → **bloquear**.
- Leer un `.env*` (salvo `.example`), con la herramienta de lectura o por terminal → **confirmar**.

### R5 — Configuración de las herramientas
Editar, crear o borrar: skills/agentes/scripts/plugins/ajustes de la herramienta de IA, los archivos de estas herramientas, `~/.config/oas-ai-tools/`, `<UDISTRITAL>/AGENTS.md`, `<UDISTRITAL>/CLAUDE.md`, o un archivo `.skill-guard-off`/`.contexto-off` → **confirmar**. (La IA no puede desactivar ni debilitar sus propios controles sin que el usuario lo vea.)

### R6 — Especificación aprobada antes del código
Si el repo está en una rama `feature/*` o `hotfix/*`, editar código exige una especificación con `rama:` igual a la rama actual, el nombre del repo en `repos:` y estado distinto de `borrador`:
- no existe → **bloquear** ("planifica con planificar-issue y obtén la aprobación del usuario");
- existe pero el repo no está en `repos:` → **bloquear** (actualizar el alcance con aprobación);
- está en `borrador` → **bloquear**.
En `develop`/`master`/otras ramas no se exige (el commit directo ahí lo frena el hook de git).

### R7 — Integridad de las especificaciones
- Sólo se editan con las herramientas de edición de la IA; por terminal → **bloquear**.
- Deben conservar la cabecera con `rama` y `repos` no vacíos → si no, **bloquear**. Estado fuera de la lista → **bloquear**.
- Transiciones que exigen aprobación del usuario (si no hay una aprobación válida sin consumir → **bloquear**):
  - de inexistente/`borrador` a `aprobada`/`en-implementacion`/`implementada` → prefijo `Aprobar plan`;
  - a `omitida` → prefijo `Omitir planificación`;
  - cambiar `rama` o `repos` de una especificación ya aprobada/en curso/implementada/omitida → prefijo `Aprobar cambio`.
- Crear en `borrador`, avanzar de `aprobada` a `en-implementacion` a `implementada`, o editar el cuerpo → **permitir**.

### R8 — Escrituras por terminal
Un comando de terminal que escribe, mueve o borra archivos se evalúa con R2, R4, R6 y R7 sobre cada destino (sin R3, porque no se ve el contenido). Deben detectarse al menos: redirecciones `>`/`>>`, `tee`, `sed -i`, `perl -i`, `cp`, `mv` (origen y destino), `rm`, `touch`, `truncate`, `dd of=`, `xargs`/`find -exec|-delete` con esos programas (destino desconocido = el directorio actual), `bash -c`/`sh -c`/`eval`, `cd` previo con rutas relativas y scripts de Python/Node/Perl inline o por heredoc que escriben archivos. Leer y escribir fuera de `<UDISTRITAL>` → **permitir**. Comando no analizable dentro de `<UDISTRITAL>` → **confirmar**.

### R9 — Commits
Un commit real en un repo udistrital:
- sin `commit-oas` usada en la sesión → **bloquear**;
- con archivos de código preparados (incluidos los de `-a`/`--all`) y sin `seguridad-oas` usada → **bloquear**;
- si no, sigue R11 (confirmación).
Mencionar "git commit" en un texto, `echo` o heredoc **no** es un commit.

### R10 — Operaciones git del usuario
`git push` y `gh pr create` → **bloquear** (los hace el usuario). `git pull`, `git rebase`, `git reset --hard` → **confirmar**. Otros (`status`, `log`, `diff`…) → **permitir**. Igual detección que R9 (texto ≠ comando).

### R11 — Mensaje de commit
Si el **mensaje** del commit (`-m`, `--message`, `-F`, heredocs del comando) contiene `Co-Authored-By`, `Claude`, `Anthropic`, `Generated with`, `noreply@anthropic`, 🤖 o las siglas `IA`/`AI`/`LLM` como palabra → **bloquear**. Lo que aparezca fuera del mensaje (rutas como `~/.claude`) no cuenta. Sin atribución → **confirmar**.

### R12 — No saltarse los hooks de git
`--no-verify` (o `-n` en commit) en commit/push/merge/rebase/am/cherry-pick, o la variable `OAS_HOOKS_OMITIR` en el comando → **bloquear**.

### R13 — Documentar al cerrar
Al terminar un turno de la IA dentro de `<UDISTRITAL>`, si hubo un commit real **en un repo udistrital** en la sesión (se determina el repo por el directorio donde se ejecutó el comando, sus `cd` y `git -C`; un commit en un repo fuera de `<UDISTRITAL>` no cuenta) y `documentar-cambios` no se usó **después** de ese commit → **bloquear una sola vez por commit** con la indicación: "si la tarea quedó cerrada, invoca documentar-cambios; si continúa, dilo en una línea y termina". Si la herramienta no permite forzar la continuación, convertirlo en un recordatorio visible.

## Avisos y contexto

### A1 — Recordatorio de reglas (cada mensaje del usuario)
Si el directorio de trabajo está dentro de `<UDISTRITAL>`, agregar al contexto de la IA un recordatorio de una línea con el tipo de repo y las skills que aplican (ver `scripts/reglas-udistrital.py`), indicando que lo ignore si el mensaje no implica trabajo de código.

### A2 — Contexto del proyecto (inicio de sesión, cada mensaje y tras comandos git de la IA)
Para el repo del directorio de trabajo (y los destinos de `git clone`/`init`/`pull`… que ejecute la IA):
- Proyecto con código y sin `.claude/CLAUDE.md` + `.claude/docs/` → pedir a la IA que lance el agente `contexto-proyecto` en **MODO generar** (en segundo plano).
- Con contexto y marca `.claude/.contexto-sync` distinta de `HEAD`: si entre la marca y `HEAD` hay commits de **otros autores** (correo distinto de `git config user.email`) que tocan archivos fuera de `.claude/` → pedir **MODO actualizar** con el rango, la lista de commits y archivos; si sólo hay commits propios → mover la marca en silencio. Un aviso por sesión y `HEAD`.
- Sin marca y con contexto → crear la marca en `HEAD` en silencio.
- Opt-out por repo: archivo `.claude/.contexto-off` (lo crea el usuario).

### A3 — Agente `contexto-proyecto`
Modos `generar`, `reorganizar`, `actualizar`, `documentar` (ver `agents/contexto-proyecto.md`). Sólo escribe en `<REPO>/.claude/`; nunca hace git add/commit/push/checkout; agrega `.claude/` a `.git/info/exclude`; al terminar `generar`/`actualizar` mueve la marca a `HEAD` (`documentar` no la mueve).

Estructura exigida:
- **Por dominio funcional**, no por carpeta técnica, con **los mismos dominios, nombres y números en todos los repos del sistema** (el sistema es la primera carpeta bajo `<UDISTRITAL>`; si un repo hermano ya tiene contexto, se adopta su numeración).
- `CLAUDE.md` ≤ 80 líneas; cada documento ≤ 300 líneas salvo los que contienen tablas generadas; `docs/README.md` es un índice orientado a tareas y lista todos los documentos.
- Documentos transversales según el tipo de repo (MF: estados y flujos, acciones por rol, notificaciones, servicios y endpoints; MID: endpoints, integraciones, reglas y estados; CRUD: modelo de datos, endpoints y filtros).
- Cada dominio tiene la sección "En otros repos" con enlaces relativos reales a los documentos (o archivos) de los repos hermanos.
- Las tablas derivables de una fuente única se generan con un script registrado en `CLAUDE.md` y van entre `<!-- generado:inicio <comando> -->` y `<!-- generado:fin -->`.
- Antes de terminar, `scripts/verificar_contexto.py <REPO>` debe pasar (tamaños, enlaces, índice, bloques generados, secretos).

## Hooks de git del equipo (cualquier herramienta y personas)

Se instalan como `core.hooksPath` global; sólo validan repos udistrital (dentro de `<UDISTRITAL>` o con remoto `github.com/udistrital`) y después ejecutan el hook propio del repo (`.git/hooks/<hook>`) si existe.

### H1 — pre-commit
- Rama actual: `develop`/`master`/`main` sin merge en curso → **rechazar**; si no, debe cumplir `^(feature|hotfix)/[a-z0-9][a-z0-9._-]*$` o `^release/[0-9]+\.[0-9]+\.[0-9]+$` y no mencionar claude/anthropic/ai/ia/bot/llm/gpt/copilot.
- Archivos preparados: `.env*`, llaves (`.pem`, `.key`, `.p12`, `.pfx`, `.keystore`, `.jks`, `id_rsa*`, `id_ed25519*`), `credentials*.json` → **rechazar** (salvo `.example`, `.sample`, `.template`, `.dist`, `.pub`).
- Líneas agregadas: llave privada, AWS access key, JWT, cadena de conexión con usuario:clave, token de GitHub, credencial literal (`password|secret|token|api_key… = "…"`, excepto en tests y Markdown) → **rechazar**.

### H2 — commit-msg
Ignora mensajes que empiezan por `Merge `, `Revert "`, `fixup! `, `squash! `, `amend! `. La primera línea debe cumplir `^(feat|fix|docs|test|refactor|devops|management): \S.*$` y el mensaje completo no puede contener atribución a IA (lista de R11, sin distinguir mayúsculas).

Escape **sólo para personas**: `OAS_HOOKS_OMITIR=1 git commit …` (R12 lo bloquea para la IA). Pruebas: `git-hooks/tests/test_git_hooks.sh`.
