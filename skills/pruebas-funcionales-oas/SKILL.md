---
name: pruebas-funcionales-oas
description: Pruebas funcionales y e2e de los MF udistrital (Angular + single-spa) con Playwright, TypeScript y Page Object Model, sobre la skill oficial playwright-cli — instala en el MF la carpeta e2e/ autocontenida desde la plantilla del plugin (core/ genérico con login institucional OIDC/WSO2 por rol, bloqueo automático de escrituras en escenarios @lectura y simulación de respuestas GET; pages/ con los page objects del proyecto), levanta y verifica el stack local (root, MF, APIs), usa usuarios de prueba dedicados desde e2e/.env.e2e (o secrets de Drone) sin que la IA lea sus valores, convierte los criterios de aceptación de la especificación en planes y escenarios (un escenario por archivo, etiquetados por módulo, rol y @lectura/@escritura), actualiza los escenarios que usan una pantalla que cambió, corre y repara los specs, explica cómo verlos en vivo (modo UI, --headed, WSL) y dónde quedan reporte y trazas, y deja evidencias para doc-issue-oas y seguridad-oas, además de la propuesta para funcionamiento y Drone. Úsala cuando el usuario diga "/pruebas-funcionales-oas", "prueba el flujo", "pruebas funcionales", "pruebas e2e", "valida en el navegador", "genera los tests de Playwright", "toma las capturas de la issue", o al cerrar una issue con interfaz.
---

# Pruebas funcionales OAS (Playwright en los MF)

La mecánica de Playwright (snapshot, refs, generación de código, plan → generar → reparar, depuración con `--debug=cli`) es de la skill **`playwright-cli`**: cárgala y sigue su `references/test-generation.md` y `references/playwright-tests.md`. Esta skill agrega lo propio de los MF udistrital: la estructura `e2e/`, el stack local, el login institucional, los datos y las evidencias.

