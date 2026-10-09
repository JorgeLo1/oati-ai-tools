---
name: seguridad-oas
description: Revisión de seguridad previa al PR o a la solicitud de verificación de Seguridad, según el checklist institucional OAS (qa/validación_seguridad.md) — secretos y llaves expuestos, variables de entorno, validación de entradas (DTO, ObjectId, inyección en filtros Mongo, XSS en el MF), autenticación y autorización por rol, exposición de información en APIs (errores, CORS, Swagger), logs, dependencias vulnerables y configuración de SonarQube. Revisa el diff de la rama o el repo completo en MF Angular, MID y CRUD (NestJS/Beego) y entrega el checklist marcado con hallazgos por severidad. Úsala cuando el usuario diga "/seguridad-oas", "revisa la seguridad", "checklist de seguridad", "antes del PR revisa", "vamos a pedir revisión a seguridad".
---

# Seguridad OAS (checklist previo)

Ejecuta el **Checklist 1 — Validación previa del equipo de desarrollo** del lineamiento y anticipa lo que el equipo de Seguridad revisará en el **Checklist 2** (SonarQube, dependencias, authN/authZ, APIs, OWASP Top 10 / API Security Top 10).

Fuente: `qa/validación_seguridad.md` (léela con `gh api "repos/udistrital/lineamientos_oas/contents/qa/validaci%C3%B3n_seguridad.md" -H "Accept: application/vnd.github.raw"` para confirmar que no cambió).

**Esta skill revisa y reporta; no corrige por su cuenta.** Al final ofrece aplicar las correcciones que el usuario elija.

## Paso 0 — Alcance

- Argumento `repo` o `completo` → todo el repositorio. Por defecto → **los cambios de la rama**: `git diff <base>...HEAD` + cambios sin commitear, donde `<base>` es `develop` (o `main`/`master` si no existe).
- Detecta el tipo de proyecto: **MF Angular** (`angular.json`), **API Nest** (`@nestjs/core`), **Beego** (`go.mod`). Si la tarea abarcó varios repos (MF + MID + CRUD), pregunta si se revisan todos y repite por repo.
- Lista los archivos del alcance (`git diff --name-only <base>...HEAD; git status --porcelain`), excluyendo lockfiles, `dist/`, `node_modules/`, assets binarios.

## 1. Secretos y llaves (bloqueante si hay hallazgo)

1. Archivos que no deben versionarse:
   ```bash
   git ls-files | grep -Ei '(^|/)\.env($|\.)|\.pem$|\.key$|\.p12$|\.pfx$|id_rsa|credentials|\.keystore$' | grep -v '\.example$'
   ```
   Y que `.gitignore` cubra `.env*`.
2. Patrones en el alcance (y en los commits de la rama: `git log -p <base>..HEAD`):
   ```bash
   git grep -nEI '(password|passwd|pass|secret|token|api[_-]?key|client[_-]?secret|authorization|bearer)\s*[:=]\s*["'\''][^"'\''$\{]{6,}' -- . ':!*.lock' ':!*lock.yaml' ':!*.spec.ts'
   git grep -nEI 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.|mongodb(\+srv)?://[^$\{ ]+:[^$\{ ]+@|postgres://[^$\{ ]+:[^$\{ ]+@'
   ```
   Si `gitleaks` está instalado, úsalo además (`gitleaks detect --no-banner --log-opts="<base>..HEAD"`).
3. En el **MF**, `src/environments/*.ts` va al navegador: sólo URLs públicas e IDs; nunca client secrets, tokens o credenciales.
4. Si un secreto llegó a un commit (aunque ya se haya borrado), el hallazgo es **crítico**: hay que **rotarlo**; borrarlo del código no basta.

## 2. Variables de entorno y configuración

- Credenciales, hosts y puertos por variables de entorno (Nest: `ConfigService`/`configuration.ts`; Beego: `${VAR}` en `app.conf`), con nombres `<NOMBRE_API>_<PARAMETRO>` en mayúsculas. Nada de `localhost`, IPs internas o credenciales fijas en el código.
- Variables nuevas documentadas (README / `.env.example`) sin valores reales.
- En producción: `NODE_ENV=production`, Swagger y modos debug condicionados por ambiente cuando corresponda (anótalo como observación si están siempre expuestos).

## 3. Validación de entradas

**Backend (Nest)**
- Cada `@Body`, `@Param`, `@Query` nuevo tiene DTO o validación explícita; ids Mongo validados (`ParseObjectIdPipe`/`isValid`) antes de consultar. `@Body() body: any` que se pasa directo a `create`/`findByIdAndUpdate` permite **inyección de operadores** (`{"$set": …}`, `{"activo": {"$ne": false}}`) y *mass assignment* (sobrescribir `fecha_creacion`, `activo`, `estado_id`): señálalo.
- Filtros construidos desde el query string: entrada del usuario usada en `new RegExp(...)` sin escapar (búsquedas `__icontains`/`__contains`) permite ReDoS o patrones arbitrarios → recomendar escapar (`s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')`). Revisa también `$where`, `eval`, `Function(`.
- Archivos subidos (base64/multipart): tipo MIME y tamaño validados en el servidor.

**Beego**: parámetros parseados con manejo de error; nada de SQL concatenado con entrada del usuario (usar el ORM o parámetros).

