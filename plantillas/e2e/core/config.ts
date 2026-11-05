/**
 * Núcleo genérico del marco E2E (no depende del proyecto): lectura de variables, roles con
 * usuario y construcción de un proyecto de Playwright por rol.
 *
 * Convención común a todos los proyectos udistrital:
 *   E2E_BASE_URL                 URL del root que compone los MF (por defecto http://localhost:4200)
 *   E2E_AMBIENTE=<nombre>        corre contra E2E_BASE_URL_<NOMBRE> (p. ej. pruebas → E2E_BASE_URL_PRUEBAS)
 *                                sin editar .env.e2e; sus sesiones quedan aparte en .auth/<nombre>/
 *   E2E_<ROL>_USER / _PASS       usuario de prueba dedicado por rol (jefe-dependencia → JEFE_DEPENDENCIA)
 *   E2E_ESCRITURA=1              permite correr escenarios @escritura (o pasar --grep @escritura)
 */
import path from 'node:path';
import type { Project } from '@playwright/test';

export const RAIZ_E2E = path.resolve(__dirname, '..');

// Local: lee e2e/.env.e2e si existe (Node >= 20.12); no pisa las variables que ya trae el entorno.
// En CI las variables llegan como secrets.
try {
  process.loadEnvFile(path.join(RAIZ_E2E, '.env.e2e'));
} catch {
  /* sin archivo: se usan las variables del entorno */
}

/** Ambiente elegido con E2E_AMBIENTE (minúsculas, con "-"); vacío = el de E2E_BASE_URL. */
export const AMBIENTE = (process.env['E2E_AMBIENTE'] || '').trim().toLowerCase();

function urlDelAmbiente(): string {
  if (!AMBIENTE) return process.env['E2E_BASE_URL'] || 'http://localhost:4200';
  if (!/^[a-z0-9-]+$/.test(AMBIENTE)) throw new Error(`[e2e] E2E_AMBIENTE inválido: "${AMBIENTE}" (solo letras, números y "-")`);
  const variable = `E2E_BASE_URL_${AMBIENTE.toUpperCase().replace(/-/g, '_')}`;
  const url = process.env[variable];
  if (!url) throw new Error(`[e2e] E2E_AMBIENTE=${AMBIENTE} pide ${variable}, que no está en e2e/.env.e2e ni en el entorno`);
  return url;
}

export const BASE_URL = urlDelAmbiente().replace(/\/$/, '');

/** Sesiones por ambiente: al cambiar de ambiente no se pisan ni obligan a repetir los logins. */
export const DIR_SESIONES = AMBIENTE ? path.join(RAIZ_E2E, '.auth', AMBIENTE) : path.join(RAIZ_E2E, '.auth');

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
