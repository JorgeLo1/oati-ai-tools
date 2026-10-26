---
name: pruebas-funcionales-oas
description: Pruebas funcionales y e2e de los MF udistrital (Angular + single-spa) con Playwright sobre la skill oficial playwright-cli — prepara Playwright en el repo del MF (config, carpeta e2e/, planes de prueba versionados), levanta y verifica el stack local (root, MF, MID, CRUD), hace el login institucional OIDC por rol automáticamente con usuarios de prueba dedicados desde variables de entorno (.env.e2e local o secrets de Drone, sin que la IA lea sus valores; login manual como alternativa), convierte los criterios de aceptación de la especificación en escenarios (un escenario por archivo, etiquetados por módulo), cuida los datos de prueba, corre y repara los specs, separa escenarios @lectura/@escritura para correr en el ambiente de pruebas (funcionamiento y, cuando se autorice, Drone), escribe la guía e2e/README.md y deja evidencias para doc-issue-oas y seguridad-oas. Úsala cuando el usuario diga "/pruebas-funcionales-oas", "prueba el flujo", "pruebas funcionales", "pruebas e2e", "valida en el navegador", "genera los tests de Playwright", "toma las capturas de la issue", o al cerrar una issue con interfaz.
---

# Pruebas funcionales OAS (Playwright en los MF)

La mecánica de Playwright (snapshot, refs, generación de código, plan → generar → reparar, depuración con `--debug=cli`) es de la skill **`playwright-cli`**: cárgala y sigue su `references/test-generation.md` y `references/playwright-tests.md`. Esta skill agrega lo propio de SISIFO: dónde viven los specs, el stack local, el login institucional, los datos y las evidencias.

Reglas de equipo para pruebas en módulos compartidos: `AGENTS.md` §8.

## Paso 0 — Alcance y prerrequisitos

1. Issue y especificación (`<UDISTRITAL>/.claude/specs/<repo>-<n>.md`): de su tabla "Criterios de aceptación → verificación" salen los escenarios. Sin especificación, pide los criterios al usuario.
2. MF afectados (por la especificación o el diff) y su módulo: la etiqueta `@<modulo>` y la carpeta `e2e/<modulo>/` usan el **nombre de la carpeta** del módulo en `src/app/modules/` (p. ej. `@programacion`), para que el aviso tras un pull pueda sugerir los escenarios correctos.
3. Herramienta: `playwright-cli --version`. Si no está: `npm install -g @playwright/cli@latest` (con confirmación).
4. Usuarios de prueba: comprueba que exista `.env.e2e` con los nombres de los roles que necesitan los escenarios (`grep -oE '^E2E_[A-Z_]+=' .env.e2e`, sin ver valores). Si falta un rol, usa el login manual del Paso 3, que requiere ventana (WSLg en WSL): si `playwright-cli open --headed` no abre ventana, dilo y pide al usuario que lo resuelva.

## Paso 1 — Playwright en el repo del MF (sólo la primera vez)

Si el MF no tiene `playwright.config.ts`, propón (con confirmación y en la rama de la issue, como una tarea más del plan):

- Dependencia con el gestor del repo según el lockfile: `pnpm add -D @playwright/test` o `npm i -D @playwright/test` (nunca edites el lockfile a mano) y `npx playwright install chromium`.
- Script `"e2e": "playwright test"` en `package.json`.
- Estructura:
  ```
  playwright.config.ts
  e2e/
    global-setup.ts             # login automático por rol con las variables E2E_* (Paso 3)
    fixtures.ts                 # page con navegación inicial y helpers compartidos del MF
    seed.spec.ts                # punto de partida para planear y generar (playwright-cli)
    specs/<funcionalidad>.plan.md   # planes de prueba (versionados)
    <modulo>/<escenario>.spec.ts    # un escenario por archivo
    README.md                   # guía para quien no desarrolla (funcionamiento): Paso 8
    .auth/                      # sesiones guardadas: NUNCA se versiona
  .env.e2e                      # usuarios de prueba por rol: NUNCA se versiona (lo crea el usuario)
  .env.e2e.example              # sólo los nombres de las variables: se versiona
  ```
