---
name: pruebas-funcionales-oas
description: Pruebas funcionales y e2e de los MF udistrital (Angular + single-spa) con Playwright sobre la skill oficial playwright-cli — prepara Playwright en el repo del MF (config, carpeta e2e/, planes de prueba versionados), levanta y verifica el stack local (root, MF, MID, CRUD), maneja la sesión del login institucional OIDC por rol sin guardar credenciales, convierte los criterios de aceptación de la especificación en escenarios (un escenario por archivo, etiquetados por módulo), cuida los datos de prueba, corre y repara los specs y deja evidencias para doc-issue-oas y seguridad-oas. Úsala cuando el usuario diga "/pruebas-funcionales-oas", "prueba el flujo", "pruebas funcionales", "pruebas e2e", "valida en el navegador", "genera los tests de Playwright", "toma las capturas de la issue", o al cerrar una issue con interfaz.
---

# Pruebas funcionales OAS (Playwright en los MF)

La mecánica de Playwright (snapshot, refs, generación de código, plan → generar → reparar, depuración con `--debug=cli`) es de la skill **`playwright-cli`**: cárgala y sigue su `references/test-generation.md` y `references/playwright-tests.md`. Esta skill agrega lo propio de SISIFO: dónde viven los specs, el stack local, el login institucional, los datos y las evidencias.

Reglas de equipo para pruebas en módulos compartidos: `AGENTS.md` §8.

## Paso 0 — Alcance y prerrequisitos

1. Issue y especificación (`<UDISTRITAL>/.claude/specs/<repo>-<n>.md`): de su tabla "Criterios de aceptación → verificación" salen los escenarios. Sin especificación, pide los criterios al usuario.
2. MF afectados (por la especificación o el diff) y su módulo (`programacion`, `planeacion`, `plan-mejoramiento`, …): definen la etiqueta `@<modulo>`.
3. Herramienta: `playwright-cli --version`. Si no está: `npm install -g @playwright/cli@latest` (con confirmación).
4. Navegador visible en WSL: el login manual requiere ventana (WSLg). Si `playwright-cli open --headed` no abre ventana, dilo y pide al usuario que lo resuelva; no intentes hacer el login sin ventana.

## Paso 1 — Playwright en el repo del MF (sólo la primera vez)

Si el MF no tiene `playwright.config.ts`, propón (con confirmación y en la rama de la issue, como una tarea más del plan):

- Dependencia con el gestor del repo según el lockfile: `pnpm add -D @playwright/test` o `npm i -D @playwright/test` (nunca edites el lockfile a mano) y `npx playwright install chromium`.
- Script `"e2e": "playwright test"` en `package.json`.
- Estructura:
  ```
  playwright.config.ts
  e2e/
    fixtures.ts                 # page con navegación inicial y helpers compartidos del MF
    seed.spec.ts                # punto de partida para planear y generar (playwright-cli)
    specs/<funcionalidad>.plan.md   # planes de prueba (versionados)
    <modulo>/<escenario>.spec.ts    # un escenario por archivo
    .auth/                      # sesiones guardadas: NUNCA se versiona
  ```
- `.gitignore`: `e2e/.auth/`, `playwright-report/`, `test-results/`, `.playwright-cli/`.
- Que el runner unitario no tome `e2e/` (`testPathIgnorePatterns` en Jest; `exclude` en el `tsconfig` de la app y de Karma) y que Sonar lo trate como pruebas (`sonar.tests` o `sonar.exclusions`).
- `playwright.config.ts`, a partir de esta base:
  ```ts
  import { defineConfig } from '@playwright/test';

  export default defineConfig({
    testDir: './e2e',
    fullyParallel: false,          // comparten backend y datos locales
    retries: 0,
    reporter: [['html', { open: 'never' }], ['list']],
    use: {
      baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:4200',   // el root compone los MF
      trace: 'retain-on-failure',
      screenshot: 'only-on-failure',
    },
    projects: [
      // un proyecto por usuario de prueba / rol; la sesión la guarda el usuario (Paso 3)
      { name: 'jefe-oci', use: { storageState: 'e2e/.auth/jefe-oci.json' } },
      { name: 'auditado', use: { storageState: 'e2e/.auth/auditado.json' } },
    ],
  });
  ```
  Los nombres de rol salen de la configuración real del MF (`rol.service.ts`, `environment`); no los inventes.

## Paso 2 — Stack local

Los MF se prueban dentro del **root** (`auditoria_plan_mejoramiento_root_mf`, puerto `4200`), que carga los MF locales según `parcels` de su `environment` (p. ej. `plan_anual_auditoria_mf` en `4203`, `usuario_rol_mf` en `4202`) y `core-mf` remoto.

1. Lee los puertos reales en `environment.ts` del root y en los `package.json` (`serve:single-spa:<mf>`), y los puertos de MID/CRUD en su `.env`/README (sin mostrar valores sensibles).
2. Comprueba qué está arriba (`curl -s -o /dev/null -w '%{http_code}' <url>`). Lo que falte, pídeselo al usuario o levántalo en segundo plano con su confirmación (`pnpm start`, `pnpm run serve:single-spa:<mf>`, `pnpm start:dev` del MID/CRUD).
3. El MF debe apuntar al MID/CRUD **locales** (`environment` de desarrollo). Si apunta a pruebas compartido, avisa: aplica la regla de datos del Paso 5.

## Paso 3 — Sesión del login institucional (OIDC)

El login es OIDC implícito contra `autenticacion.portaloas.udistrital.edu.co`; el `core-mf` guarda `access_token`, `id_token`, `expires_at`, `menu` y `persona_id` en `localStorage` del origen `localhost:4200`.

