/**
 * Alertas SweetAlert2 de los clientes OAS en los flujos que escriben: una acción puede encadenar
 * una confirmación ("¿Está seguro…?"), una espera (firma, generación de PDF) y el resultado.
 */
import { expect, type Page } from '@playwright/test';

/**
 * Atiende las alertas que dispara una acción hasta el resultado: confirma las preguntas (las que
 * tienen botón de cancelar), falla de inmediato si la aplicación muestra un error y cierra el aviso
 * final. Devuelve el texto de cada alerta, en orden.
 *
 * `hasta`: texto del aviso final cuando la aplicación encadena varios avisos de éxito (p. ej.
 * "Archivo subido exitosamente." y, al cerrarlo, sigue el proceso y avisa "Plan aprobado
 * exitosamente."). Sin `hasta`, termina en el primer aviso que no es pregunta.
 *
 * Errores: SweetAlert2 v11 marca el tipo en el propio popup (`.swal2-popup.swal2-icon-error`); el
 * ícono es `.swal2-icon.swal2-error`. Buscar `.swal2-icon-error` dentro del popup no encuentra nada.
 */
export async function resolverAlertas(
  page: Page,
  { timeout = 180_000, maxPreguntas = 3, hasta }: { timeout?: number; maxPreguntas?: number; hasta?: RegExp } = {},
): Promise<string[]> {
  const alerta = page.locator('.swal2-popup');
  const textos: string[] = [];
  const limite = Date.now() + timeout;
  while (textos.length <= maxPreguntas + 3) {
    if (Date.now() > limite) break;
    await expect(alerta).toBeVisible({ timeout });
    // Las alertas de carga muestran "Aceptar" deshabilitado (o sin botones) hasta que la operación
    // termina y se reemplazan solas: se espera a un botón visible y habilitado.
    const boton = alerta.locator('.swal2-confirm:not([disabled]), .swal2-cancel:not([disabled])').filter({ visible: true }).first();
    await expect(boton).toBeVisible({ timeout });
    await expect(alerta.locator('.swal2-loader')).toBeHidden({ timeout });
    const texto = (await alerta.innerText()).replace(/\s+/g, ' ').trim();
    // SweetAlert2 v11 marca el tipo en el propio popup (swal2-icon-error); el ícono es .swal2-icon.swal2-error.
    if (/\bswal2-icon-error\b/.test((await alerta.getAttribute('class')) ?? '')) {
      throw new Error(`la aplicación respondió con un error: "${texto}"`);
    }
    const esPregunta = await alerta.locator('.swal2-cancel').isVisible();
    // La aplicación puede reemplazar la alerta (p. ej. por una de carga) entre la lectura y el clic: si
    // "Aceptar" ya no se puede pulsar, se vuelve a leer la alerta que quedó en pantalla.
    const pulsado = await alerta.locator('.swal2-confirm').click({ timeout: 5_000 }).then(() => true, () => false);
    if (!pulsado) continue;
    textos.push(texto);
    if (!esPregunta && (!hasta || hasta.test(texto))) {
      await expect(alerta).toBeHidden();
      return textos;
    }
  }
  throw new Error(`demasiadas alertas seguidas sin llegar al resultado: ${textos.join(' | ')}`);
}
