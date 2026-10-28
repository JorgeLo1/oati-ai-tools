/**
 * `test` extendido del marco. Todo escenario importa `test` y `expect` desde aquí.
 *
 * Automático en cada escenario:
 * - ajustes del navegador (CORS del core-mf, overlay del dev-server);
 * - con la etiqueta @lectura, aborta toda escritura (POST/PUT/PATCH/DELETE) fuera del root y deja
 *   la lista en el reporte: una corrida de lectura nunca modifica el ambiente de pruebas;
 * - errores de JavaScript de la página adjuntos al reporte.
 *
 * Bajo demanda: `simularGet` reescribe el `Data` de una respuesta GET para preparar un estado sin
 * escribir en el backend. Los escenarios que lo usan llevan la etiqueta @simulado.
 */
import { test as base, expect, type Route } from '@playwright/test';
import { BASE_URL } from './config';
import { prepararContexto } from './navegador';

const ESCRITURAS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

type TransformarData = (data: any[]) => any[];

interface FixturesE2E {
  ajustesNavegador: void;
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
