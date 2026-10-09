---
name: crud-oas
description: Crea o modifica recursos en una API CRUD udistrital siguiendo los lineamientos OAS — NestJS + MongoDB (schema, DTO, service, controller con respuesta estándar, module, pruebas) con el lineamiento de modelado Mongo (nombres, tipos, referencias _id, activo/fecha_creacion/fecha_modificacion, índices), y como anexo Beego + PostgreSQL (migraciones, SQL, comentarios). Úsala cuando el usuario diga "/crud-oas", "crea la colección/tabla X", "agrega el campo X al crud", "nuevo recurso en el crud", "modifica el schema", o la tarea implique tocar un *_crud.
---

# CRUD OAS (recursos y modelo de datos)

Implementa recursos de persistencia en APIs CRUD institucionales. El CRUD **no tiene lógica de negocio**: guarda, consulta, actualiza y borra (lógico). Validaciones de existencia de referencias sí; reglas del proceso van en el MID (`/mid-oas`).

Fuentes (léelas con `gh api repos/udistrital/lineamientos_oas/contents/<ruta> -H "Accept: application/vnd.github.raw"` cuando necesites el detalle):

- `api_nest/api_nest.md`, `api_nest/refactorizacion.md`, `api_nest/manejo_error.md`, `api_nest/swagger.md`, `api_nest/variables_entorno.md`
- `modelo_de_datos/lineamientos_mongo.md`
- Beego/Postgres: `generacion_de_apis/beego_migrations.md`, `control_error_json_crud.md`, `variables_en_api.md`, `modelo_de_datos/lineamientos_modelos_relacionales.md`, `modelo_de_datos/guia_de_comentariado.md`

## Paso 0 — Reconocer el repo

1. Stack: `package.json` con `@nestjs/mongoose` → **Nest + Mongo** (secciones 1–6). `go.mod` con `beego` → **Anexo Beego**.
2. Gestor de paquetes por lockfile (`pnpm-lock.yaml` → `pnpm`, `package-lock.json` → `npm`). Node con `nvm use` si hay `.nvmrc`.
3. Toma como **plantilla un recurso existente parecido** y copia su estilo exacto (carpeta `schema/` vs `schemas/`, mensajes, uso de `@Res()`, `FilterDto`, `FiltersService`, pipes). La coherencia con el repo prima sobre los ejemplos genéricos del lineamiento; si el repo se desvía del lineamiento en algo importante, menciónalo sin refactorizar lo existente.
4. Si el cambio expone o modifica endpoints, valida rutas con las reglas de `/endpoint-oas`.

## 1. Modelado (lineamiento Mongo)

Antes de escribir código, presenta al usuario el modelo propuesto y confírmalo:

| Elemento | Regla |
|---|---|
| Colección | **español, singular, snake_case**, descriptiva, 10–30 caracteres, sin redundancia: `accion_mejora_estado`, `plan_mejoramiento` |
| Campos | español, singular, snake_case, sin tildes ni ñ (`anio`, no `año`) |
| Referencia a otra colección (1 a muchos) | `ObjectId` llamado **`<coleccion>_id`**: `plan_mejoramiento_id` con `ref` al schema |
| Referencia a otro sistema (parámetros, terceros, oikos) | número llamado `<entidad>_id`: `estado_id`, `usuario_id`, `vigencia_id` |
| Relación 1 a pocos | **embebido** (subdocumento o arreglo) en vez de colección aparte |
| Campos obligatorios en colecciones no paramétricas | `activo: boolean` (default `true`), `fecha_creacion: Date`, `fecha_modificacion: Date` (= `fecha_creacion` al crear) |
| Tipos | `string`, `number` (int/double), `boolean`, `Date`, arreglos, objetos embebidos, `ObjectId`. Moneda/porcentaje: `number` y documenta la escala |
| Índices | según las **consultas más frecuentes** (lo que el MID/MF filtra con `query=`): simples o compuestos, p. ej. `{ plan_mejoramiento_id: 1, activo: 1 }` |
| Historial de estados | colección `<recurso>_estado` con `<recurso>_id`, `estado_id`, `usuario_id`, `usuario_rol`, `observacion`, `actual`, `fecha_ejecucion_estado`, `activo` (patrón de SISIFO) |

Diseña pensando en las consultas: si siempre se lee junto, embébelo o denormaliza (documentándolo en un comentario, como el `estado_id` vigente copiado en la acción de mejora).

## 2. Archivos del recurso (Nest)

Estructura (kebab-case en archivos y carpeta; ajusta `schema/` o `schemas/` según el repo):

```
src/<recurso>/
├── <recurso>.module.ts
├── <recurso>.controller.ts
├── <recurso>.controller.spec.ts
├── <recurso>.service.ts
├── <recurso>.service.spec.ts
├── dto/<recurso>.dto.ts
└── schema/<recurso>.schema.ts
```

### Schema

