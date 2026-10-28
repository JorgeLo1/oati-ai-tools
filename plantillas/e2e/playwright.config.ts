import { defineConfig } from '@playwright/test';
import { BASE_URL, proyectosPorRol } from './core/config';
import type { MetadatosE2E } from './core/global-setup';

/**
 * Roles del proyecto con usuario de prueba (nombres en minúsculas con "-").
 * Salen de la configuración real del MF (servicio de roles / environment), no se inventan.
 * Cada rol usa E2E_<ROL>_USER / E2E_<ROL>_PASS (jefe-dependencia → E2E_JEFE_DEPENDENCIA_*).
 */
export const ROLES = ['<rol-1>', '<rol-2>'];

const metadatos: MetadatosE2E = {
  roles: ROLES,
  // El core-mf deja la sesión completa cuando guarda el token, el menú y la persona.
  clavesSesion: ['id_token', 'menu', 'persona_id'],
};

export default defineConfig({
  testDir: './tests',
  globalSetup: require.resolve('./core/global-setup'),
  metadata: metadatos,
  fullyParallel: false, // comparten backend y datos del ambiente de pruebas
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: BASE_URL,
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    navigationTimeout: 90_000,
  },
  projects: proyectosPorRol(ROLES),
});
