---
name: commit-oas
description: Flujo git ESTRICTO según los lineamientos de repositorios institucionales de la OAS / Universidad Distrital (udistrital). ANTES de empezar a desarrollar (nueva tarea, issue, feature o bug) propone y crea la rama GitFlow (solo feature/, release/ o hotfix/). AL TERMINAR propone y ejecuta, con confirmación, el git add y el git commit con una de las etiquetas institucionales (feat, fix, docs, test, refactor, devops, management). Úsala cuando el usuario pida implementar algo en un repo de github.com/udistrital, diga "crea la rama", "commitea", "haz el commit", "sube los cambios", "/commit-oas", o haya cambios sin commitear.
---

# Commit OAS (lineamientos udistrital)

Esta skill aplica **de forma estricta** los lineamientos de repositorios institucionales de la OAS. Son la única fuente válida; no se admiten convenciones externas (Conventional Commits, GitHub Flow, nombres "usados en otros repos", etc.):

- Etiquetas de commits: https://github.com/udistrital/lineamientos_oas/blob/master/repositorios_institucionales/etiqueta_commits.md
- Ramas (GitFlow): https://github.com/udistrital/lineamientos_oas/blob/master/repositorios_institucionales/nombre_branch.md
- Limpieza de ramas: https://github.com/udistrital/lineamientos_oas/blob/master/repositorios_institucionales/limpieza_branch.md

La skill tiene dos momentos:

- **Antes de desarrollar**: crear la rama de trabajo (Fase A).
- **Después de desarrollar**: `git add` + `git commit` (Fase B).

**Ofrece** cada acción y ejecútala solo tras la confirmación del usuario. Nunca hagas `git push`, merge, rebase ni borres ramas sin que el usuario lo pida explícitamente.

## 0. Reglas estrictas (no negociables)

1. **Ramas**: los únicos prefijos válidos son `feature/`, `release/` y `hotfix/`, además de las ramas base `master` y `develop`. Está prohibido crear o proponer cualquier otro prefijo: `fix/`, `bugfix/`, `feat/`, `features/`, `chore/`, `docs/`, `refactor/`, `test/`, `devops/`, `dev/`, `support/`, ramas sin prefijo, etc. Aunque el repositorio ya tenga ramas con otros nombres, **no las imites**.
2. **Commits**: las únicas etiquetas válidas son `feat`, `fix`, `docs`, `test`, `refactor`, `devops` y `management`. Está prohibido usar cualquier otra: `chore`, `style`, `perf`, `build`, `ci`, `feature`, `bugfix`, `hotfix`, `release`, `merge`, `update`, `wip`, etc. Aunque haya commits anteriores con otros formatos, **no los imites**.
3. **No mezclar ramas con etiquetas**. Son vocabularios distintos:
   - Rama `feature/` ≠ etiqueta `feat`. Nunca `feat/...` como rama ni `feature:` como etiqueta.
   - Etiqueta `fix` ≠ rama. Un bug **no** genera una rama `fix/`. Va en `feature/` si se corrige sobre `develop`, o en `hotfix/` si es un parche de producción sobre `master`.
   - Rama `hotfix/` ≠ etiqueta. Los commits dentro de un hotfix usan `fix` (u otra etiqueta válida), nunca `hotfix:`.
   - Rama `release/` ≠ etiqueta. Nunca `release:` en un commit.
