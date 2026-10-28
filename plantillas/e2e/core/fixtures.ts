/**
 * `test` extendido del marco. Todo escenario importa `test` y `expect` desde aquí.
 *
 * Automático en cada escenario:
 * - ajustes del navegador (CORS del core-mf, overlay del dev-server);
 * - vigilancia de la sesión: si el root termina en WSO2 (sesión cerrada por inactividad o por el
 *   servidor), el escenario falla de inmediato, se hace un login nuevo del rol y el escenario se
 *   reintenta una vez (solo por esta causa). Si pasa, se guarda el estado del navegador para que la
 *   sesión siga fresca para el siguiente escenario;
 * - con la etiqueta @lectura, aborta toda escritura (POST/PUT/PATCH/DELETE) fuera del root y deja
 *   la lista en el reporte: una corrida de lectura nunca modifica el ambiente de pruebas;
 * - errores de JavaScript de la página adjuntos al reporte.
 *
 * Bajo demanda: `simularGet` reescribe el `Data` de una respuesta GET para preparar un estado sin
 * escribir en el backend. Los escenarios que lo usan llevan la etiqueta @simulado.
 */
import fs from 'node:fs';
import { test as base, expect, type Route } from '@playwright/test';
import { BASE_URL, rutaSesion } from './config';
import { prepararContexto } from './navegador';
import { CLAVES_SESION_POR_DEFECTO, esPaginaAutenticacion, renovarSesion, rutaMarcaRenovada } from './sesion';

const ESCRITURAS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

type TransformarData = (data: any[]) => any[];

interface FixturesE2E {
  ajustesNavegador: void;
  vigilarSesion: void;
  escriturasBloqueadas: string[];
  erroresPagina: void;
  simularGet: (patron: string | RegExp, transformar: TransformarData) => Promise<void>;
}

export const test = base.extend<FixturesE2E>({
  ajustesNavegador: [
    async ({ context }, use) => {
      await prepararContexto(context);
      await use();
    },
    { auto: true },
  ],

  vigilarSesion: [
    async ({ context, page, ajustesNavegador }, use, testInfo) => {
      void ajustesNavegador;
      const rol = testInfo.project.name;
      const marca = rutaMarcaRenovada(rol);
      const claves = (testInfo.config.metadata as { clavesSesion?: string[] })?.clavesSesion ?? CLAVES_SESION_POR_DEFECTO;

      // Un reintento solo procede si el intento anterior falló porque se cerró la sesión.
      if (testInfo.retry > 0) {
        if (!fs.existsSync(marca)) {
          throw new Error('[e2e] no se reintenta: la falla anterior no fue por sesión cerrada (ver el intento 1).');
        }
        fs.rmSync(marca, { force: true });
      }

      // Cualquier navegación de la página hacia WSO2 (logout o login, aunque sea solo una redirección)
      // significa que el root perdió la sesión. Las llamadas a las APIs por el gateway no son navegaciones.
      let sesionCerrada = false;
      page.on('request', (req) => {
        if (!sesionCerrada && req.isNavigationRequest() && req.frame() === page.mainFrame() && esPaginaAutenticacion(req.url())) {
          sesionCerrada = true;
          // Falla rápido: sin esto el escenario esperaría el timeout de cada aserción. Se cierra fuera del
          // evento: dentro de él, la navegación interceptada deja el cierre esperando.
          setTimeout(() => void page.close().catch(() => undefined), 0);
        }
      });

      await use();

      if (sesionCerrada) {
        renovarSesion(rol, claves);
        fs.writeFileSync(marca, new Date().toISOString());
        throw new Error(
          `[e2e] el root cerró la sesión del rol ${rol} (inactividad del core-mf o sesión de WSO2 terminada). ` +
            'Se inició una sesión nueva y el escenario se reintenta.',
        );
      }
      if (testInfo.status === 'passed' && !page.isClosed()) {
        // La aplicación renovó su marca de actividad: se guarda para que el siguiente escenario la reutilice.
        await context.storageState({ path: rutaSesion(rol) });
      }
    },
    { auto: true },
  ],

  escriturasBloqueadas: [
    async ({ context, ajustesNavegador }, use, testInfo) => {
      void ajustesNavegador;
      const bloqueadas: string[] = [];
      if (testInfo.tags.includes('@lectura')) {
        await context.route('**/*', (route: Route) => {
          const req = route.request();
          if (ESCRITURAS.has(req.method()) && !req.url().startsWith(BASE_URL)) {
            bloqueadas.push(`${req.method()} ${new URL(req.url()).pathname}`);
            return route.abort('blockedbyclient');
          }
          return route.fallback();
        });
      }
      await use(bloqueadas);
      if (bloqueadas.length) {
        await testInfo.attach('escrituras bloqueadas', { body: bloqueadas.join('\n'), contentType: 'text/plain' });
      }
    },
    { auto: true },
  ],

  erroresPagina: [
    async ({ page }, use, testInfo) => {
      const errores: string[] = [];
      page.on('pageerror', (e) => errores.push(e.message.split('\n')[0]));
      await use();
      if (errores.length) {
        await testInfo.attach('errores de la página', { body: errores.join('\n'), contentType: 'text/plain' });
      }
    },
    { auto: true },
  ],

  simularGet: async ({ context }, use) => {
    await use(async (patron, transformar) => {
      await context.route(patron, async (route: Route) => {
        if (route.request().method() !== 'GET') return route.fallback();
        const respuesta = await route.fetch();
        const cuerpo = await respuesta.json();
        cuerpo.Data = transformar(Array.isArray(cuerpo.Data) ? cuerpo.Data : []);
        await route.fulfill({ response: respuesta, json: cuerpo });
      });
    });
  },
});

export { expect };