- `.gitignore`: `.env.e2e`, `e2e/.auth/`, `playwright-report/`, `test-results/`, `.playwright-cli/`.
- **Convención común a todos los MF** (mismos nombres en cada repo, en el `.env.e2e` local y en los secrets de Drone):
  ```bash
  # .env.e2e.example — usuarios de prueba DEDICADOS del ambiente de pruebas (nunca personales ni de producción)
  E2E_BASE_URL=http://localhost:4200
  E2E_<ROL>_USER=
  E2E_<ROL>_PASS=
  # p. ej. E2E_JEFE_OCI_USER / E2E_JEFE_OCI_PASS, E2E_AUDITOR_*, E2E_AUDITADO_*
  ```
  El `<ROL>` en mayúsculas con `_` corresponde al nombre del proyecto en minúsculas con `-` (`E2E_JEFE_OCI_*` ↔ proyecto `jefe-oci`). El `.env.e2e` lo crea y llena **el usuario** (los guardianes no dejan a la IA editarlo); si existía en otra ruta (p. ej. `.claude/.env`), pídele que lo mueva.
- Que el runner unitario no tome `e2e/` (`testPathIgnorePatterns` en Jest; `exclude` en el `tsconfig` de la app y de Karma) y que Sonar lo trate como pruebas (`sonar.tests` o `sonar.exclusions`).
- `playwright.config.ts`, a partir de esta base:
  ```ts
  import { defineConfig } from '@playwright/test';

  // Local: lee .env.e2e si existe (Node >= 20.12). En Drone las variables llegan como secrets.
  try { process.loadEnvFile('.env.e2e'); } catch { /* sin archivo: se usan las variables del entorno */ }

  export const ROLES = ['jefe-oci', 'auditor', 'auditado'];   // los del MF real

  export default defineConfig({
    testDir: './e2e',
    globalSetup: './e2e/global-setup.ts',
    fullyParallel: false,          // comparten backend y datos
    retries: 0,
    reporter: [['html', { open: 'never' }], ['list']],
    use: {
      baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:4200',   // el root compone los MF
      trace: 'retain-on-failure',
      screenshot: 'only-on-failure',
    },
    projects: ROLES.map((rol) => ({ name: rol, use: { storageState: `e2e/.auth/${rol}.json` } })),
  });
  ```
  Los nombres de rol salen de la configuración real del MF (`rol.service.ts`, `environment`); no los inventes. Si el Node del repo es menor a 20.12, usa `dotenv` como dependencia de desarrollo (con confirmación).

## Paso 2 — Stack local

Los MF se prueban dentro del **root** (`auditoria_plan_mejoramiento_root_mf`, puerto `4200`), que carga los MF locales según `parcels` de su `environment` (p. ej. `plan_anual_auditoria_mf` en `4203`, `usuario_rol_mf` en `4202`) y `core-mf` remoto.

1. Lee los puertos reales en `environment.ts` del root y en los `package.json` (`serve:single-spa:<mf>`), y los puertos de MID/CRUD en su `.env`/README (sin mostrar valores sensibles).
2. Comprueba qué está arriba (`curl -s -o /dev/null -w '%{http_code}' <url>`). Lo que falte, pídeselo al usuario o levántalo en segundo plano con su confirmación (`pnpm start`, `pnpm run serve:single-spa:<mf>`, `pnpm start:dev` del MID/CRUD).
3. El MF debe apuntar al MID/CRUD **locales** (`environment` de desarrollo). Si apunta a pruebas compartido, avisa: aplica la regla de datos del Paso 5.

## Paso 3 — Sesión del login institucional (OIDC)

El login es OIDC implícito contra `autenticacion.portaloas.udistrital.edu.co`; el `core-mf` guarda `access_token`, `id_token`, `expires_at`, `menu` y `persona_id` en `localStorage` del origen `localhost:4200`.

