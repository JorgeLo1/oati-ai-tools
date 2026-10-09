---
name: endpoint-oas
description: Diseña o revisa endpoints REST de APIs udistrital (CRUD y MID en NestJS, también Beego) según el lineamiento OAS de endpoints y de versionado — URI en español, kebab-case, sin verbos CRUD, verbo HTTP y status code correctos, envoltura de respuesta, decoradores Swagger, impacto en los consumidores (MF/MID) y qué parte de la versión SemVer subir. Úsala cuando el usuario diga "/endpoint-oas", "crea/agrega un endpoint", "revisa el endpoint", "cómo debería llamarse esta ruta", "nuevo servicio en el mid/crud", o antes de agregar o cambiar un @Controller/@Get/@Post/@Put/@Patch/@Delete o un @router de Beego.
---

# Endpoints OAS (diseño y revisión)

Aplica los lineamientos institucionales a la **definición de endpoints**. Sirve en dos modos:

- **Diseñar**: el usuario describe qué necesita ("un servicio que devuelva las acciones de un plan con su estado") → propones la ruta, verbo, parámetros, respuesta y decoradores, y luego la implementas (con `/crud-oas` o `/mid-oas` si aplica).
- **Revisar**: sobre endpoints existentes o un diff → reportas incumplimientos y propones correcciones.

Fuentes (léelas con `gh api repos/udistrital/lineamientos_oas/contents/<ruta> -H "Accept: application/vnd.github.raw"` si necesitas confirmar un detalle o si sospechas que cambiaron):

- `generacion_de_apis/lineamientos-endpoints.md` — nombrado de recursos, verbos, status codes.
- `generacion_de_apis/versionado-apis-XYZ.md` — SemVer.
- `api_nest/refactorizacion.md` — estructura de respuesta en Nest.

## Paso 0 — Conocer el repo antes de opinar

1. Identifica el tipo de API: **CRUD** (persistencia, `MongooseModule`/`schema`) o **MID** (lógica de negocio que llama a otros servicios con `HttpService`), y el framework (NestJS: `@Controller`; Beego: `// @router`).
2. Lista las rutas existentes para aprender la convención **real** del repo:
   - Nest: `grep -rn "@Controller\|@Get\|@Post\|@Put\|@Patch\|@Delete" src --include=*.controller.ts`
   - Beego: `grep -rn "@router" controllers`
3. **Regla de coherencia**: el lineamiento pide "ser coherente". Si el repo ya tiene una convención consistente que difiere del ejemplo del lineamiento (p. ej. recursos en **singular** que reflejan la colección `accion_mejora_estado` → `/accion-mejora-estado`, o parámetros `:personaId`), los endpoints **nuevos** siguen la convención del repo y lo mencionas. Nunca propongas renombrar endpoints existentes sin evaluar consumidores (Paso 5) y sin que el usuario lo pida: es un cambio incompatible (MAJOR).

## Paso 1 — Reglas de la URI

| Regla | Mal | Bien |
|---|---|---|
| Términos en **español**, sin ñ ni tildes | `/users`, `/año`, `/auditoría` | `/usuarios`, `/anio`, `/auditoria` |
| **Minúsculas** y `-` como separador (nunca `_` ni camelCase en segmentos) | `/planMejoramiento`, `/plan_mejoramiento` | `/plan-mejoramiento` |
| **Sin verbos CRUD** en la URI (el verbo es el método HTTP) | `/crear-plan`, `/traer-planes`, `/actualizar-plan/5`, `/eliminar-plan/5`, `/obtener-…`, `/listar-…`, `/consultar-…` | `POST /planes`, `GET /planes`, `PUT /planes/5`, `DELETE /planes/5` |
| Jerarquía con `/` | `/auditoria-hallazgos?auditoria=5` (si es sub-recurso) | `/auditoria/5/hallazgo` |
| Filtros, paginado y búsqueda como **query params**, no como segmentos | `/usuarios/pagina/1`, `/usuarios/genero/fem` | `/usuarios?pagina=1`, `/usuarios?genero=fem` |
| Sin `/` final ni extensiones | `/planes/`, `/planes.json` | `/planes` |
| Sin palabras clave/ambiguas ni redundancia | `/todos-likes`, `/mis-amigos`, `/plan/plan-detalle` | `/likes`, `/amigos`, `/plan/5/detalle` |
| Plural o singular **consistente** en todo el repo | mezcla `/auditorias` y `/plan` | según la convención del repo |

**Acciones de negocio que no son CRUD** (sólo MID): el lineamiento distingue *documentos, colecciones, almacenes y controladores*. Una operación de proceso que no encaja como recurso (generar, firmar, aprobar, exportar, remitir) puede modelarse como **recurso controlador** colgado del recurso afectado y con `POST`: `POST /plan-auditoria/:id/generar-auditorias`, `POST /cargue-masivo/exportar-excel`. Prefiere primero modelarla como recurso (`POST /plan/:id/aprobacion`), y si no, el verbo de negocio en infinitivo — nunca un verbo CRUD.

**Parámetros de ruta**: sólo identificadores (`:id`, `:planId`). El lineamiento ilustra `{usuario-id}`; en Nest usa el estilo que ya tenga el repo (`:personaId`). Valida ObjectId en el CRUD (pipe `ParseObjectIdPipe` o equivalente).

## Paso 2 — Verbo HTTP

| Verbo | Uso | Body | Idempotente |
|---|---|---|---|
| `GET` | Consultar (colección o uno). **Nunca** modifica estado | No | Sí |
| `POST` | Crear un recurso o ejecutar una acción de negocio | Sí | No |
| `PUT` | Reemplazar/actualizar un recurso existente por id | Sí | Sí |
| `PATCH` | Actualización parcial | Sí | — |
| `DELETE` | Eliminar (en OAS suele ser **lógico**: `activo=false`) | No | Sí |

