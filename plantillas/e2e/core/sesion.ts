/**
 * Sesión del login institucional (OIDC con WSO2) por rol: cuándo se reutiliza y cómo se renueva.
 *
 * El core-mf cierra la sesión al abrir el root si el token venció (`expires_at`) o si pasaron 15 min
 * 30 s sin actividad del usuario (`core_last_activity`, que solo se actualiza con teclado o mouse).
 * WSO2 también puede cerrarla del lado del servidor. Por eso:
 * - el global-setup reutiliza la sesión guardada solo si cumple esas dos reglas, con margen;
 * - cada escenario que pasa guarda el estado del navegador (la app ya actualizó su actividad);
 * - si el root termina en WSO2 a mitad de corrida, el fixture vigilarSesion renueva y reintenta.
 *
 * El login corre siempre en un proceso de Node aparte (core/login.mjs): ni trazas ni la
 * configuración del proyecto alcanzan al navegador donde se escribe la contraseña.
 * Si WSO2 rechaza las credenciales NO se reintenta (la cuenta se bloquea tras varios intentos);
 * solo una falla transitoria (red, tiempo agotado) se reintenta una vez.
 */
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { BASE_URL, DIR_SESIONES, RAIZ_E2E, credenciales, prefijoRol, rutaSesion } from './config';

/** Host del servidor de autenticación: si el root termina aquí, la sesión no sirve. */
export const HOST_AUTENTICACION = 'autenticacion.portaloas.udistrital.edu.co';
/** Claves de localStorage que deja el core-mf con la sesión completa (se ajustan en playwright.config). */
export const CLAVES_SESION_POR_DEFECTO = ['id_token'];
/** Inactividad tras la que el core-mf cierra la sesión (15 min 30 s), y margen de seguridad. */
const INACTIVIDAD_MS = 15 * 60 * 1000 + 30 * 1000;
const MARGEN_MS = 2 * 60 * 1000;
const CLAVE_ACTIVIDAD = 'core_last_activity';

export function esPaginaAutenticacion(url: string): boolean {
  try {
    return new URL(url).hostname === HOST_AUTENTICACION;
  } catch {
    return false;
  }
}

function leerLocalStorage(ruta: string): Map<string, string> | null {
  try {
    const estado = JSON.parse(fs.readFileSync(ruta, 'utf-8'));
    const origen = estado.origins?.find((o: { origin: string }) => o.origin === new URL(BASE_URL).origin);
    return new Map((origen?.localStorage ?? []).map((i: { name: string; value: string }) => [i.name, i.value]));
  } catch {
    return null;
  }
}

/** La sesión guardada pasaría las mismas reglas del core-mf al abrir el root (con margen). */
export function sesionReutilizable(ruta: string, ahora = Date.now()): boolean {
  const ls = leerLocalStorage(ruta);
  if (!ls) return false;
  const expira = Date.parse(ls.get('expires_at') ?? '');
  if (!Number.isFinite(expira) || expira - ahora <= MARGEN_MS) return false;
  const actividad = Number(ls.get(CLAVE_ACTIVIDAD));
  if (Number.isFinite(actividad) && actividad > 0 && actividad + INACTIVIDAD_MS - ahora <= MARGEN_MS) return false;
  return true;
}

/**
 * Login nuevo del rol (proceso aparte) y sesión guardada en .auth/<rol>.json.
 * Reintenta una vez solo si la falla fue transitoria; con credenciales rechazadas se detiene.
 */
export function renovarSesion(rol: string, claves = CLAVES_SESION_POR_DEFECTO): void {
  if (!credenciales(rol)) throw new Error(`[e2e] sin usuario de prueba para el rol ${rol} (${prefijoRol(rol)}_USER/_PASS)`);
  fs.mkdirSync(DIR_SESIONES, { recursive: true });
  const ruta = rutaSesion(rol);
  const script = path.join(RAIZ_E2E, 'core', 'login.mjs');

  for (let intento = 1; intento <= 2; intento++) {
    const r = spawnSync(process.execPath, [script, rol, BASE_URL, ruta, claves.join(',')], {
      cwd: RAIZ_E2E,
      env: process.env,
      encoding: 'utf-8',
      timeout: 4 * 60 * 1000,
    });
    if (r.status === 0) return;
    const causa = (r.stderr || r.error?.message || 'sin detalle').trim().split('\n').pop();
    if (r.status === 2) {
      throw new Error(
        `[e2e] login del rol ${rol} rechazado: ${causa}. No se reintenta para no bloquear la cuenta en WSO2; ` +
          `revisa ${prefijoRol(rol)}_USER/_PASS en e2e/.env.e2e o el estado de la cuenta.`,
      );
    }
    if (intento === 2) {
      throw new Error(`[e2e] falló el login del rol ${rol} dos veces (${causa}). Revisa la VPN y que el root cargue.`);
    }
    console.warn(`[e2e] ${rol}: falla transitoria en el login (${causa}); se reintenta una vez`);
  }
}

/** Marca que deja el fixture cuando renovó la sesión de un rol a mitad de corrida (habilita el reintento). */
export function rutaMarcaRenovada(rol: string): string {
  return `${rutaSesion(rol)}.renovada`;
}