**Login automático por rol (preferido)** — lo hace `e2e/global-setup.ts` una vez al inicio de cada corrida, con los usuarios de prueba dedicados de `E2E_<ROL>_USER`/`E2E_<ROL>_PASS`, y guarda la sesión en `e2e/.auth/<rol>.json` para que la reutilicen los escenarios:

```ts
import { chromium, type FullConfig } from '@playwright/test';
import { ROLES } from '../playwright.config';

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0].use.baseURL!;
  for (const rol of ROLES) {
    const pref = `E2E_${rol.toUpperCase().replace(/-/g, '_')}`;
    const usuario = process.env[`${pref}_USER`];
    const clave = process.env[`${pref}_PASS`];
    if (!usuario || !clave) { console.warn(`[e2e] ${pref}_USER/_PASS sin definir: se omite el rol ${rol}`); continue; }
    const browser = await chromium.launch();
    const page = await browser.newPage();           // sin trace ni video: grabarían la contraseña
    await page.goto(baseURL);
    await page.waitForURL(/autenticacion\.portaloas\.udistrital\.edu\.co/);
    // Selectores del formulario de WSO2: verifícalos con `playwright-cli snapshot` antes de fijarlos.
    await page.getByLabel(/usuario|username/i).fill(usuario);
    await page.getByLabel(/contraseña|password/i).fill(clave);
    await page.getByRole('button', { name: /continuar|ingresar|sign in|continue/i }).click();
    await page.waitForURL((url) => url.href.startsWith(baseURL));
    await page.waitForFunction(() => !!localStorage.getItem('id_token'));
    await page.context().storageState({ path: `e2e/.auth/${rol}.json` });
    await browser.close();
  }
}
```

Reglas:
1. **Los valores de `.env.e2e` nunca se leen, muestran ni copian** (ni en el chat, ni en logs, ni en el informe). Para comprobar que están, sólo los nombres: `grep -oE '^E2E_[A-Z_]+=' .env.e2e`. Nunca los pases por `playwright-cli fill` ni los escribas en un spec.
2. Si el login falla, **no reintentes en bucle**: WSO2 puede bloquear la cuenta o pedir captcha tras varios intentos. Detén la corrida y pide al usuario revisar la contraseña o el estado de la cuenta.
3. Sólo cuentas de prueba **dedicadas** del ambiente de pruebas, con el rol mínimo que necesita el escenario. Nunca cuentas personales ni de producción.
4. `e2e/.auth/*.json` contiene tokens: no lo leas completo, no lo pegues en el chat, no lo commitees (verifica `git check-ignore e2e/.auth/<rol>.json` y `git check-ignore .env.e2e`).
5. No alteres `menu`, roles ni tokens en `localStorage` para simular otro rol: eso no prueba la aplicación y salta el control de acceso. Cada rol, su usuario de prueba.

**Login manual (alternativa)** — si no hay usuarios de prueba para un rol, **el usuario** inicia sesión a mano y guarda la sesión; nunca escribas sus credenciales:
```bash
playwright-cli open --headed http://localhost:4200
# el usuario completa el login en la ventana; luego:
playwright-cli state-save e2e/.auth/<rol>.json
playwright-cli close
```
Los tokens caducan (`expires_at`): si un test termina en la página de autenticación, la sesión venció; con login manual pide repetirlo, con login automático vuelve a correr la suite.

## Paso 4 — Plan y specs

1. **Plan versionado** en `e2e/specs/<funcionalidad>.plan.md` con el formato de `playwright-cli` (`references/test-generation.md` §1.4), una sección por criterio de aceptación, indicando en cada escenario el **rol** (proyecto) y la **etiqueta** del módulo. Cubre camino feliz, validaciones, vacíos y permisos por rol (un rol que no debe ver o hacer algo).
2. **Generar** cada escenario con el flujo de `playwright-cli` (seed → `--debug=cli` → `attach` → acciones → aserciones), de a uno y cerrando la sesión entre escenarios:
   ```bash
   PLAYWRIGHT_HTML_OPEN=never npx playwright test e2e/seed.spec.ts --project=<rol> --debug=cli   # en segundo plano
   playwright-cli attach tw-XXXX
   ```