Errores típicos a detectar: `GET` con body o que crea/actualiza; `POST` para consultar con filtros (usar query params; si el filtro es enorme, documentar por qué se usa `POST`); `PUT` sin id en la ruta; borrar físicamente cuando el resto del repo borra lógico.

## Paso 3 — Status codes y respuesta

- **2xx**: `200` consulta/actualización/borrado exitoso, `201` creación. **Una lista vacía es `200` con `Data: []`**, no `404`.
- **4xx**: `400` parámetros o body inválidos (incluye ObjectId mal formado), `404` el recurso pedido por id no existe, `401/403` auth (si aplica).
- **5xx**: falla del servidor o de un servicio externo del que depende el MID (`502` si es el externo, `500` si es propio).
- Mensajes de error **legibles y útiles**, en el idioma que ya use el repo (en SISIFO, español: `"Error en servicio GetAll: la peticion contiene un parametro incorrecto o no existe un registro"`).

**Envoltura de respuesta** (lineamiento `api_nest/refactorizacion.md`; mantener las mayúsculas que use el repo):

```json
{ "Success": true, "Status": 200, "Message": "Peticion Exitosa", "Data": [ ... ], "MetaData": { "Count": 42 } }
```

- CRUD: el controller arma la envoltura (`res.status(...).json({...})`). `MetaData.Count` en el `GET` de colección si el repo lo usa.
- MID: normalmente reenvía/compone la respuesta del CRUD; si construye la suya, usa la misma envoltura. Errores con excepciones de Nest (`BadRequestException`, `NotFoundException`, `HttpException`) para que el filtro global los formatee.

## Paso 4 — Documentación Swagger (obligatoria)

Cada endpoint nuevo o modificado lleva:

```ts
@ApiTags('<recurso>')                         // en la clase
@ApiOperation({ summary: '<qué hace, en español>' })
@ApiParam({ name: 'id', type: 'string', description: '...' })   // por cada :param
@ApiQuery({ name: '...', required: false, description: '...' }) // query params propios (FilterDto ya se documenta solo)
@ApiBody({ type: <Dto> })                     // o schema inline si no hay DTO
@ApiResponse({ status: HttpStatus.OK, description: '...', type: <Dto> })
@ApiResponse({ status: HttpStatus.BAD_REQUEST, description: '...' })
@ApiResponse({ status: HttpStatus.NOT_FOUND, description: '...' })
```

En Beego: comentarios `@Title`, `@Description`, `@Param`, `@Success`, `@Failure`, `@router /ruta [verbo]`.

## Paso 5 — Impacto en consumidores

Antes de **cambiar o eliminar** un endpoint (ruta, verbo, params, forma de `Data`), busca quién lo usa:

```bash
# desde la carpeta que agrupa los repos (p. ej. `<UDISTRITAL>/SISIFO`; `<UDISTRITAL>` = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/oas_config.py" udistrital`)
grep -rn "'<ruta>'\|\"<ruta>\"\|/<ruta>" --include=*.ts --include=*.go Frontend Backend | grep -v node_modules | grep -v dist
```

En los MF de SISIFO las llamadas son del tipo `this.planAuditoriaService.get('plan-mejoramiento-estado', ...)` y la base URL viene de `environment` (`PLAN_ANUAL_AUDITORIA_SERVICE`, `PLAN_ANUAL_AUDITORIA_MID`). Lista cada consumidor con `archivo:línea` y qué se rompe.

## Paso 6 — Versionado (SemVer, lineamiento OAS)

Clasifica el cambio y di qué versión corresponde (la versión de la API está en `DocumentBuilder().setVersion(...)` de `main.ts` en Nest; en Beego en el README/tag):

| Cambio | Nivel |
|---|---|
| Quitar/renombrar endpoint, cambiar verbo, cambiar forma de `Data`, volver obligatorio un campo, cambiar significado de un status | **MAJOR** (incompatible) |
| Endpoint nuevo, campo opcional nuevo, nuevo filtro | **MINOR** |
| Corrección de bug sin cambiar el contrato | **PATCH** |

Reglas OAS: primera salida a producción `0.1.0`; mientras no sea estable se itera `0.Y.Z`; estable y en uso oficial `1.0.0`; luego SemVer normal. **No edites la versión** por tu cuenta: indícala como recomendación (se ajusta al preparar el `release/`).

## Salida

### Modo diseñar
1. Tabla de endpoints propuestos: `Verbo | Ruta | Params | Query | Body (DTO) | Respuesta Data | Status`.
2. Justificación breve de cada decisión que no sea obvia (recurso vs. controlador, singular/plural por coherencia).
3. Recomendación de versión.
4. Tras confirmación del usuario, implementar (con `/crud-oas` o `/mid-oas` si se trata de un recurso o servicio completo).

### Modo revisar
Tabla `Endpoint | Archivo:línea | Regla incumplida | Severidad | Propuesta` con severidad:
- **Alta**: verbo que no corresponde (GET que modifica), status incorrecto en éxito/error, verbo CRUD en la URI, falta de validación de id.
- **Media**: nombrado (`_`, camelCase, inglés, tildes), filtros como segmento, falta Swagger.
- **Baja**: mensajes poco claros, inconsistencias menores.

Luego: consumidores afectados por cada propuesta y nivel de versión. No apliques renombres de rutas existentes sin confirmación explícita.

No hagas commits: al terminar sugiere `/commit-oas`.