**MF Angular**
- Formularios con `Validators` coherentes con lo que el backend exige.
- XSS: `[innerHTML]`, `bypassSecurityTrust*`, `DomSanitizer`, `document.write`, `eval`, `insertAdjacentHTML`, `nativeElement.innerHTML` con datos del usuario o del backend. Texto enriquecido (editores, imágenes embebidas) debe sanearse antes de renderizar o al guardar.
- URLs construidas con entrada del usuario (`window.open`, `href`) sin validar el esquema (`javascript:`).

## 4. Autenticación y autorización

- **MF**: rutas nuevas protegidas con el guard del proyecto; acciones por rol definidas en la matriz/config del proyecto. Recuerda: **ocultar un botón no es control de acceso**; si el backend no valida, es un hallazgo.
- **MID/CRUD**: identifica dónde se valida la identidad (gateway/WSO2, guard, middleware). Si los endpoints no validan nada y dependen del gateway, anótalo como observación para confirmar con infraestructura.
- Para transiciones de estado y operaciones sensibles en el MID: ¿se verifica que el `usuario_rol`/`usuario_id` enviado tenga permiso y que el estado actual permita la transición? Un body controlado por el cliente que decide rol o estado sin verificación es **escalamiento de privilegios**.
- **Acceso a recursos de otros usuarios (IDOR)**: endpoints con `:personaId`, `:id` que devuelven datos sin comprobar pertenencia.

## 5. Exposición de información en APIs

- Mensajes de error: no devolver stack traces, `error.message` de Mongo/Axios con URLs internas, nombres de colecciones o consultas. Mensaje genérico al cliente y detalle en el log.
- Respuestas sin campos sensibles innecesarios (documentos de identidad completos, correos de terceros, tokens).
- CORS: `app.enableCors()` sin opciones permite cualquier origen → observación (restringir a los dominios del sistema por ambiente).
- Métodos HTTP: `GET` que modifica datos, `DELETE` físico donde se espera lógico.
- Rate limiting / tamaño máximo de body en endpoints costosos (cargue masivo, exportaciones, plantillas) → observación si aplica.

## 6. Logs

Sin contraseñas, tokens, cabeceras `Authorization`, documentos en base64 ni datos personales completos. Revisa `console.log` nuevos con objetos completos de request/response.

## 7. Dependencias

```bash
pnpm audit --prod         # o npm audit --omit=dev, según lockfile
govulncheck ./...         # Go, si está instalado
```

Requiere red: si falla, dilo y deja el comando para que el usuario lo ejecute. Reporta sólo vulnerabilidades **altas/críticas** de dependencias de producción, con la versión que las corrige y si la actualización es mayor (riesgo de romper). Si el diff agrega dependencias nuevas, verifica que sean mantenidas y necesarias.

## 8. SonarQube y calidad

- Existe `sonar-project.properties` con `sonar.projectKey`, `sonar.sources`, exclusiones (`node_modules`, `dist`, `**/*.spec.ts`) y, si hay cobertura, la ruta del lcov. **No ejecutes `sonar-scanner`** (envía el código al servidor): sólo indica si la configuración está completa.
- `pnpm build` y `pnpm lint` pasan (reporta resultado real; si `lint`/`test` ya estaban rotos antes del cambio, dilo).

## 9. Documentación para la entrega a Seguridad

Verifica si existen (o qué falta) los insumos que Seguridad pide: nombre de la aplicación, URL de pruebas, repositorio(s) y ramas, **diagrama/documento de arquitectura**, usuarios/roles de prueba, tecnologías, **Swagger/OpenAPI** de las APIs, manuales/instructivos.

## Salida

Escribe el informe en el chat y guárdalo en `.claude/docs/seguridad/<rama-sin-prefijo>.md` (local, no versionado; crea la carpeta si no existe):

```markdown
# Revisión de seguridad — <repo> · <rama> · <AAAA-MM-DD>
Alcance: <diff vs base | repo completo> · Archivos revisados: N

## Resultado preliminar: Aprobado | Aprobado con observaciones | No aprobado

## Checklist 1 (lineamiento OAS)
| Ítem | Estado | Evidencia |
|---|---|---|
| Código en el repositorio de la universidad | ✅/❌ | remote |
| Sin contraseñas, tokens, API keys o secretos | ✅/⚠️/❌ | archivo:línea |
| Sin llaves privadas o certificados expuestos | | |
| Pruebas funcionales realizadas | | (preguntar/derivar de la sesión) |
| Formularios y entradas validados | | |
| Validación de autenticación | | |
| Validación de usuarios | | |
| Validación de roles y permisos | | |
| Variables de entorno configuradas correctamente | | |
| Arquitectura documentada | | |
| APIs documentadas (Swagger) | | |

## Hallazgos
| # | Severidad | Categoría | Archivo:línea | Descripción | Recomendación |
|---|---|---|---|---|---|

## Dependencias
## Insumos faltantes para la entrega a Seguridad
```

Severidad y criterio de bloqueo (según el lineamiento):
- **Crítica** (bloquea): secretos/credenciales expuestos, falla grave de autenticación/autorización, inyección explotable.
- **Alta** (bloquea si es explotable y expuesta): IDOR, escalamiento de privilegios, XSS almacenado, dependencia crítica en producción.
- **Media**: validación incompleta, errores que filtran detalles internos, CORS abierto, mass assignment no explotado.
- **Baja / observación**: logs mejorables, Swagger expuesto, falta de rate limit, documentación faltante.

Distingue lo **introducido por el cambio** de lo **preexistente** (marca preexistentes aparte para no bloquear la tarea por deuda ajena, pero sí reportarlos).

Al final pregunta qué hallazgos corregir. No hagas commits: tras corregir, sugiere `/commit-oas`.