```ts
@Schema({ collection: '<coleccion_snake>' })
export class <Recurso> extends Document {
  @Prop({ required: false, type: Types.ObjectId, ref: <Padre>.name })
  <padre>_id: Types.ObjectId;

  @Prop({ required: false })
  estado_id: number;

  @Prop({ required: false })
  activo: boolean;

  @Prop({ required: false })
  fecha_creacion: Date;

  @Prop({ required: false })
  fecha_modificacion: Date;
}

export const <Recurso>Schema = SchemaFactory.createForClass(<Recurso>);
<Recurso>Schema.set('versionKey', false);
// Índice para la consulta más frecuente: <explica cuál>
<Recurso>Schema.index({ <padre>_id: 1, activo: 1 });
```

### DTO

```ts
export class <Recurso>Dto {
  @ApiProperty({ description: '...' })
  readonly <padre>_id: Types.ObjectId;
  // ... un @ApiProperty por campo, con description en español
  activo: boolean;
  fecha_creacion: Date;
  fecha_modificacion: Date;
}
```

Si el repo usa `class-validator`, agrega validaciones (`@IsMongoId`, `@IsOptional`, …); si no, no lo introduzcas sin preguntar.

### Service

Métodos estándar (nombres del repo: `post`, `getAll`, `getById`, `put`, `delete`, `count`):

- `private populateFields()` — rutas a poblar con `?populate=true`.
- `private checkRelated(dto)` — verifica que cada `<x>_id` referenciado exista (`findById`); si no, `throw new Error('<Entidad> relacionada con id <id> no existe')`.
- `post(dto)` — `checkRelated`; fija `activo: true`, `fecha_creacion` y `fecha_modificacion` con la misma `new Date()`; `create`.
- `getAll(filterDto)` — `new FiltersService(filterDto)` → `find(getQuery(), getFields(), getLimitAndOffset()).sort(getSortBy()).populate(...).lean().exec()`.
- `getById(id)` — `findById`; si no existe, `throw new Error('<id> no existe')`.
- `put(id, dto)` — `checkRelated`; `fecha_modificacion = new Date()`; **no** permitir sobrescribir `fecha_creacion` (`delete dto.fecha_creacion`); `findByIdAndUpdate(id, dto, { new: true })`; si `null`, error.
- `delete(id)` — **borrado lógico**: `findByIdAndUpdate(id, { activo: false, fecha_modificacion: new Date() }, { new: true })`.
- `count(filterDto)` — `countDocuments(getQuery())`.

Para historial de estados: en `post` marcar los anteriores `actual: false` (`updateMany`) antes de crear el nuevo con `actual: true`, y si el padre guarda el estado vigente, actualizarlo.

### Controller

Respuesta estándar `{ Success, Status, Message, Data }` (+ `MetaData: { Count }` en `getAll`), con `@Res()` como el resto del repo:

| Método | Éxito | Error | Mensaje de error |
|---|---|---|---|
| `POST /` | `201` `'Registro Exitoso'` | `400` | `'Error servicio Post: la solicitud contiene un tipo de dato incorrecto o un parametro invalido'` |
| `GET /` | `200` `'Peticion Exitosa'` | `404` | `'Error en servicio GetAll: la peticion contiene un parametro incorrecto o no existe un registro'` |
| `GET /:id` | `200` `'Peticion Exitosa'` | `404` | `'Error en servicio GetOne: la peticion contiene un parametro incorrecto o no existe un registro'` |
| `PUT /:id` | `200` `'Actualizacion Exitosa'` | `400` | `'Error en servicio Put: la peticion contiene un tipo de dato incorrecto o un parametro invalido'` |
| `DELETE /:id` | `200` `'Eliminacion Exitosa'` | `404` | `'Error en el servicio Delete: la peticion contiene parametros incorrectos'` |

(Usa los textos exactos del repo si difieren.) `Data` en error = `error.message`. Aplica `new ParseObjectIdPipe([...campos _id])` en el `@Body` de `POST`/`PUT`. Decoradores Swagger completos (`@ApiTags`, `@ApiOperation`, `@ApiParam`, `@ApiBody`, `@ApiResponse`). Ruta del `@Controller`: la colección en kebab-case (`accion_mejora_estado` → `'accion-mejora-estado'`).

### Module y registro

```ts
@Module({
  imports: [MongooseModule.forFeature([
    { name: <Recurso>.name, schema: <Recurso>Schema },
    { name: <Padre>.name, schema: <Padre>Schema }, // los que use checkRelated
  ])],
  controllers: [<Recurso>Controller],
  providers: [<Recurso>Service],
  exports: [<Recurso>Service],
})
```

Registra el módulo en `app.module.ts` (`imports`).

## 3. Modificar un recurso existente