3. Specs: `e2e/<modulo>/<escenario>.spec.ts`, **un escenario por archivo**, con cabecera `// spec: e2e/specs/<funcionalidad>.plan.md` y etiquetas:
   ```ts
   test('<escenario>', { tag: ['@plan-mejoramiento', '@auditado', '@lectura'] }, async ({ page }) => { … });
   ```
4. Locators por rol y nombre accesible (`getByRole`, `getByLabel`). Si un control no tiene nombre accesible, no inventes selectores CSS frágiles: propón agregar `aria-label` o `data-testid` en el componente como cambio del MF, dentro del alcance aprobado de la issue.
5. Nada de `waitForTimeout` ni `networkidle`: espera por lo observable (`toBeVisible`, `toHaveURL`, la respuesta del MID con `page.waitForResponse`).

## Paso 5 — Datos de prueba

- Cada escenario lleva además la etiqueta **`@lectura`** (sólo consulta, no crea ni cambia nada) o **`@escritura`** (crea, edita o cambia estados). En el ambiente de pruebas compartido (funcionamiento, Drone) corren sólo los `@lectura`, salvo que el escenario `@escritura` limpie lo que crea y el usuario haya aprobado correrlo ahí. Contra producción, nunca.
- En local se prueba contra el **CRUD local**. Escribir en un ambiente compartido sólo con confirmación explícita del usuario para ese escenario.
- Lo que crea un test lleva un marcador único (`E2E-<AAAAMMDD-HHmm>` en un campo de texto) y se limpia al final (borrado lógico vía API del CRUD local en un `afterEach` o fixture). Si no se puede limpiar, dilo en el informe.
- Los escenarios no dependen del orden ni de datos creados por otro escenario: cada uno prepara lo suyo o parte de datos semilla documentados en el plan.

## Paso 6 — Ejecutar y reparar

```bash
PLAYWRIGHT_HTML_OPEN=never npx playwright test --grep @<modulo>        # antes del PR: TODOS los escenarios del módulo
PLAYWRIGHT_HTML_OPEN=never npx playwright test                         # completo: si cambiaste e2e/fixtures.ts y antes de un release
```

- Fallos: flujo de reparación de `playwright-cli` (`references/test-generation.md` §3), de a uno.
- Si el MF no hace lo que dice el criterio: **para y pregunta** si es un bug o si el criterio cambió (no ajustes el test para que pase).
- Nunca `test.skip`/`test.fixme` sin decisión del usuario.

## Trabajo en equipo en el mismo módulo

Varias personas agregan flujos al mismo módulo; los escenarios e2e del módulo son de todos.

| Situación | Qué se hace |
|---|---|
| Issue nueva en un módulo | Plan propio `e2e/specs/<funcionalidad>.plan.md` (no se edita el plan de otra funcionalidad) y escenarios en archivos propios con la etiqueta `@<modulo>`. Así dos issues en paralelo no chocan |
| Lo compartido: login por rol, navegación, creación y limpieza de datos | Vive en `e2e/fixtures.ts`. Quien lo cambia corre **todas** las e2e del MF, no sólo las del módulo |
| Tu cambio toca la interfaz (texto, botón, etiqueta, paso del flujo) | Busca en `e2e/` los escenarios que lo usan (`grep -rn "<texto o nombre accesible>" e2e/`) y actualízalos en el mismo PR; es parte del cambio. Si el comportamiento cambió a propósito, dilo en el PR |
| Antes del PR | Corre **todos** los escenarios del módulo (`--grep @<modulo>`), no sólo los tuyos: tu cambio puede romper flujos de otros. Lo que ya fallaba en la base se reporta aparte |
| Después de traer cambios de otra persona al módulo | El aviso de `contexto-proyecto` sugiere correr `--grep @<modulo>` si tienes el stack y la sesión; es sugerencia, no obligación |
| Falla un escenario por el cambio de otra persona | No corrijas su interfaz ni su escenario por tu cuenta: pásale el escenario que falla y la traza (`test-results/<…>/trace.zip`, se abre con `npx playwright show-trace`), y decide el autor |
| Roles | Los nombres de `projects` en `playwright.config.ts` son los mismos para todo el equipo; cada persona guarda en `e2e/.auth/` la sesión de **sus** usuarios de prueba |
| Datos | Cada escenario crea lo suyo por API con marcador y lo limpia (Paso 5); nunca depende de lo que haya en la base local de alguien |

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

