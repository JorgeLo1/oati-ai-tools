# Changelog

Formato: versión (SemVer, la de `.claude-plugin/plugin.json`) · fecha · cambios.

## 1.2.0 · 2026-10-12

- Nueva skill `code-review-oas`: revisa el PR de un compañero sin descargar sus cambios al repo local (todo con `gh`; sin checkout, fetch, pull ni stash).
  - Entiende la implementación de punta a punta (flujos, contratos con el backend, código eliminado, equivalencia en refactors, variantes paralelas) y la valida contra los repos de los que depende: si un repo involucrado no está local lo clona, y si no tiene contexto lo genera con el agente `contexto-proyecto`. Busca PRs hermanos de la misma issue en otros repos.
  - Mide el PR contra la issue y sus criterios de aceptación (y la especificación si existe en la carpeta local), las reglas de `endpoint-oas`, `crud-oas` y `mid-oas` en modo revisar, el checklist de `seguridad-oas` sobre el diff del PR, las reglas de ramas y commits de `commit-oas`, la disciplina de `AGENTS.md` y las reglas clave del repo.
  - Tono de compañeros: reconoce lo bueno, sólo los bugs con escenario concreto piden ajustes, los detalles de forma se agrupan y son opcionales. Verifica cada hallazgo antes de reportarlo y soporta re-revisión.
  - Nada llega al comentario sin comprobar: filtro de precedentes (diseño ya aprobado en variantes o PRs anteriores), explicaciones del autor y alcance real del escenario; verificación independiente con un subagente que intenta refutar cada observación; repaso frase por frase con evidencia `archivo:línea`. Lo descartado queda en el informe con su motivo.
  - Los comentarios se redactan con el estilo de `doc-issue-oas` calibrado con los comentarios previos del usuario, sin tono de IA.
  - El informe es local (`.claude/docs/revisiones/pr-<n>.md`) con comentarios listos para copiar; nunca publica en GitHub.

## 1.1.0 · 2026-10-09

- Agente `contexto-proyecto`: el contexto se organiza por **dominios funcionales comunes entre repos** (MF, MID y CRUD con los mismos nombres y números; adopta la numeración de un repo hermano que ya tenga contexto), con documentos transversales según el tipo de repo, plantilla fija por dominio con "En otros repos" (enlaces reales MF → MID → CRUD) y "Trampas", tablas generadas por script entre marcadores, índice orientado a tareas y límites de tamaño.
- Nuevo MODO `reorganizar` para llevar un contexto existente a esa estructura sin perder contenido.
- Nuevo `scripts/verificar_contexto.py`: tamaños, enlaces (también entre repos), índice completo, bloques generados y secretos; el agente debe dejarlo en verde.

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