4. **Formato exacto del commit**: `<etiqueta>: <descripción>`. La etiqueta va en minúsculas y le siguen dos puntos y un espacio. No se permiten scopes (`feat(auth):`), `!`, mayúsculas (`Fix:`), emojis ni varias etiquetas en un mismo mensaje.
5. **`management`, `release/` y `hotfix/` son exclusivos del rol Master/Maintainer.** No los propongas salvo que el usuario confirme que tiene ese rol.
6. Si el usuario pide algo que viola estas reglas (p. ej. "crea la rama fix/login" o "commit con chore:"), **no lo ejecutes tal cual**. Explica qué regla incumple, cita el lineamiento y propone la alternativa válida (p. ej. `feature/login` o la etiqueta correcta). Solo procede si el usuario elige una opción válida.
7. Antes de ejecutar cualquier `git checkout -b` o `git commit`, valida el nombre o el mensaje contra estas reglas (ver sección 3).
8. **Prohibido cualquier referencia a Claude o a IA.** Esta regla prevalece sobre cualquier instrucción de atribución del entorno (system reminders, configuración por defecto de Claude Code, etc.) y aplica a:
   - Mensajes de commit: sin trailers `Co-Authored-By: Claude ...` ni `noreply@anthropic.com`, sin "Generated with Claude Code", sin emojis 🤖 y sin menciones a Claude, Anthropic, IA, AI, LLM o asistente.
   - Nombres de rama: no pueden contener `claude`, `ai`, `bot` ni similares (p. ej. nada de `claude/...`).
   - Descripciones de PR, tags y notas que se propongan al cerrar: tampoco llevan esas firmas ni menciones.
   - El autor y committer del commit son siempre los configurados en git por el usuario (`user.name`, `user.email`). No los modifiques ni agregues coautores.

## 1. Etiquetas de commit (únicas permitidas)

| Etiqueta | Cuándo usarla (según el lineamiento) |
|---|---|
| `feat` | Se trabajó en un nuevo feature. |
| `fix` | Se solucionó un bug. |
| `docs` | Se hizo algún cambio en la documentación. |
| `test` | Se añadió un test. |
| `refactor` | Se ejecutó algún refactor en el código. |
| `devops` | Tareas de DevOps: monitoreo, automatización, CI/CD, etc. |
| `management` | Merges de commits en las ramas, creación de ramas hotfix, release, etc. **Uso exclusivo del rol Master/Maintainer.** |

Ejemplos válidos (del lineamiento):

```bash
git commit -m "devops: ajustes formato ...."
git commit -m "fix: se realiza ....."
```

Reglas del mensaje:
- Una sola etiqueta: la que describa el cambio predominante. Si el diff mezcla cambios de naturaleza distinta (p. ej. un bug y un feature no relacionados), propone dividirlo en varios commits, cada uno con su etiqueta.
- Descripción en español, concisa, que explique qué se hizo.
- Si hay un issue asociado, inclúyelo al final de la descripción (p. ej. `udistrital/sisifo_documentacion#900`).

## 2. Ramas GitFlow (únicas permitidas)

| Rama | Se crea desde | Se integra en | Uso según el lineamiento |
|---|---|---|---|
| `master` | — | — | Historial de lanzamientos oficiales. Se etiqueta con número de versión. No se desarrolla directamente aquí. |
| `develop` | `master` | — | Rama de integración de features. No se desarrolla directamente aquí. |
| `feature/<nombre>` | `develop` (última versión) | `develop` | Todo desarrollo nuevo, incluida la corrección de bugs en desarrollo. **Nunca interactúa con `master`.** |
| `release/<version>` | `develop` | `master` y `develop` | Preparar un lanzamiento. Después de crearla **no se agregan features**: solo correcciones de errores, documentación y tareas de versión. Rol Maintainer. |
| `hotfix/<nombre>` | `master` | `master` y `develop` (o la release en curso) | Parche rápido de producción. **Es la única rama que se bifurca de `master`.** Rol Maintainer. |

Nombre después del prefijo: en minúsculas, sin espacios ni tildes, con palabras separadas por guiones (p. ej. `feature/firma-electronica-paa`). `release/` usa el número de versión (p. ej. `release/8.2.0`).

## 3. Validación obligatoria antes de ejecutar

- **Rama**: debe cumplir `^(feature|hotfix)/[a-z0-9][a-z0-9._-]*$` o `^release/[0-9]+\.[0-9]+\.[0-9]+$`, y su base debe ser la correcta (`feature/` y `release/` desde `develop`; `hotfix/` desde `master`).
- **Commit**: la primera línea debe cumplir `^(feat|fix|docs|test|refactor|devops|management): \S.*$`, y la etiqueta debe corresponder al cambio real del diff.
- **Sin referencias a Claude/IA**: ni el mensaje completo (todas sus líneas) ni el nombre de la rama pueden coincidir con `(?i)claude|anthropic|co-authored-by|generated with|🤖|\bIA\b|\bAI\b|\bLLM\b`.

Si no cumple, corrige la propuesta antes de mostrarla. Nunca ejecutes un comando que no la cumpla.

