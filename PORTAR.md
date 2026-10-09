# PORTAR.md — Instrucciones para una IA que instala estas herramientas

**Para quién es este archivo:** para la IA (Cursor, Codex, Gemini CLI, GitHub Copilot, Windsurf u otra) que un integrante del equipo abre en este repositorio para instalarlo. Si eres **Claude Code**, no lo necesitas: instala el plugin como dice el [README](README.md#claude-code).

**Tu tarea:** reescribir (portar) estas herramientas al formato y a los mecanismos de **tu propia herramienta**, de modo que el usuario trabaje con las mismas reglas, skills y controles que el equipo usa en Claude Code. No copies a ciegas: entiende cada pieza por su contrato y reprodúcela con lo que tu herramienta ofrece. Si algo no se puede reproducir, dilo con exactitud.

---

## Reglas para ti durante el porte (no negociables)

1. **No modifiques ningún repositorio institucional** (nada dentro de `<UDISTRITAL>` salvo `<UDISTRITAL>/AGENTS.md`, `<UDISTRITAL>/CLAUDE.md` y `<UDISTRITAL>/.claude/specs/`, que instala `instalar.sh`). No hagas `git add`, `commit`, `push`, `checkout` ni nada que cambie historial o ramas.
2. Escribe sólo en: la configuración de **tu** herramienta (carpeta de usuario/global), `~/.config/oas-ai-tools/<tu-herramienta>/`, y este repositorio clonado si el usuario te lo pide.
3. **Antes de modificar un archivo de configuración existente**, haz una copia `<archivo>.bak-oas-<AAAAMMDD>` y menciónala en el informe.
4. **No debilites los controles.** Si tu herramienta no puede hacer cumplir una regla, no la omitas: déjala como instrucción explícita y repórtala como "no controlada" en el informe.
5. **No inventes capacidades.** Antes de usar un mecanismo de tu herramienta (archivo de reglas, skills, comandos, hooks, subagentes), **verifica en su documentación actual o con `--help`** que existe y cómo se configura. Las indicaciones de este archivo sobre herramientas concretas son orientativas.
6. **Muestra el plan y espera la aprobación del usuario** antes de escribir nada (Paso 3).
7. Mantén el idioma (español) y el contenido de reglas y skills; sólo adapta formato, nombres de herramientas internas y rutas.

---

## Paso 0 — Leer las fuentes

Lee completos, en este orden:

1. [AGENTS.md](AGENTS.md) — reglas del equipo (lo que la IA debe hacer siempre).
2. [spec/contratos.md](spec/contratos.md) — contrato de cada control (R0–R13), avisos (A1–A3) y hooks de git (H1–H2).
3. [spec/casos.json](spec/casos.json) — casos de aceptación con la decisión esperada.
4. `skills/*/SKILL.md` — las 8 skills (formato abierto de Agent Skills: carpeta con `SKILL.md`, cabecera YAML `name` + `description`).
5. `agents/contexto-proyecto.md` — el agente de contexto.
6. `scripts/` — implementación de referencia (Python 3, sin dependencias externas): `skill-guard.py`, `git-guard.py`, `shell_cmd.py`, `contexto-proyecto.py`, `reglas-udistrital.py`, `oas_config.py`. Su protocolo de entrada/salida es el de hooks de Claude Code (JSON por stdin; salida `hookSpecificOutput.permissionDecision` = `allow|ask|deny`, o `decision: block` en `Stop`).

Comprueba que `instalar.sh` ya corrió (existe `~/.config/oas-ai-tools/config.json` y `git config --global core.hooksPath` apunta a `~/.config/oas-ai-tools/git-hooks`). Si no, pide al usuario que lo ejecute primero: instala los hooks de git y las reglas en `<UDISTRITAL>`, que valen para cualquier herramienta.

`<UDISTRITAL>` = salida de `python3 scripts/oas_config.py udistrital`.

## Paso 1 — Identificarte y listar tus capacidades

Determina qué herramienta eres y su versión, y responde con evidencia (documentación o `--help`):

| Capacidad | Pregunta | Ejemplos orientativos (verificar) |
|---|---|---|
| Instrucciones globales | ¿Dónde se ponen reglas que apliquen a todos los proyectos o a una carpeta? ¿Lees `AGENTS.md` de carpetas padre del repo? | `~/.codex/AGENTS.md`, `~/.gemini/GEMINI.md`, User Rules de Cursor, instrucciones de usuario de Copilot |
| Skills / comandos | ¿Soportas el formato `SKILL.md`? Si no, ¿comandos personalizados, prompt files, reglas invocables? | Carpeta de skills de la herramienta, `commands/*.toml`, `*.prompt.md`, reglas `.mdc` |
| Preguntas con opciones | ¿Puedes preguntar al usuario con opciones seleccionables? ¿Queda registro de la respuesta? | Herramienta de pregunta nativa, o pregunta numerada en texto |
| Subagentes | ¿Puedes lanzar un agente con su propio prompt/herramientas? | Subagentes/modos personalizados |
| Hooks | ¿Ejecutas comandos antes/después de leer, editar, ejecutar en terminal, al enviar un mensaje, al iniciar sesión, al terminar el turno? ¿Pueden **bloquear** o **pedir confirmación**? ¿Qué JSON reciben? | Hooks de la herramienta (algunas los tienen, con formatos propios) |
| Historial de sesión | ¿El hook puede saber qué skills/comandos se usaron y qué respondió el usuario en la sesión (archivo de transcript, id de sesión)? | Ruta del transcript en el JSON del hook |

## Paso 2 — Mapear cada componente

Completa esta tabla para tu herramienta (es el núcleo del plan):

| # | Componente | Contrato | Destino preferido | Si no existe el mecanismo |
|---|---|---|---|---|
| 1 | Reglas del equipo | `AGENTS.md` | Tu archivo de instrucciones **global**, con una sección que diga: "Cuando el directorio de trabajo esté dentro de `<UDISTRITAL>`, aplica las reglas de `<UDISTRITAL>/AGENTS.md`" y su contenido (o una referencia si tu herramienta importa archivos). No modifiques los repos para esto | — (siempre existe algún archivo de instrucciones) |
| 2 | 8 skills | `skills/*/SKILL.md` | Formato nativo de skills, conservando nombre, descripción (es lo que dispara su uso automático) y cuerpo | Comandos/prompt files con el mismo nombre + una regla que liste cuándo usar cada uno (copia la columna "Para qué" de AGENTS.md §2) |
| 3 | Agente `contexto-proyecto` | `agents/contexto-proyecto.md`, A3 | Subagente/modo con el mismo prompt | Skill/comando `contexto-proyecto` que el usuario o la IA ejecuta en el mismo hilo |
| 4 | Guardián de acciones | R0–R13 | Hooks nativos que llamen a los scripts de referencia mediante un **adaptador** (ver Paso 4.3) | Instrucción explícita en las reglas + informe "no controlado" por cada regla |
| 5 | Guardián de git en la IA | R9–R12 | Hook antes de ejecutar comandos de terminal → `git-guard.py` vía adaptador | Hooks de git (H1–H2, ya instalados) cubren ramas, etiquetas, atribución y secretos; push/PR quedan como instrucción |
| 6 | Recordatorio de reglas | A1 | Hook al enviar mensaje → `reglas-udistrital.py` | Las reglas globales (componente 1) ya lo cubren |
| 7 | Contexto del proyecto | A2 | Hook al iniciar sesión/enviar mensaje/tras comandos git → `contexto-proyecto.py hook` | Regla: "al empezar en un repo udistrital, ejecuta `python3 <ruta>/scripts/contexto-proyecto.py estado` y, si falta contexto o hay cambios de otros autores, ejecuta la skill/agente contexto-proyecto" |
| 8 | Hooks de git | H1–H2 | Ya instalados por `instalar.sh` (`core.hooksPath`) | — (no dependen de la IA) |

### Adaptaciones obligatorias dentro de skills y agente

- `${CLAUDE_PLUGIN_ROOT}` → ruta absoluta donde quede este repositorio (o donde copies `scripts/`).
- Prefijo `oas:` (`/oas:commit-oas`, `oas:contexto-proyecto`) → el nombre con el que tu herramienta invoca la skill/agente.
- "herramienta `Skill`" → cómo se invoca una skill en tu herramienta. "herramienta `AskUserQuestion`" → tu mecanismo de preguntas con opciones; si sólo hay texto, pregunta con opciones numeradas, marca la recomendada con `(Recomendado)` y exige que el usuario responda con el texto de la opción para las aprobaciones (AGENTS.md §5).
- "lanza el agente … (subagent_type: …)" → tu mecanismo de subagentes, o ejecutar sus instrucciones en el mismo hilo.
- Menciones a "Claude"/"Claude Code" en reglas operativas → tu herramienta. **No cambies** las reglas que prohíben atribución a IA en commits.

## Paso 3 — Presentar el plan y esperar aprobación

Muestra al usuario:

1. La tabla del Paso 2 completa: componente → mecanismo elegido → **nivel**: `control real` (tu herramienta lo hace cumplir), `instrucción` (depende de que la IA obedezca) o `no portado` (con motivo).
2. Los archivos que crearás o modificarás (con las copias de respaldo).
3. Las reglas R0–R13 que quedarán sin control real, y qué casos de `casos.json` dejarán de cumplirse.

Pregunta con opciones: **Aplicar el plan (Recomendado)** · Ajustar · Cancelar. No escribas nada hasta que elija aplicar.

## Paso 4 — Implementar

### 4.1 Reglas
Escribe la sección del componente 1. Comprueba que tu herramienta la carga (por ejemplo, abriendo una sesión en `<UDISTRITAL>/<algún repo>` y preguntándole qué reglas aplican).

### 4.2 Skills y agente
Convierte cada `SKILL.md` y el agente aplicando las adaptaciones. Conserva las tablas, plantillas y pasos íntegros (son el valor de las skills). Si tu herramienta limita el tamaño, divide en archivos referenciados, sin resumir reglas.

### 4.3 Guardianes por hooks (si tu herramienta tiene hooks)
**Reutiliza los scripts de referencia; no reescribas la lógica.** Escribe un adaptador pequeño (`~/.config/oas-ai-tools/<tu-herramienta>/adaptador.py`) que:

1. Reciba el JSON del hook de tu herramienta.
2. Lo traduzca al formato que esperan los scripts:
   - edición/escritura → `skill-guard.py pre-edit` con `{"tool_name": "Edit"|"Write", "tool_input": {"file_path", "old_string", "new_string"} | {"file_path", "content"}, "cwd", "session_id", "transcript_path"}`
   - lectura → `skill-guard.py pre-read` con `{"tool_input": {"file_path"}}`
   - comando de terminal → `git-guard.py` y `skill-guard.py pre-bash` con `{"tool_input": {"command"}, "cwd", "session_id", "transcript_path"}`
   - fin de turno → `skill-guard.py stop` con `{"cwd", "session_id", "transcript_path", "stop_hook_active"}`
   - mensaje del usuario/inicio de sesión → `reglas-udistrital.py` y `contexto-proyecto.py hook` con `{"cwd", "session_id", "hook_event_name"}`
3. **Historial de sesión**: los scripts leen `transcript_path` como JSONL con líneas `{"message": {"content": [ ... ]}}`, donde los elementos son `{"type": "tool_use", "name": "Skill", "input": {"skill": "<nombre>"}}`, `{"type": "tool_use", "name": "Bash", "id": "<id>", "input": {"command": "..."}}`, `{"type": "tool_result", "tool_use_id": "<id>", "content": "<salida>", "is_error": false}`, y para respuestas del usuario `{"toolUseResult": {"answers": {"<pregunta>": "<opción elegida>"}}, "message": {"content": [{"type": "tool_result", "tool_use_id": "<id>"}]}}`. Si tu herramienta tiene historial con otro formato, el adaptador genera un transcript equivalente en `~/.config/oas-ai-tools/<tu-herramienta>/sesiones/<id>.jsonl`. Si no tiene historial accesible, R2, R3, R6 (aprobación), R7 (aprobaciones), R9 y R13 no pueden ser control real: déjalas como instrucción y repórtalas.
4. Traduzca la respuesta (`allow`/`ask`/`deny`/`block` + razón) a lo que tu herramienta entienda (bloquear, pedir confirmación, mensaje a la IA). Si tu herramienta no tiene "pedir confirmación", usa bloquear con un mensaje que pida al usuario autorizar explícitamente.
5. Defina las variables que los scripts usan: `UDISTRITAL_DIR` (opcional) y **no** defina `CLAUDE_PLUGIN_ROOT` (así los mensajes usan los nombres de skill sin prefijo `oas:`).

### 4.4 Sin hooks
Agrega a las reglas (componente 1) una sección "Controles que debes aplicar tú misma" con R2–R13 redactadas como obligaciones, y la lista de comandos de verificación que puede ejecutar el usuario: `python3 <ruta>/scripts/contexto-proyecto.py estado`, `bash <ruta>/git-hooks/tests/test_git_hooks.sh`.

## Paso 5 — Verificar

1. Hooks de git: `bash git-hooks/tests/test_git_hooks.sh` → todo OK.
2. Si implementaste guardianes con adaptador: escribe un ejecutor equivalente a `scripts/tests/run_casos.py` que alimente **tu adaptador** con los casos de `spec/casos.json` (puedes partir de ese archivo y cambiar sólo la función que arma el JSON y lee la respuesta). Objetivo: todos los casos de las reglas que marcaste como `control real` pasan.
3. Prueba manual mínima en un repo udistrital (sin commitear nada): pedir a tu IA "edita un archivo de un *_crud" y comprobar que exige `crud-oas`; pedir "haz git push" y comprobar que lo rechaza.

## Paso 6 — Informe

Escribe `~/.config/oas-ai-tools/<tu-herramienta>/INFORME-PORTE.md` y muéstralo al usuario:

```markdown
# Informe de porte — oas-ai-tools → <herramienta> <versión>
Fecha: AAAA-MM-DD · Versión de oas-ai-tools: <version de .claude-plugin/plugin.json> · Commit: <git rev-parse --short HEAD>

## Componentes
| # | Componente | Mecanismo | Nivel | Archivos |
|---|---|---|---|---|

## Reglas sin control real
| Regla | Por qué | Cómo queda (instrucción) |
|---|---|---|

## Verificación
- Hooks de git: N/N
- Casos de casos.json por adaptador: N/N (fallan: …)
- Prueba manual: …

## Respaldos creados
## Cómo se usa (para el usuario)
- Invocar una skill: …
- Ver/actualizar contexto: …
## Para actualizar
Cuando el repositorio oas-ai-tools cambie: `git pull` en el clon y volver a pedir "sigue PORTAR.md"; compara con el commit de este informe y aplica sólo las diferencias.
```

## Paso 7 — Cerrar

Explica al usuario en pocas líneas: qué quedó como control real, qué depende de la IA, cómo invocar las skills en su herramienta y dónde está el informe. No hagas commits ni push de nada.
