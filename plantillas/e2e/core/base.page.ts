/**
 * Clase base de los page objects. Cada pantalla del proyecto extiende BasePage y expone sus
 * elementos y acciones con nombres del negocio; los escenarios no usan selectores directamente.
 */
import { expect, type Locator, type Page } from '@playwright/test';

export abstract class BasePage {
  constructor(readonly page: Page) {}

  /** Navega a una ruta relativa al root y espera el elemento que indica que la pantalla cargó. */
  protected async abrirRuta(ruta: string, listo: Locator) {
    await this.page.goto(ruta);
    await expect(listo).toBeVisible({ timeout: 60_000 });
  }

  // ── Alertas SweetAlert2 (AlertService / ModalService de los clientes OAS) ──────────────────

  get alerta(): Locator {
    return this.page.locator('.swal2-popup');
  }

  async textoAlerta(): Promise<string> {
    await expect(this.alerta).toBeVisible();
    return (await this.alerta.innerText()).replace(/\s+/g, ' ').trim();
  }

  async cancelarAlerta() {
    await this.alerta.locator('.swal2-cancel').click();
    await expect(this.alerta).toBeHidden();
  }

  async confirmarAlerta() {
    await this.alerta.locator('.swal2-confirm').click();
  }

  // ── Diseño responsivo ──────────────────────────────────────────────────────────────────────

  async cambiarAncho(ancho: number, alto = 844) {
    await this.page.setViewportSize({ width: ancho, height: alto });
  }

  /** Ancho real del documento: mayor que el viewport indica desborde horizontal. */
  async anchoDocumento(): Promise<number> {
    return this.page.evaluate(() => document.documentElement.scrollWidth);
  }
}
