/**
 * Login institucional (OIDC con WSO2) de un rol, en un proceso de Node aparte.
 *
 *   node core/login.mjs <rol> <baseURL> <rutaSesion> <clavesSesion separadas por coma>
 *
 * Corre fuera de Playwright Test a propósito: así ninguna traza, video ni configuración de proyecto
 * (p. ej. el storageState del rol) alcanza al navegador donde se escribe la contraseña. Lo usan el
 * global-setup y el fixture vigilarSesion (core/sesion.ts → renovarSesion).
 *
 * Las credenciales llegan por variables de entorno (E2E_<ROL>_USER/_PASS) y nunca se imprimen.
 * Salida: 0 sesión guardada · 2 WSO2 rechazó las credenciales (no se reintenta) · 1 otra falla.
 */
import { chromium } from '@playwright/test';

const [rol, baseURL, rutaSesion, clavesTexto = 'id_token'] = process.argv.slice(2);
const claves = clavesTexto.split(',').filter(Boolean);
const prefijo = `E2E_${rol.toUpperCase().replace(/-/g, '_')}`;
const usuario = process.env[`${prefijo}_USER`];
const clave = process.env[`${prefijo}_PASS`];

if (!usuario || !clave) {
  console.error(`[e2e] sin ${prefijo}_USER/_PASS`);
  process.exit(1);
}

const browser = await chromium.launch();
try {
  const contexto = await browser.newContext();
  // Mismos ajustes que core/navegador.ts (CORS del core-mf y overlay del dev-server): mantenerlos iguales.
  await contexto.route('https://pruebascoreclientes.portaloas.udistrital.edu.co/**', async (route) => {
    const respuesta = await route.fetch();
    await route.fulfill({ response: respuesta, headers: { ...respuesta.headers(), 'access-control-allow-origin': '*' } });
  });
  await contexto.addInitScript(() => {
    setInterval(() => document.querySelectorAll('[id^="webpack-dev-server-client-overlay"]').forEach((e) => e.remove()), 300);
  });

  const page = await contexto.newPage();
  await page.goto(baseURL);
  await page.getByRole('button', { name: 'Iniciar Sesión' }).click();
  const campoUsuario = page.locator('input[name=username], #usernameUserInput').first();
  await campoUsuario.waitFor({ timeout: 60_000 });
  await campoUsuario.fill(usuario);
  await page.locator('input[name=password], #password').first().fill(clave);
  await page.locator('button[type=submit], input[type=submit]').first().click();
  // WSO2 vuelve al root si acepta, o se queda en su página con authFailure si rechaza las credenciales.
  await page.waitForURL((url) => url.href.startsWith(baseURL) || /authFailure=true|oauth2_error/.test(url.href), {
    timeout: 90_000,
  });
  if (!page.url().startsWith(baseURL)) {
    console.error('[e2e] WSO2 rechazó el usuario o la contraseña (o la cuenta está bloqueada)');
    process.exitCode = 2;
  } else {
    await page.waitForFunction((c) => c.every((k) => !!localStorage.getItem(k)), claves, { timeout: 90_000 });
    await contexto.storageState({ path: rutaSesion });
  }
} catch (error) {
  console.error(`[e2e] ${String(error?.message ?? error).split('\n')[0]}`);
  process.exitCode = 1;
} finally {
  await browser.close();
}