- Plantilla del marco: `${CLAUDE_PLUGIN_ROOT}/plantillas/e2e/`.
- Implementación de referencia: `plan_anual_auditoria_mf/e2e/` (SISIFO, udistrital/sisifo_documentacion#939).
- Reglas de equipo para pruebas en módulos compartidos: `AGENTS.md` §8.

## Paso 0 — Alcance y prerrequisitos

1. Issue y especificación (`<UDISTRITAL>/.claude/specs/<repo>-<n>.md`): de su sección **Pruebas E2E** y de la tabla "Criterios de aceptación → verificación" salen los escenarios nuevos y los existentes que hay que ajustar. Sin especificación, pide los criterios al usuario.
2. MF afectados (por la especificación o el diff) y su módulo: la etiqueta `@<modulo>` y la carpeta `e2e/tests/<modulo>/` usan el **nombre de la carpeta** del módulo en `src/app/modules/` (p. ej. `@plan-mejoramiento`), para que el aviso tras un pull sugiera los escenarios correctos. Los recorridos transversales (menú, login) van en `@navegacion`.
3. Escenarios existentes afectados: si el MF ya tiene `e2e/`, busca los que usan las pantallas o textos que cambian (`grep -rn "<texto o nombre accesible>" e2e/pages e2e/tests`). Se actualizan en el mismo PR.
4. Herramienta: `playwright-cli --version`. Si no está: `npm install -g @playwright/cli@latest` (con confirmación).
5. Usuarios de prueba: comprueba que `e2e/.env.e2e` tenga los roles que necesitan los escenarios, **solo los nombres**: `grep -oE '^E2E_[A-Z_]+=' e2e/.env.e2e`. Si falta un rol, usa el login manual del Paso 3.

## Paso 1 — `e2e/` en el MF (solo la primera vez)

Si el MF no tiene `e2e/playwright.config.ts`, propón (con confirmación y en la rama de la issue, como una tarea más del plan) copiar la plantilla:

```bash
cp -r "${CLAUDE_PLUGIN_ROOT}/plantillas/e2e" <repo>/e2e
cd <repo>/e2e && npm install && npx playwright install chromium   # genera e2e/package-lock.json (se versiona)
```

Estructura resultante:

```
e2e/
  package.json · package-lock.json · tsconfig.json   # autocontenido: solo @playwright/test y TypeScript (npm)
  playwright.config.ts      # ROLES del proyecto y opciones de ejecución
  .env.e2e.example          # nombres de las variables (versionado)
  README.md                 # guía para el equipo y para funcionamiento
  core/                     # genérico, NO se modifica por proyecto (mejoras → plantilla del plugin)
    config.ts               # lee .env.e2e, roles con usuario, un proyecto por rol con grep @<rol>
    global-setup.ts         # login WSO2 por rol → .auth/<rol>.json; reutiliza la sesión vigente
    navegador.ts            # CORS del core-mf de CloudFront y overlay del dev-server
    fixtures.ts             # test extendido: bloqueo de escrituras en @lectura, errores, simularGet
    base.page.ts            # clase base del POM (rutas, alertas SweetAlert, ancho de pantalla)
  pages/                    # page objects del proyecto (shell.page.ts = menú del root, ya incluido)
  specs/<funcionalidad>.plan.md   # planes de prueba (versionados)
  tests/<modulo>/<escenario>.spec.ts   # un escenario por archivo
  .env.e2e · .auth/ · playwright-report/ · test-results/ · node_modules/   # NUNCA se versionan
```

Ajustes al copiar:

- `package.json`: `name` = `<repo>-e2e`. `README.md` y `specs/navegacion.plan.md`: reemplaza los marcadores `<…>`.
- `playwright.config.ts`: `ROLES` con los roles reales del MF (servicio de roles, `environment`), en minúsculas con `-`. No los inventes.
- `.env.e2e.example`: un par `E2E_<ROL>_USER` / `E2E_<ROL>_PASS` por rol. **Convención común a todos los MF**, en el `.env.e2e` local y en los secrets de Drone: `<ROL>` es el proyecto en mayúsculas con `_` (`jefe-dependencia` ↔ `E2E_JEFE_DEPENDENCIA_*`). La variable dice el rol **real** de la cuenta, no el que se esperaba.
- `.gitignore` del MF:
  ```
  !/e2e/package-lock.json        # si la raíz ignora package-lock.json
  /e2e/.env.e2e
  /e2e/.auth/
  /e2e/node_modules/
  /e2e/playwright-report/
  /e2e/test-results/
  /e2e/blob-report/
  .playwright-cli/
  ```
- Que el MF no tome `e2e/`: `testPathIgnorePatterns: ['/node_modules/', '<rootDir>/e2e/']` en `jest.config.ts` (o `exclude` en Karma) y `"exclude": ["node_modules", "e2e"]` en el `tsconfig.json` raíz. Verifica `sonar.sources`, `lintFilePatterns` y `tsconfig.app.json`: si ya se limitan a `src/`, no hace falta tocarlos.
- El `.env.e2e` lo crea y llena **el usuario** (los guardianes no dejan a la IA escribirlo). Si ya tenía las variables en otra ruta (p. ej. `.claude/.env`), dale el comando para que él lo mueva y renombre.
- Verificación: `npx tsc --noEmit` en `e2e/`, `npx playwright test --list` (solo proyectos de roles con usuario), build del MF y que Jest no liste nada de `e2e/`.

## Paso 2 — Stack local

Los MF se prueban dentro del **root** (`auditoria_plan_mejoramiento_root_mf` en SISIFO, puerto `4200`), que carga los MF locales según `parcels` de su `environment` y el `core-mf` remoto.

1. Lee los puertos reales en el `environment.ts` del root y en los `package.json` de los MF.
2. Comprueba qué está arriba (`curl -s -o /dev/null -w '%{http_code}' <url>`). Lo que falte, pídeselo al usuario o levántalo en segundo plano con su confirmación (`pnpm start` en cada repo, con el Node del repo).
3. Revisa a qué APIs apunta el `environment.ts` local del MF. Si apunta a `localhost` y no hay CRUD/MID locales, el usuario decide: levantarlos o apuntar a las APIs de pruebas (VPN). Un cambio local del `environment` **no entra en ningún commit**. Si apunta a pruebas compartido, aplica la regla de datos del Paso 5.

## Paso 3 — Sesión del login institucional (OIDC)

El login es OIDC implícito contra WSO2 (`autenticacion.portaloas.udistrital.edu.co`). El `core-mf` guarda `access_token`, `id_token`, `expires_at`, `menu` y `persona_id` en el `localStorage` del root.

**Login automático por rol (preferido)** — lo hace `core/global-setup.ts` al inicio de cada corrida, con los usuarios de `E2E_<ROL>_USER/_PASS`: abre el root, pulsa **"Iniciar Sesión"**, llena `input[name=username], #usernameUserInput` y `input[name=password], #password`, envía, espera volver al root con las claves de sesión (`clavesSesion` en `playwright.config.ts`) y guarda `e2e/.auth/<rol>.json`. Si la sesión guardada sigue vigente (`expires_at` con margen), no repite el login.

Reglas:
1. **Los valores de `.env.e2e` nunca se leen, muestran ni copian** (ni en el chat, ni en logs, ni en el informe). Nunca los pases por `playwright-cli fill` ni los escribas en un spec.
2. Si el login falla, **no reintentes**: WSO2 bloquea la cuenta o pide captcha tras varios intentos. El setup se detiene con el rol que falló; pide al usuario revisar la VPN, la contraseña o el estado de la cuenta.
3. Solo cuentas de prueba **dedicadas** del ambiente de pruebas, con el rol mínimo que necesita el escenario. Nunca cuentas personales ni de producción.
4. `e2e/.auth/*.json` contiene tokens: no lo leas completo, no lo pegues en el chat, no lo commitees (`git check-ignore e2e/.auth/<rol>.json e2e/.env.e2e`).
5. No alteres `menu`, roles ni tokens en `localStorage` para simular otro rol: eso no prueba la aplicación y salta el control de acceso. Cada rol, su usuario de prueba.
6. Si el login cambia en el core-mf o WSO2, ajusta `core/global-setup.ts` **en la plantilla del plugin** y en los MF que la usan.

**Login manual (alternativa)** — si no hay usuario de prueba para un rol, **el usuario** inicia sesión a mano y guarda la sesión; nunca escribas sus credenciales:
```bash
playwright-cli open --headed http://localhost:4200
# el usuario completa el login en la ventana; luego:
playwright-cli state-save e2e/.auth/<rol>.json
playwright-cli close
```
Los tokens caducan: si un escenario termina en la página de autenticación, la sesión venció (`rm -rf e2e/.auth` y volver a correr).

## Paso 4 — Plan, page objects y escenarios

1. **Plan versionado** en `e2e/specs/<funcionalidad>.plan.md` (formato de `playwright-cli`, `references/test-generation.md` §1.4): contexto, **datos semilla**, y una sección por escenario con su rol, etiquetas, pasos y resultado esperado. Cubre camino feliz, validaciones, vacíos y **permisos por rol** (un rol que no debe ver o hacer algo).
2. **Explora antes de fijar selectores**: menú y pantallas reales por rol (snapshot de `playwright-cli` o un script de exploración en el scratchpad, con escrituras bloqueadas). Así salen las opciones, títulos y datos reales.
3. **Page objects** en `e2e/pages/<pantalla>.page.ts`, extendiendo `BasePage`: los locators y las acciones viven aquí, con nombres de negocio (`registro.abrirFicha()`). Los escenarios **no** usan selectores.
   - Locators por rol y nombre accesible (`getByRole`, `getByLabel`). Donde no haya nombre accesible, el selector CSS queda **dentro** del page object; si es frágil, propón `aria-label` o `data-testid` en el componente como cambio del MF, dentro del alcance aprobado.
   - Material: el `mat-select` vacío lo tapa su etiqueta (se hace clic en el `mat-form-field`); las opciones deshabilitadas (`--Seleccionar--`) no se eligen.
4. **Escenarios** en `e2e/tests/<modulo>/<escenario>.spec.ts`, **uno por archivo**, importando `test` y `expect` de `../../core/fixtures`, con cabecera `// spec: e2e/specs/<funcionalidad>.plan.md` y etiquetas:
   ```ts
   test('<escenario>', { tag: ['@plan-mejoramiento', '@auditor', '@lectura'] }, async ({ page, escriturasBloqueadas }, testInfo) => {
     await test.step('<criterio en lenguaje de negocio>', async () => { … });
     expect(escriturasBloqueadas).toEqual([]);
   });
   ```
   - `test.step` con el texto del criterio: es lo que se lee en el modo UI y en el reporte.
   - Datos compartidos del módulo (vigencia, cómo abrir una entidad, opciones esperadas) en `e2e/tests/<modulo>/datos.ts`.
5. Nada de `waitForTimeout` ni `networkidle`: espera por lo observable (`toBeVisible`, `toHaveURL`, `expect.poll`, `page.waitForResponse`).
6. Generar con `playwright-cli` (seed → `--debug=cli` → `attach` → acciones → aserciones), de a un escenario: `tests/navegacion/menu.spec.ts` de la plantilla sirve de seed.

## Paso 5 — Datos de prueba

- Cada escenario lleva **`@lectura`** (solo consulta) o **`@escritura`** (crea, edita o cambia estados). En `@lectura`, `core/fixtures.ts` **aborta** cualquier `POST/PUT/PATCH/DELETE` fuera del root y lo adjunta al reporte (`escriturasBloqueadas`): una corrida de lectura nunca modifica el ambiente. Conviene un escenario que lo demuestre (intentar una escritura y verificar que se bloqueó y que el dato no cambió).
- En el ambiente de pruebas compartido (funcionamiento, Drone) corren solo los `@lectura`. Un `@escritura` corre contra el CRUD local, o en compartido solo con aprobación explícita del usuario para ese escenario y limpiando lo que crea. Contra producción, nunca.
- Lo que crea un `@escritura` lleva un marcador único (`E2E-<AAAAMMDD-HHmm>`) y se limpia al final (borrado lógico vía API en un fixture). Si no se puede limpiar, dilo en el informe.
- **`@simulado`**: para un estado de pantalla que no existe en los datos (p. ej. "sin calificaciones"), `simularGet('<patrón>', (data) => …)` reescribe el `Data` de la respuesta GET sin escribir en el backend. No prueba el backend: el escenario lo dice con la etiqueta.
- Los escenarios no dependen del orden ni de datos creados por otro. Los datos semilla (vigencia, entidad) van en el plan y se pueden cambiar por variable (`E2E_<DATO>`), con un mensaje claro si no existen.

## Paso 6 — Ejecutar, ver y reparar

Desde `e2e/` (con el stack arriba):

```bash
npm test                                   # todo
npx playwright test --grep @<modulo>       # antes del PR: TODOS los escenarios del módulo
npm run test:lectura                       # solo lectura
npx playwright test --ui                   # modo UI: escenario por escenario, pasos, Before/After, red
npx playwright test --headed               # el navegador haciendo el flujo
npx playwright test <archivo> --debug      # paso a paso
npm run report                             # reporte HTML de la última corrida
```

- **WSL**: `--ui`, `--headed` y `--debug` necesitan la interfaz gráfica (`guiApplications=true` en `C:\Users\<usuario>\.wslconfig` + `wsl --shutdown`; `ls /tmp/.X11-unix/` muestra `X0`). Sin ella, `npx playwright test --ui-port=9323` y abrir `http://localhost:9323` en el navegador de Windows (se ven los pasos, no en vivo). No cambies el `.wslconfig` sin confirmación: reiniciar WSL apaga todo el stack.
- **Resultados**: consola (✓/✘), `e2e/playwright-report/` (pasos, capturas adjuntas, errores; solo la última corrida) y `e2e/test-results/` (traza `trace.zip` de los que fallan: `npx playwright show-trace …`).
- Estable = la suite en verde **dos veces seguidas**, y una falla provocada sale con código distinto de 0.
- Fallos: flujo de reparación de `playwright-cli` (`references/test-generation.md` §3), de a uno.
- Si el MF no hace lo que dice el criterio: **para y pregunta** si es un bug o si el criterio cambió (no ajustes el test para que pase).
- Nunca `test.skip`/`test.fixme` sin decisión del usuario.

## Trabajo en equipo en el mismo módulo

| Situación | Qué se hace |
|---|---|
| Issue nueva en un módulo | Plan propio `e2e/specs/<funcionalidad>.plan.md` (no se edita el plan de otra funcionalidad) y escenarios en archivos propios con `@<modulo>`. Dos issues en paralelo no chocan |
| Tu cambio toca la interfaz (texto, botón, etiqueta, paso del flujo) | Busca en `e2e/pages` y `e2e/tests` lo que lo usa y actualízalo en el mismo PR. Casi siempre basta con el page object. Si el comportamiento cambió a propósito, dilo en el PR |
| Lo compartido: `core/` y `pages/` usados por varios módulos | Quien los cambia corre **todas** las e2e del MF. `core/` no se cambia por proyecto: la mejora va a la plantilla del plugin |
| Antes del PR | Corre **todos** los escenarios del módulo (`--grep @<modulo>`), no solo los tuyos. Lo que ya fallaba en la base se reporta aparte |
| Después de traer cambios de otra persona al módulo | El aviso de `contexto-proyecto` sugiere correr `--grep @<modulo>`; es sugerencia, no obligación |
| Falla un escenario por el cambio de otra persona | No corrijas su interfaz ni su escenario por tu cuenta: pásale el escenario y la traza, y decide el autor |
| Roles | Los nombres de `ROLES` son los mismos para todo el equipo; cada persona tiene su `.env.e2e` y sus sesiones en `e2e/.auth/` |

## Paso 7 — Evidencias e informe

- En cada escenario que verifica un criterio, adjunta la captura: `await testInfo.attach('<criterio>', { body: await page.screenshot(), contentType: 'image/png' })`. Quedan en el reporte HTML.
- **Cuidado**: trazas, reporte y capturas contienen la sesión de la cuenta de prueba y datos reales del ambiente. Solo dentro del equipo; nunca en sitios abiertos ni en la issue pública sin revisar las capturas.
- Escribe el informe en el chat y en `.claude/docs/pruebas/<rama-sin-prefijo>.md` (local, no versionado):
  ```markdown
  # Pruebas funcionales — <repo> · <rama> · <AAAA-MM-DD>
  Stack: root <url> · MF <url> · APIs <local|pruebas> · Roles: <lista>

  | Criterio | Escenario (archivo) | Rol | Resultado | Evidencia |
  |---|---|---|---|---|

  ## Escenarios existentes ajustados
  ## Fallos y decisiones
  ## Datos creados y limpieza (o "solo lectura: 0 escrituras")
  ## Pendientes (sesión vencida, criterios no automatizables, por confirmar)
  ```
- Ese informe lo usan `/doc-issue-oas` (sección "Pruebas realizadas") y `/seguridad-oas` (ítem "Pruebas funcionales realizadas").

## Paso 8 — Funcionamiento y Drone (propuesta, pendiente de autorización)

Las mismas pruebas sirven para que funcionamiento verifique el sistema antes y después de un cambio, y para el pipeline cuando se autorice. Corren contra el **ambiente de pruebas desplegado**, solo `@lectura`.

- **Funcionamiento**: clona el MF, `cd e2e && npm ci && npx playwright install chromium`, crea `.env.e2e` con las cuentas que le entrega el responsable, y corre `E2E_BASE_URL=<url de pruebas> npm run test:lectura`. No necesita Angular ni levantar el stack. El `e2e/README.md` está escrito para quien no desarrolla.
- **Drone (no edites `.drone.yml` sin autorización)**: deja el borrador en el informe. Paso posterior al despliegue a pruebas (en SISIFO, `publish_s3_release` en `release/*`):
  ```yaml
  - name: e2e_pruebas
    image: mcr.microsoft.com/playwright:v<misma versión que @playwright/test>-noble
    environment:
      E2E_BASE_URL: <url del root en pruebas>
      E2E_<ROL>_USER:
        from_secret: e2e_<rol>_user
      E2E_<ROL>_PASS:
        from_secret: e2e_<rol>_pass
      # … un par de secrets por rol, con los mismos nombres en todos los MF
    commands:
      - cd e2e && npm ci && npm run test:lectura
    depends_on: [<paso que despliega a pruebas>]
  ```
  La solicitud debe decir: los secrets los registra Infraestructura (nunca valores en el `.drone.yml`); solo `@lectura`; si falla, el pipeline se detiene; el reporte HTML solo en almacenamiento restringido (contiene la sesión); alguien es responsable de rotar las contraseñas de las cuentas de prueba; validar antes el login y el CORS contra la URL desplegada y la caché de CloudFront tras el despliegue; y avisar a Seguridad que hay credenciales de prueba en el pipeline.

## Pruebas de API sin interfaz

Para criterios que solo tocan el MID o el CRUD, prueba el endpoint local con `curl` (o el `request` de Playwright) desde lo que documenta el Swagger: status esperado, envoltura `{ Success, Status, Message, Data }`, caso vacío (`200` con `Data: []`), errores (`400`, `404`, `409`). Registra comando y respuesta resumida en el mismo informe, sin tokens ni datos personales.

No hagas commits: al terminar sugiere `/commit-oas` con los archivos de `e2e/` (planes, page objects, escenarios, `package-lock.json`) y los ajustes del MF (`.gitignore`, `jest.config.ts`, `tsconfig.json`). Nunca `e2e/.env.e2e`, `e2e/.auth/` ni un cambio local del `environment`.
