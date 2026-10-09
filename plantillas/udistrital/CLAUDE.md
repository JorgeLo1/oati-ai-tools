# Reglas generales — repositorios udistrital (Claude Code)

@AGENTS.md

## Específico de Claude Code

- Las herramientas están instaladas como el plugin `oas`: las skills se invocan como `/oas:<skill>` (herramienta `Skill` con `oas:<skill>`) y el agente como `oas:contexto-proyecto`.
- Los hooks del plugin hacen cumplir estas reglas:
  - `[reglas-udistrital]` recuerda en cada mensaje qué skills aplican al repo.
  - `[contexto-proyecto]` avisa cuando falta el contexto o se trajeron cambios: lanza el agente como indica.
  - `[skill-guard]` bloquea editar código sin especificación aprobada o sin la skill del dominio, commits sin `/oas:commit-oas` o `/oas:seguridad-oas`, y edición de `.env`/lockfiles; pide confirmación para tocar la configuración de las herramientas.
  - `git-guard` bloquea `git push`, `gh pr create`, `--no-verify` y la atribución a IA; pide confirmación para commit, pull, rebase y reset --hard.
- Las aprobaciones de especificaciones se piden con `AskUserQuestion` (el guardián valida la respuesta).
