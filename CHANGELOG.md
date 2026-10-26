# Changelog

Formato: versión (SemVer, la de `.claude-plugin/plugin.json`) · fecha · cambios.

## 1.5.0 · 2026-10-26

- Pruebas funcionales con varias personas en el mismo módulo (`pruebas-funcionales-oas`, sección "Trabajo en equipo en el mismo módulo"; `AGENTS.md` §8): plan propio por funcionalidad; `e2e/fixtures.ts` compartido (quien lo cambia corre todas las e2e); quien cambia la interfaz actualiza en el mismo PR los escenarios que la usan; antes del PR se corren todos los escenarios del módulo (`--grep @<modulo>`); si falla el escenario de otra persona por su cambio, se le pasa la traza y decide el autor; nombres de rol comunes y sesiones propias. La etiqueta `@<modulo>` es el nombre de la carpeta en `src/app/modules/`.
- Aviso de `contexto-proyecto`: si llegan cambios de otras personas a módulos de un MF con Playwright, sugiere correr sus escenarios (`--grep "@<modulo>"`), sin ejecutarlos.
- `code-review-oas`: revisa que los cambios de interfaz actualicen los escenarios e2e afectados y que los flujos nuevos traigan escenario.
- La evidencia de pruebas en el PR pasa a ser una **recomendación** (`commit-oas` la propone; `code-review-oas` la sugiere sin exigirla). Las pruebas unitarias del `pre-commit` quedan como herramienta de uso local.

## 1.4.1 · 2026-10-26

- Recordatorio `[reglas-udistrital]`: la suite completa va en `/seguridad-oas` y los tests que rompe un cambio son de quien lo hace; `/release-oas` para releases; en MF, `/pruebas-funcionales-oas` antes de cerrar issues con interfaz.
- `commit-oas`: texto del PR con sección **Pruebas** (resultado real de la suite, preexistentes, specs agregados o ajustados, pruebas funcionales). Mientras el pipeline no ejecute las pruebas, es la evidencia del PR; `code-review-oas` la exige como ajuste requerido.
- Caso G20 (escape `OAS_PRUEBAS_OMITIR` desde la IA → bloquear) y contratos A1, A2 y R12 actualizados.

## 1.4.0 · 2026-10-26

- Pruebas compartidas (`AGENTS.md` §8): quien cambia un contrato arregla los tests que rompe; suite completa antes del PR; nunca borrar, saltar ni debilitar un test ajeno; comportamiento nuevo con su test; specs nuevos por caso de uso con datos en `test/fixtures/<modulo>.ts`.
- `git-hooks/oas_pruebas.py`: corre las pruebas relacionadas con los archivos cambiados (Jest con `--findRelatedTests` desde `scripts.test`; `go test` de los paquetes tocados; `ng test` se omite con aviso). Salida 0 pasan, 1 fallan, 2 no se pudo evaluar.
  - `pre-commit`: bloquea si fallan las relacionadas con lo que está en stage; si la suite no arranca, falta `node_modules` o se agota el tiempo, sólo avisa. Escape para personas `OAS_PRUEBAS_OMITIR=1` (bloqueado para la IA en `git-guard`). Nuevos casos en `test_git_hooks.sh`.
  - Aviso de `contexto-proyecto` tras traer commits de otras personas con código: indica correr las relacionadas con lo que llegó y reportar qué falla y de qué autor, sin corregir código ajeno.
- Nueva skill `pruebas-funcionales-oas` sobre la skill oficial `playwright-cli`: Playwright en el repo del MF (`e2e/`, planes versionados, un escenario por archivo etiquetado por módulo), stack local root/MF/MID/CRUD, sesión OIDC por rol guardada tras el login manual (sin credenciales; `.auth/` ignorado), datos marcados y limpiados, evidencias en `.claude/docs/pruebas/` para `doc-issue-oas` y `seguridad-oas`.
- `mid-oas`, `crud-oas`: reglas de equipo para specs y suite completa en la verificación. `seguridad-oas`: suite completa separando lo introducido de lo preexistente. `code-review-oas`: capa 4.6 de pruebas. `planificar-issue`: cada tarea indica su spec y el cierre incluye pruebas funcionales. `release-oas` y `doc-issue-oas`: usan las e2e y su informe.

## 1.3.0 · 2026-10-26

- Precedencia explícita en las skills: manda `udistrital/lineamientos_oas`; la guía del proyecto `udistrital/sisifo_documentacion` (`docs/backend/backend_guide.md`, `utils/sonar`) sólo tapa huecos. Lo que la contradice no se aplica (rama `fix/`, ramas desde `release/*`, `master` sin tag, `X.Y.Z.prod`, plural obligatorio, `DELETE` `204` sin envoltura, paginación `pagina`/`limite`).
- Nueva skill `release-oas`: checklist de release según el lineamiento de despliegues (versión SemVer, `release/X.Y.Z`, Swagger y su conversión a OpenAPI 2.0 para el registro en WSO2, pasos y responsables por ambiente, pruebas, BD), plan de rollback con N y N−1, tag en `master` y limpieza. No despliega ni publica.
- `endpoint-oas`: `409` por conflicto con el estado actual, `202` para tareas asíncronas, `Location` opcional en `201`, aviso de registro en WSO2 con OpenAPI 2.0 para endpoints nuevos.
- `mid-oas`: timeouts en las llamadas a otras APIs, reintentos acotados sólo en lecturas o en operaciones idempotentes, idempotencia en escrituras repetibles y logs con identificador de petición, servicio dependiente y duración.
- `crud-oas`: evidencia con `explain("executionStats")` para índices nuevos y agregaciones costosas.
- `seguridad-oas`: análisis con el SonarQube local de `utils/sonar` (sólo con confirmación y servidor en `127.0.0.1`), exclusiones de `dist`/`coverage`, reporte de cobertura (`lcov.reportPaths`), `.scannerwork/` en `.gitignore` y exportación de issues y hotspots.
- `commit-oas`: aclara que las guías del proyecto no cambian las reglas de ramas, etiquetas y tags.

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
