/**
 * Sesión por rol al inicio de la corrida (ver core/sesion.ts). Para cada rol con usuario se reutiliza
 * la sesión guardada si el core-mf la aceptaría (token vigente y sin inactividad); si no, login nuevo.
 */
import fs from 'node:fs';
import type { FullConfig } from '@playwright/test';
import { DIR_SESIONES, rolesConUsuario, rutaSesion } from './config';
import { CLAVES_SESION_POR_DEFECTO, renovarSesion, rutaMarcaRenovada, sesionReutilizable } from './sesion';

export interface MetadatosE2E {
  /** Roles del proyecto (nombres de los proyectos de Playwright). */
  roles: string[];
  /** Claves de localStorage que indican que la sesión quedó completa. */
  clavesSesion?: string[];
}

export default async function globalSetup(config: FullConfig) {
  const { roles = [], clavesSesion = CLAVES_SESION_POR_DEFECTO } = (config.metadata ?? {}) as Partial<MetadatosE2E>;
  fs.mkdirSync(DIR_SESIONES, { recursive: true });

  for (const rol of rolesConUsuario(roles)) {
    const ruta = rutaSesion(rol);
    fs.rmSync(rutaMarcaRenovada(rol), { force: true });
    if (sesionReutilizable(ruta)) {
      console.log(`[e2e] ${rol}: sesión vigente, se reutiliza`);
      continue;
    }
    if (fs.existsSync(ruta)) console.log(`[e2e] ${rol}: la sesión guardada venció o quedó inactiva, se inicia una nueva`);
    renovarSesion(rol, clavesSesion);
    console.log(`[e2e] ${rol}: sesión iniciada`);
  }
}