## Paso 8 — Ambiente de pruebas, funcionamiento y Drone

Las mismas pruebas sirven para que funcionamiento verifique el sistema antes y después de un cambio, y para el pipeline cuando se autorice. Corren contra el **ambiente de pruebas desplegado**, no contra un stack levantado en el pipeline.

- **Comando**: `E2E_BASE_URL=<url del ambiente de pruebas> npx playwright test --grep @lectura` (o `--grep "@<modulo>.*@lectura"` para un módulo). Script sugerido en `package.json`: `"e2e:pruebas": "playwright test --grep @lectura"`.
- **`e2e/README.md`** (versionado, para quien no desarrolla): requisitos (Node, `npm ci` o `pnpm install`, `npx playwright install chromium`), cómo crear `.env.e2e` desde `.env.e2e.example` (las credenciales las entrega el responsable de las cuentas de prueba, nunca por el repo), los comandos (todo, por módulo, sólo lectura), cómo abrir el reporte (`npx playwright show-report`) y qué hacer si falla (a quién reportar, con el reporte o la traza). Escríbelo en lenguaje simple, sin jerga de desarrollo.
- **Drone (sólo con autorización; no edites `.drone.yml` sin ella)**: deja el borrador de la solicitud en el informe. Base del paso, después del despliegue al ambiente de pruebas:
  ```yaml
  - name: e2e_pruebas
    image: mcr.microsoft.com/playwright:v<misma versión que @playwright/test>-jammy
    environment:
      E2E_BASE_URL: <url del ambiente de pruebas>
      E2E_JEFE_OCI_USER:
        from_secret: e2e_jefe_oci_user
      E2E_JEFE_OCI_PASS:
        from_secret: e2e_jefe_oci_pass
      # … un par de secrets por rol, con los mismos nombres en todos los MF
    commands:
      - npm install -g pnpm && pnpm install --frozen-lockfile   # o npm ci según el lockfile
      - pnpm run e2e:pruebas
    depends_on: [<paso que despliega a pruebas>]
  ```
  Puntos que la solicitud debe decir: los secrets los registra Infraestructura (nunca valores en el `.drone.yml`); sólo `@lectura`; el reporte HTML se publica si el pipeline tiene dónde (p. ej. el bucket que ya usan los pasos `publish_s3_*`); la cuenta de prueba se bloquea si su contraseña vence, así que alguien debe ser responsable de rotarla; y conviene avisar a Seguridad que hay credenciales de prueba en el pipeline.

## Pruebas de API sin interfaz

Para criterios que sólo tocan el MID o el CRUD, prueba el endpoint local con `curl` (o el `request` de Playwright) desde lo que documenta el Swagger: status esperado, envoltura `{ Success, Status, Message, Data }`, caso vacío (`200` con `Data: []`), errores (`400`, `404`, `409`). Registra comando y respuesta resumida en el mismo informe, sin tokens ni datos personales.

No hagas commits: al terminar sugiere `/commit-oas` con los archivos de `e2e/` (planes, specs, fixtures), `playwright.config.ts`, `package.json` y el lockfile actualizado por el gestor. Nunca `e2e/.auth/`.
