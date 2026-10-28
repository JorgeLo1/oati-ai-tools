# Plan de pruebas — Login por rol y navegación

Issue: <org/repo#N> · MF: <repo> · Etiqueta: `@navegacion`

## Contexto

El root (core-mf) arma el menú lateral con las opciones que la configuración de roles le da al usuario. Los escenarios inician sesión por WSO2 (global-setup) y recorren el menú como lo haría una persona.

Datos: no requieren datos propios. Solo lectura (`@lectura`).

## Escenarios

### 1. <Rol> navega por sus opciones (`@<rol>`)

Archivo: `tests/navegacion/<escenario>.spec.ts`

1. Abrir el root con la sesión del rol.
2. El menú muestra: <opciones de primer nivel>.
3. Para cada opción, navegar desde el menú y verificar la URL y el título de la pantalla:

| Menú | URL | Título |
|---|---|---|
| <Rama › Opción> | `/<ruta>` | <Título> |

Resultado esperado: cada pantalla carga con su título, sin errores de JavaScript y sin escrituras.

Permiso: <opción que el rol NO debe ver>.