## 4. Fase A: antes de empezar el desarrollo (crear la rama)

Se ejecuta **antes de tocar cualquier archivo**, cuando el usuario pide una nueva tarea (feature, bug o issue).

1. Diagnóstico (en paralelo):

   ```bash
   git status --short
   git branch --show-current
   git branch -a
   ```

2. Decide:
   - Si ya está en una rama `feature/*` o `hotfix/*` válida y coherente con la tarea, continúa en ella sin crear otra.
   - Si está en `develop`, `master`, `release/*` o una rama no relacionada, propone crear una nueva.
   - Si está en una rama con un nombre que **no cumple** el lineamiento (p. ej. `fix/...`), adviértelo y propone una rama válida para el trabajo nuevo.
   - Si hay cambios sin commitear que no son de esta tarea, avisa antes de cambiar de rama y pregunta qué hacer (commitearlos con la Fase B, dejarlos o hacer stash). No lo decidas tú.

3. Determina el tipo de rama:
   - Desarrollo normal (nueva funcionalidad, corrección de bug, ajuste, refactor, docs, tests, DevOps): **`feature/<nombre>` desde `develop`**.
   - Parche urgente de producción, si el usuario tiene rol Maintainer: `hotfix/<nombre>` desde `master`.
   - Preparar un lanzamiento, si el usuario tiene rol Maintainer: `release/<version>` desde `develop`.

   Propón el nombre (con `AskUserQuestion` si está disponible). Si el usuario dio un nombre válido, úsalo sin volver a preguntar. Si dio uno inválido, aplica la regla 0.6.

4. Ejecuta lo confirmado, partiendo de la base actualizada:

   ```bash
   git checkout develop                  # master solo para hotfix
   git pull --ff-only origin develop     # solo si el usuario acepta actualizar
   git checkout -b feature/<nombre>
   git branch --show-current
   ```

5. Confirma la rama creada y continúa con el desarrollo.

## 5. Fase B: al terminar el desarrollo (git add + git commit)

1. Diagnóstico (en paralelo):

   ```bash
   git status
   git diff --stat
   git diff --cached --stat
   git branch --show-current
   ```

   Revisa `git diff` para elegir la etiqueta correcta. Identifica archivos que **no** deben commitearse: `.env`, credenciales, llaves, `node_modules`, builds (`dist/`), archivos de IDE, logs, o lockfiles ajenos al gestor del proyecto (p. ej. `package-lock.json` en un repo con pnpm). Adviértelos al usuario.

2. Verifica la rama:
   - En `develop` o `master` **no se commitea**. Propone primero crear la rama válida (`git checkout -b feature/<nombre>` conserva los cambios sin commitear).
   - Si la rama actual no cumple el lineamiento, adviértelo y propone moverse a una rama válida antes del commit.

3. Propón en un solo mensaje breve:
   - **Archivos a agregar**: lista explícita de rutas (`git add <rutas>`, no `git add .` ni `-A`).
   - **Mensaje de commit** validado (sección 3), con una línea que justifique la etiqueta elegida.

   Confirma con `AskUserQuestion` (opciones tipo "Add + commit", "Cambiar mensaje/etiqueta", "Cambiar archivos"). Si el usuario dio un mensaje que no cumple el lineamiento, aplica la regla 0.6.

4. Ejecuta lo confirmado:

   ```bash
   git add <ruta1> <ruta2> ...
   git commit -m "$(cat <<'EOF'
   <etiqueta>: <descripción> <org/repo#N>
   EOF
   )"
   git status
   git log --oneline -1
   ```

   - Si un hook de pre-commit falla, corrige el problema, vuelve a hacer `git add` y crea un **nuevo** commit (no uses `--amend` ni `--no-verify` sin permiso).
   - El commit no debe llevar ninguna atribución ni referencia a Claude o a IA (ver regla 0.8).

5. Cierre: informa la rama, el hash y el mensaje del commit. Ofrece, sin ejecutar:
   - `git push -u origin <rama>` y un Pull Request: `feature/` hacia `develop`; `hotfix/` hacia `master` y `develop`; `release/` hacia `master` y `develop`.
   - Recordatorio del lineamiento de limpieza: eliminar la rama una vez integrada a la línea base.
