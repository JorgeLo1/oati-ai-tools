# Changelog

Formato: versión (SemVer, la de `.claude-plugin/plugin.json`) · fecha · cambios.

## 1.0.2 · 2026-10-09

- `instalar.sh --migrar-desde-manual`: deja sustitutos vacíos (`oas-shim`) en `~/.claude/scripts` para las sesiones de Claude Code abiertas antes de migrar, que siguen llamando a los hooks anteriores (sin ellos, el hook fallaba y podía bloquear la sesión). Los sustitutos no cuentan como instalación manual en ejecuciones posteriores.

## 1.0.1 · 2026-10-09

- Guardián (R13): el aviso de cerrar con `documentar-cambios` sólo cuenta commits hechos en repos udistrital. El repo de cada commit se determina por el directorio donde se ejecutó el comando, sus `cd` y `git -C`. Antes, un commit en un repo ajeno disparaba el aviso si la sesión estaba abierta en la carpeta udistrital.
- Casos F06–F08 en `spec/casos.json`; el ejecutor de casos acepta el directorio de cada comando de la sesión.

## 1.0.0 · 2026-10-09

Primera versión compartible.

- Plugin `oas` para Claude Code con marketplace `oas-udistrital`.
- Skills: `planificar-issue` (spec-driven: especificación + plan aprobados por el usuario, ejecución tarea por tarea orquestando las demás skills), `commit-oas`, `endpoint-oas`, `crud-oas`, `mid-oas`, `seguridad-oas`, `documentar-cambios`, `doc-issue-oas`.
- Agente `contexto-proyecto` (modos generar, actualizar, documentar) y aviso automático al faltar contexto o traer cambios de otros autores.
- Guardianes: especificación aprobada antes del código (aprobación validada contra la respuesta del usuario), skill de dominio por tipo de repo, rutas con `endpoint-oas`, commits con `commit-oas` + `seguridad-oas`, escrituras por terminal analizadas, protección de `.env`/lockfiles/configuración, `git-guard` (push/PR, `--no-verify`, atribución a IA en el mensaje).
- Hooks de git universales (`pre-commit`, `commit-msg`): rama GitFlow, etiqueta OAS, atribución a IA y secretos; encadenan el hook propio del repo.
- `AGENTS.md` como fuente única de reglas; `PORTAR.md`, `spec/contratos.md` y `spec/casos.json` para portar a otras IAs.
- `instalar.sh` (verificación, migración desde instalación manual, pruebas) y `desinstalar.sh`.
