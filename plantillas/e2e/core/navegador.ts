/**
 * Ajustes del navegador de prueba comunes a los clientes OAS (root + core-mf). No cambian nada del
 * servidor: solo lo que recibe el navegador de la prueba.
 */
import type { BrowserContext, Route } from '@playwright/test';

/**
 * CloudFront a veces sirve el main.js del core-mf de pruebas sin Access-Control-Allow-Origin y el
 * root no carga. Se agrega la cabecera a esas respuestas.
 */
const ORIGENES_SIN_CORS = ['https://pruebascoreclientes.portaloas.udistrital.edu.co/**'];

async function agregarCors(route: Route) {
  const respuesta = await route.fetch();
  await route.fulfill({ response: respuesta, headers: { ...respuesta.headers(), 'access-control-allow-origin': '*' } });
}

export async function prepararContexto(contexto: BrowserContext) {
  for (const origen of ORIGENES_SIN_CORS) {
    await contexto.route(origen, agregarCors);
  }
  // El overlay "Uncaught runtime errors" del dev-server del root (errores de scripts externos) tapa la página.
  await contexto.addInitScript(() => {
    setInterval(() => {
      document.querySelectorAll('[id^="webpack-dev-server-client-overlay"]').forEach((e) => e.remove());
    }, 300);
  });
}
