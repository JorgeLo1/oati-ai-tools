/**
 * Núcleo genérico del marco E2E (no depende del proyecto): lectura de variables, roles con
 * usuario y construcción de un proyecto de Playwright por rol.
 *
 * Convención común a todos los proyectos udistrital:
 *   E2E_BASE_URL                 URL del root que compone los MF
 *   E2E_<ROL>_USER / _PASS       usuario de prueba dedicado por rol (jefe-dependencia → JEFE_DEPENDENCIA)
 *   E2E_ESCRITURA=1              permite correr escenarios @escritura (o pasar --grep @escritura)
 */
import path from 'node:path';
import type { Project } from '@playwright/test';

export const RAIZ_E2E = path.resolve(__dirname, '..');
export const DIR_SESIONES = path.join(RAIZ_E2E, '.auth');

// Local: lee e2e/.env.e2e si existe (Node >= 20.12). En CI las variables llegan como secrets.
try {
  process.loadEnvFile(path.join(RAIZ_E2E, '.env.e2e'));
} catch {
  /* sin archivo: se usan las variables del entorno */
}

export const BASE_URL = (process.env['E2E_BASE_URL'] || 'http://localhost:4200').replace(/\/$/, '');

/**
 * Los escenarios @escritura cambian datos de un ambiente compartido: solo corren si se piden de forma
 * explícita, con `--grep @escritura` (npm run test:escritura) o con E2E_ESCRITURA=1. Así `npm test` o
 * `npx playwright test <archivo>` nunca escriben por descuido. La marca pasa por variable de entorno
 * para que los workers vean la misma configuración que el proceso principal.
 */
if (process.argv.some((arg) => arg.includes('@escritura'))) process.env['E2E_ESCRITURA'] = '1';
export const ESCRITURA_PERMITIDA = process.env['E2E_ESCRITURA'] === '1';

export function prefijoRol(rol: string): string {
  return `E2E_${rol.toUpperCase().replace(/-/g, '_')}`;
}

export function credenciales(rol: string): { usuario: string; clave: string } | null {
  const pref = prefijoRol(rol);
  const usuario = process.env[`${pref}_USER`];
  const clave = process.env[`${pref}_PASS`];
  return usuario && clave ? { usuario, clave } : null;
}

export function rutaSesion(rol: string): string {
  return path.join(DIR_SESIONES, `${rol}.json`);
}

/** Roles declarados que tienen usuario de prueba; los demás se omiten con aviso. */
export function rolesConUsuario(roles: readonly string[]): string[] {
  const disponibles = roles.filter((rol) => credenciales(rol));
  const omitidos = roles.filter((rol) => !disponibles.includes(rol));
  if (omitidos.length) {
    console.warn(`[e2e] sin usuario de prueba (se omiten sus escenarios): ${omitidos.join(', ')}`);
  }
  return disponibles;
}

/**
 * Un proyecto por rol con usuario. Cada proyecto corre solo los escenarios etiquetados con su rol
 * (`@auditor`), con la sesión guardada por el global-setup, y sin los @escritura salvo que se pidan
 * (ESCRITURA_PERMITIDA).
 *
 * `retries: 1` existe solo para la sesión cerrada a mitad de corrida: el fixture vigilarSesion hace
 * que un reintento por cualquier otra causa falle de inmediato (ver core/fixtures.ts).
 */
export function proyectosPorRol(roles: readonly string[]): Project[] {
  return rolesConUsuario(roles).map((rol) => ({
    name: rol,
    grep: new RegExp(`@${rol}(?![\\w-])`),
    ...(ESCRITURA_PERMITIDA ? {} : { grepInvert: /@escritura(?![\w-])/ }),
    retries: 1,
    use: { storageState: rutaSesion(rol) },
  }));
}
