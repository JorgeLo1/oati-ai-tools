/**
 * Login institucional (OIDC con WSO2) una vez por rol al inicio de la corrida. Guarda la sesión
 * (localStorage del root) en .auth/<rol>.json para que la reutilicen los escenarios.
 *
 * - Sin traza, video ni capturas: grabarían la contraseña.
 * - Sin reintentos: WSO2 bloquea la cuenta tras varios intentos fallidos.
 * - Si la sesión guardada sigue vigente (expires_at), no se vuelve a iniciar sesión.
 */
import fs from 'node:fs';
import { chromium, type BrowserContext, type FullConfig } from '@playwright/test';
import { BASE_URL, DIR_SESIONES, credenciales, prefijoRol, rolesConUsuario, rutaSesion } from './config';
import { prepararContexto } from './navegador';

const MARGEN_VIGENCIA_MS = 15 * 60 * 1000;

export interface MetadatosE2E {
  /** Roles del proyecto (nombres de los proyectos de Playwright). */
  roles: string[];
  /** Claves de localStorage que indican que la sesión quedó completa. */
  clavesSesion?: string[];
}

function sesionVigente(ruta: string): boolean {
  try {
    const estado = JSON.parse(fs.readFileSync(ruta, 'utf-8'));
    const origen = estado.origins?.find((o: { origin: string }) => o.origin === new URL(BASE_URL).origin);
    const expira = origen?.localStorage?.find((i: { name: string }) => i.name === 'expires_at')?.value;
    return !!expira && Date.parse(expira) - Date.now() > MARGEN_VIGENCIA_MS;
  } catch {
    return false;
  }
}

async function iniciarSesion(contexto: BrowserContext, usuario: string, clave: string, claves: string[]) {
  const page = await contexto.newPage();
  await page.goto(BASE_URL);
  await page.getByRole('button', { name: 'Iniciar Sesión' }).click();
  const campoUsuario = page.locator('input[name=username], #usernameUserInput').first();
  await campoUsuario.waitFor({ timeout: 60_000 });
  await campoUsuario.fill(usuario);
  await page.locator('input[name=password], #password').first().fill(clave);
  await page.locator('button[type=submit], input[type=submit]').first().click();
  await page.waitForURL((url) => url.href.startsWith(BASE_URL), { timeout: 90_000 });
  await page.waitForFunction((c) => c.every((k) => !!localStorage.getItem(k)), claves, { timeout: 90_000 });
}

export default async function globalSetup(config: FullConfig) {
  const { roles = [], clavesSesion = ['id_token'] } = (config.metadata ?? {}) as Partial<MetadatosE2E>;
  fs.mkdirSync(DIR_SESIONES, { recursive: true });

  for (const rol of rolesConUsuario(roles)) {
    const ruta = rutaSesion(rol);
    if (sesionVigente(ruta)) {
      console.log(`[e2e] ${rol}: sesión vigente, se reutiliza`);
      continue;
    }
    const { usuario, clave } = credenciales(rol)!;
    const browser = await chromium.launch();
    const contexto = await browser.newContext();
    await prepararContexto(contexto);
    try {
      await iniciarSesion(contexto, usuario, clave, clavesSesion);
      await contexto.storageState({ path: ruta });
      console.log(`[e2e] ${rol}: sesión iniciada`);
    } catch (error) {
      fs.rmSync(ruta, { force: true });
      throw new Error(
        `[e2e] falló el login del rol ${rol} (${prefijoRol(rol)}_USER). No se reintenta para no bloquear ` +
          `la cuenta en WSO2: revisa la contraseña o el estado de la cuenta. Causa: ${(error as Error).message.split('\n')[0]}`,
      );
    } finally {
      await browser.close();
    }
  }
}