- **Campo nuevo**: `@Prop({ required: false })` (los documentos viejos no lo tienen) + DTO + spec + Swagger. Nunca volverlo obligatorio de golpe.
- **Renombrar/eliminar campo o cambiar tipo**: es incompatible. Busca consumidores (MID y MF: `grep -rn "<campo>" --include=*.ts` en `Backend/` y `Frontend/`, excluyendo `node_modules` y `dist`) y lístalos; propone mantener ambos campos durante la transición.
- **Datos existentes** (backfill, renombres): escribe el script `mongosh` (`updateMany`) en el scratchpad o en `database/` si el repo guarda scripts, **no lo ejecutes** contra bases compartidas: en test/producción lo corre el equipo de DBA. Explica cómo revertirlo.
- Actualiza la documentación de datos si el repo la tiene (p. ej. `database/Diccionario.md` y el diagrama `.drawio`): indica qué cambiar en el diagrama si no puedes editarlo.

## 4. Variables de entorno

Nombres en MAYÚSCULAS con prefijo del API (`<NOMBRE_API>_USER`, `_PASS`, `_HOST`, `_PORT`, `_DB`, `_AUTH_DB`, `_HTTP_PORT`), leídas vía `ConfigService`/`configuration.ts`. Nunca valores reales en el código ni en el commit; si agregas una, documenta su propósito en el README y, si existe, en `.env.example`. `.env` debe estar en `.gitignore`.

## 5. Pruebas

Crea/actualiza `*.service.spec.ts` y `*.controller.spec.ts` siguiendo los spec existentes (mock del modelo con `getModelToken(<Recurso>.name)`, mocks de DTO con `Types.ObjectId`). Cubre: `post` exitoso y con referencia inexistente, `getAll` con filtros, `getById` inexistente, `put`, `delete` lógico.

## 6. Verificación

Ejecuta (con el gestor del repo) y reporta resultados reales:

```bash
pnpm build
pnpm lint            # o lint:ci si existe
pnpm test -- <recurso>
```

Si alguno falla por algo preexistente ajeno al cambio, dilo explícitamente. Si es posible, levanta la API (`pnpm start:dev`) y prueba en `/swagger` o con `curl` los 5 endpoints. Confirma que el `swagger.json` regenerado incluye el recurso.

## Salida

1. Modelo acordado (tabla de campos: nombre, tipo, obligatorio, referencia, descripción).
2. Archivos creados/modificados.
3. Resultado de build/lint/test.
4. Consumidores afectados y recomendación de versión (MINOR si es nuevo, MAJOR si rompe).
5. Script de datos pendiente para DBA, si aplica.

No hagas commits: al terminar sugiere `/commit-oas`.

---

## Anexo — Beego + PostgreSQL

Sólo si el repo es Go/Beego.

**Modelo relacional**
- Tablas en **singular**, snake_case (`venta_producto`); esquemas por **funcionalidad**, no por aplicación.
- `id serial NOT NULL` (preferido) o `integer` con secuencia; PK `pk_<tabla>`.
- FK: columna `<tabla_referenciada>_id`, restricción `fk_<tabla_que_referencia>_<tabla_referenciada>`. Si referencia otro esquema, anótalo en el comentario.
- `uq_<columna>_<tabla>`, `ck_<columna>_<tabla>`, índices `idx_<tabla>_<campo>[_aux]`.
- Moneda `numeric(20,7)`, porcentaje `numeric(5,4)`, texto `character varying(n)` con longitud.
- Siempre `activo boolean NOT NULL DEFAULT TRUE`, `fecha_creacion timestamp`, `fecha_modificacion timestamp`.
- Paramétricas: `id`, `nombre` (obligatorio), `descripcion`, `codigo_abreviacion`, `numero_orden`, `activo`, fechas.
- `COMMENT ON COLUMN` en español, sin ñ ni caracteres especiales, sin repetir el tipo; en llaves indicar la relación; en autonuméricos/secuencias indicarlo con el nombre de la secuencia; describir arreglos/JSON. `activo` no necesita comentario.

**Migraciones** (`bee generate migration <accion>_<tabla>`: `crear_schema`, `crear_<tabla>`, `modificar_<tabla>`, `ingresar_registro_<tabla>`)
- Archivos `database/migrations/<fecha>_<nombre>.go` y SQL en `database/scripts/<fecha>_<nombre>_up.sql` / `_down.sql`; el orden lo da la fecha del nombre.
- **Siempre** implementar `Down()` (rollback).
- Las migraciones sólo se corren en local (`bee migrate -driver=postgres -conn="postgres://…?sslmode=disable&search_path=<schema>"`); en test/prod las ejecuta el equipo de DBA.

**Código**: respuestas con `customerrorv2` y estructura `{Success, Status, Message, Data}`; variables de entorno `<NOMBRE_API>_HTTP_PORT`, `_RUN_MODE`, `_PGUSER`, `_PGPASS`, `_PGHOST`, `_PGPORT`, `_PGDB`, `_PGSCHEMA` referenciadas en `conf/app.conf` como `${...}`; health check con `apistatus.Init()`.
