/**
 * Root de SISIFO (core-mf): encabezado, menú lateral y el contenedor donde se monta el MF.
 */
import { expect, type Locator, type Page } from '@playwright/test';
import { BasePage } from '../core/base.page';

export class ShellPage extends BasePage {
  readonly menuLateral: Locator;
  readonly botonAbrirMenu: Locator;
  /** Título de la pantalla del MF (plantilla-tarjeta-contenedora). */
  readonly tituloPantalla: Locator;

  constructor(page: Page) {
    super(page);
    this.menuLateral = page.locator('#sidebar');
    this.botonAbrirMenu = page.locator('.menu-icon', { hasText: /^\s*menu\s*$/ });
    this.tituloPantalla = page.locator('plantilla-tarjeta-contenedora h2').first();
  }

  async abrirInicio() {
    await this.page.goto('/');
    await expect(this.page.locator('.menu-icon').first()).toBeVisible({ timeout: 60_000 });
  }

  /**
   * Nodo del menú (ng-uui-menu) cuyo nombre es exactamente `nombre`, buscado dentro de `ambito`.
   * Se busca por nodo y no solo por texto porque hay nombres repetidos en ramas distintas
   * (p. ej. "Auditorías Internas" en Planeación y en Ejecución).
   */
  private nodoMenu(ambito: Locator, nombre: string): Locator {
    const exacto = new RegExp(`^\\s*${nombre.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*$`);
    return ambito
      .locator('ng-uui-menu')
      .filter({ has: this.page.locator(':scope > mat-list-item .display-name', { hasText: exacto }) })
      .first();
  }

  async abrirMenu() {
    // Una alerta de error de la pantalla anterior tapa el menú: se falla con su texto en vez de esperar el clic.
    // SweetAlert2 v11 marca el tipo en el propio popup (swal2-icon-error).
    if (await this.page.locator('.swal2-popup.swal2-icon-error').isVisible()) {
      throw new Error(`la pantalla mostró un error antes de seguir por el menú: "${await this.textoAlerta()}"`);
    }
    if (await this.botonAbrirMenu.isVisible()) await this.botonAbrirMenu.click();
    await expect(this.menuLateral.locator('mat-list-item').first()).toBeVisible();
  }

  /** Nombres de las opciones de primer nivel del menú, en orden. */
  async nombresMenu(): Promise<string[]> {
    const textos = await this.menuLateral
      .locator(':scope > mat-nav-list > ng-uui-menu > mat-list-item .display-name')
      .allInnerTexts();
    return textos.map((t) => t.trim()).filter(Boolean);
  }

  /** Nombres de las opciones hijas de una rama (la expande si hace falta). */
  async nombresSubmenu(...ruta: string[]): Promise<string[]> {
    const nodo = await this.expandir(ruta);
    const textos = await nodo.locator(':scope > .sub-menu > ng-uui-menu > mat-list-item .display-name').allInnerTexts();
    return textos.map((t) => t.trim()).filter(Boolean);
  }

  /** Expande cada rama de la ruta (sin cerrar las que ya están abiertas) y devuelve el último nodo. */
  private async expandir(ruta: string[]): Promise<Locator> {
    await this.abrirMenu();
    let ambito = this.menuLateral;
    let nodo = ambito;
    for (const nombre of ruta) {
      nodo = this.nodoMenu(ambito, nombre);
      const submenu = nodo.locator(':scope > .sub-menu');
      if (!(await submenu.isVisible())) {
        await nodo.locator(':scope > mat-list-item').click();
        await expect(submenu).toBeVisible();
      }
      ambito = submenu;
    }
    return nodo;
  }

  /** Recorre el menú por nombres hasta la opción final (p. ej. 'Planes de Mejoramiento', 'Gestión de Acciones'). */
  async navegarPorMenu(...ruta: string[]) {
    const padre = ruta.length > 1 ? (await this.expandir(ruta.slice(0, -1))).locator(':scope > .sub-menu') : this.menuLateral;
    if (ruta.length === 1) await this.abrirMenu();
    await this.nodoMenu(padre, ruta[ruta.length - 1]).locator(':scope > mat-list-item').click();
  }
}
