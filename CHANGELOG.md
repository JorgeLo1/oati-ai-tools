# Changelog

Formato: versión (SemVer, la de `.claude-plugin/plugin.json`) · fecha · cambios.

## 1.0.0 · 2026-10-09

Primera versión compartible.

- Plugin `oas` para Claude Code con marketplace `oas-udistrital`.
- Skills: `planificar-issue` (spec-driven: especificación + plan aprobados por el usuario, ejecución tarea por tarea orquestando las demás skills), `commit-oas`, `endpoint-oas`, `crud-oas`, `mid-oas`, `seguridad-oas`, `documentar-cambios`, `doc-issue-oas`.
- Agente `contexto-proyecto` (modos generar, actualizar, documentar) y aviso automático al faltar contexto o traer cambios de otros autores.
- Guardianes: especificación aprobada antes del código (aprobación validada contra la respuesta del usuario), skill de dominio por tipo de repo, rutas con `endpoint-oas`, commits con `commit-oas` + `seguridad-oas`, escrituras por terminal analizadas, protección de `.env`/lockfiles/configuración, `git-guard` (push/PR, `--no-verify`, atribución a IA en el mensaje).
- Hooks de git universales (`pre-commit`, `commit-msg`): rama GitFlow, etiqueta OAS, atribución a IA y secretos; encadenan el hook propio del repo.
- `AGENTS.md` como fuente única de reglas; `PORTAR.md`, `spec/contratos.md` y `spec/casos.json` para portar a otras IAs.
- `instalar.sh` (verificación, migración desde instalación manual, pruebas) y `desinstalar.sh`.