1. Por cada rol que necesiten los escenarios, **el usuario** inicia sesión a mano con su usuario de prueba:
   ```bash
   playwright-cli open --headed http://localhost:4200
   # el usuario completa el login en la ventana; luego:
   playwright-cli state-save e2e/.auth/<rol>.json
   playwright-cli close
   ```
2. **Nunca** escribas, pidas ni guardes usuario o contraseña (ni en archivos, ni en variables, ni con `fill`). El login lo teclea la persona.
3. `e2e/.auth/*.json` contiene tokens: no lo leas completo, no lo pegues en el chat, no lo commitees (verifica `git check-ignore e2e/.auth/<rol>.json`).
4. Los tokens caducan (`expires_at`). Si un test termina en la página de autenticación, la sesión venció: pide al usuario repetir el paso 1; no lo trates como fallo del MF.
5. No alteres `menu`, roles ni tokens en `localStorage` para simular otro rol: eso no prueba la aplicación y salta el control de acceso. Cada rol, su usuario real de prueba.

## Paso 4 — Plan y specs

1. **Plan versionado** en `e2e/specs/<funcionalidad>.plan.md` con el formato de `playwright-cli` (`references/test-generation.md` §1.4), una sección por criterio de aceptación, indicando en cada escenario el **rol** (proyecto) y la **etiqueta** del módulo. Cubre camino feliz, validaciones, vacíos y permisos por rol (un rol que no debe ver o hacer algo).
2. **Generar** cada escenario con el flujo de `playwright-cli` (seed → `--debug=cli` → `attach` → acciones → aserciones), de a uno y cerrando la sesión entre escenarios:
   ```bash
   PLAYWRIGHT_HTML_OPEN=never npx playwright test e2e/seed.spec.ts --project=<rol> --debug=cli   # en segundo plano
   playwright-cli attach tw-XXXX
   ```
3. Specs: `e2e/<modulo>/<escenario>.spec.ts`, **un escenario por archivo**, con cabecera `// spec: e2e/specs/<funcionalidad>.plan.md` y etiquetas:
   ```ts
   test('<escenario>', { tag: ['@plan-mejoramiento', '@auditado'] }, async ({ page }) => { … });
   ```
4. Locators por rol y nombre accesible (`getByRole`, `getByLabel`). Si un control no tiene nombre accesible, no inventes selectores CSS frágiles: propón agregar `aria-label` o `data-testid` en el componente como cambio del MF, dentro del alcance aprobado de la issue.
5. Nada de `waitForTimeout` ni `networkidle`: espera por lo observable (`toBeVisible`, `toHaveURL`, la respuesta del MID con `page.waitForResponse`).

## Paso 5 — Datos de prueba

- Se prueba contra el **CRUD local**. Escribir en un ambiente compartido (pruebas, producción) sólo con confirmación explícita del usuario para ese escenario; contra producción, sólo lectura.
- Lo que crea un test lleva un marcador único (`E2E-<AAAAMMDD-HHmm>` en un campo de texto) y se limpia al final (borrado lógico vía API del CRUD local en un `afterEach` o fixture). Si no se puede limpiar, dilo en el informe.
- Los escenarios no dependen del orden ni de datos creados por otro escenario: cada uno prepara lo suyo o parte de datos semilla documentados en el plan.

## Paso 6 — Ejecutar y reparar

```bash
PLAYWRIGHT_HTML_OPEN=never npx playwright test --grep @<modulo>        # por issue: los flujos tocados
PLAYWRIGHT_HTML_OPEN=never npx playwright test                         # completo: antes de un release
```

- Fallos: flujo de reparación de `playwright-cli` (`references/test-generation.md` §3), de a uno.
- Si el MF no hace lo que dice el criterio: **para y pregunta** si es un bug o si el criterio cambió (no ajustes el test para que pase).
- Specs e2e de otras personas que rompa tu cambio de interfaz: si el cambio es intencional, actualízalos y dilo; si no, es una regresión tuya (`AGENTS.md` §8). Nunca `test.skip`/`test.fixme` sin decisión del usuario.

## Paso 7 — Evidencias e informe

- En cada escenario que verifica un criterio, adjunta la captura del resultado: `await testInfo.attach('<criterio>', { body: await page.screenshot(), contentType: 'image/png' })`. Quedan en el reporte HTML y en `test-results/` (no versionados).
- Escribe el informe en el chat y en `.claude/docs/pruebas/<rama-sin-prefijo>.md` (local, no versionado; crea la carpeta si no existe):
  ```markdown
  # Pruebas funcionales — <repo> · <rama> · <AAAA-MM-DD>
  Stack: root <url> · MF <url> · MID <url> · CRUD <url> · Roles: <lista>

  | Criterio | Escenario (archivo) | Rol | Resultado | Evidencia |
  |---|---|---|---|---|

  ## Fallos y decisiones
  ## Datos creados y limpieza
  ## Pendientes (sesión vencida, criterios no automatizables, por confirmar)
  ```
- Ese informe lo usan `/doc-issue-oas` (sección "Pruebas realizadas") y `/seguridad-oas` (ítem "Pruebas funcionales realizadas").

## Pruebas de API sin interfaz

Para criterios que sólo tocan el MID o el CRUD, prueba el endpoint local con `curl` (o el `request` de Playwright) desde lo que documenta el Swagger: status esperado, envoltura `{ Success, Status, Message, Data }`, caso vacío (`200` con `Data: []`), errores (`400`, `404`, `409`). Registra comando y respuesta resumida en el mismo informe, sin tokens ni datos personales.

No hagas commits: al terminar sugiere `/commit-oas` con los archivos de `e2e/` (planes, specs, fixtures), `playwright.config.ts`, `package.json` y el lockfile actualizado por el gestor. Nunca `e2e/.auth/`.
