// spec: e2e/specs/navegacion.plan.md
// Escenario semilla: cada rol con usuario inicia sesión y ve su menú. Sirve de punto de partida para
// generar escenarios con playwright-cli (--debug=cli) y para comprobar que el login funciona.
import { test, expect } from '../../core/fixtures';
import { ShellPage } from '../../pages/shell.page';
import { ROLES } from '../../playwright.config';

for (const rol of ROLES) {
  test(`${rol} inicia sesión y ve su menú`, { tag: ['@navegacion', `@${rol}`, '@lectura'] }, async ({ page, escriturasBloqueadas }, testInfo) => {
    const shell = new ShellPage(page);
    await shell.abrirInicio();
    await shell.abrirMenu();
    const opciones = await shell.nombresMenu();
    await testInfo.attach('menú', { body: await page.screenshot(), contentType: 'image/png' });
    // Reemplazar por las opciones esperadas del rol (ver specs/navegacion.plan.md).
    expect(opciones.length).toBeGreaterThan(0);
    expect(escriturasBloqueadas).toEqual([]);
  });
}
