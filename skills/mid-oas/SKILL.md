---
name: mid-oas
description: Implementa o modifica lógica de negocio en una API MID udistrital siguiendo los lineamientos OAS — controller delgado, service con la lógica, helpers/servicios compartidos para llamadas a CRUD y APIs externas (parámetros, terceros, oikos, nuxeo), manejo de errores con excepciones y filtro global, respuesta estándar, concurrencia controlada (equivalente a errgroup), escrituras en varios pasos con compensación, logs, configuración por ambiente, Swagger y pruebas. NestJS principalmente, con anexo Beego. Úsala cuando el usuario diga "/mid-oas", "agrega un servicio en el mid", "lógica en el mid", "endpoint que combine/consulte varias APIs", "cambio de estado desde el mid", o la tarea implique tocar un *_mid.
---

# MID OAS (lógica de negocio)

El MID **consulta, agrupa, ordena, procesa y expone** información combinando servicios CRUD y otras APIs. No persiste directamente: escribe a través de los CRUD.

Fuentes (léelas con `gh api repos/udistrital/lineamientos_oas/contents/<ruta> -H "Accept: application/vnd.github.raw"` cuando necesites el detalle):

- `generacion_de_apis/logica_orientada_a_funciones.md` — capas `controllers → services → helpers`, respuesta estándar.
- `generacion_de_apis/go_routines.md` — paralelismo controlado (errgroup) y sus restricciones.
- `generacion_de_apis/control_error_json_mid.md`, `logs_api.md` — errores y logs.
- `api_nest/manejo_error.md`, `api_nest/refactorizacion.md`, `api_nest/swagger.md`, `api_nest/variables_entorno.md`.

## Paso 0 — Reconocer el repo

1. Stack (`@nestjs/axios` → Nest; `beego` → anexo) y gestor de paquetes por lockfile.
2. Mapa del repo (en `plan_anual_auditoria_mid`, por ejemplo):
   - `src/application/<recurso>/` → `controller`, `service`, `module` (+ `dto/`, `services/` internos si es grande).
   - `src/shared/services/` → **clientes de APIs** (`AuditoriaCrudService`, `ParametrosService`, `TercerosService`/`TercerosHelperService`, `OikosService`, `NuxeoService`, `PlantillasMidService`), exportados por `ServicesModule`.
   - `src/shared/utils/`, `src/utils/` → **helpers** puros reutilizables.
   - `src/config/` → `configuration.ts` (variables de entorno `env()`) y `config.default|development|production.ts` (IDs de negocio por ambiente: `TIPO_PARAMETRO`, `ETIQUETAS_ROL`, …).
   - `LoggerService` → filtro global de excepciones + interceptores de Axios con `nestjs-pino`.
3. Toma como plantilla el módulo existente más parecido y respeta su estilo.
4. Valida rutas nuevas o modificadas con las reglas de `/endpoint-oas`.

## 1. Capas (lineamiento "lógica orientada a funciones")

Flujo obligatorio: `main → module/router → controller → service → helpers/servicios compartidos`.

| Capa | Hace | No hace |
|---|---|---|
| **Controller** | Recibe params/query/body, decoradores Swagger, llama **un** método del service y devuelve su resultado | Lógica de negocio, llamadas HTTP, transformaciones |
| **Service** (`application/<recurso>`) | Orquesta la funcionalidad: valida entrada, consulta CRUD/APIs, combina, aplica reglas, decide estados | Construir URLs a mano si ya existe un cliente compartido |
| **Servicios compartidos** (`shared/services`) | Un cliente por API externa (`get/post/put/delete` + URL base de config) | Reglas de un módulo concreto |
| **Helpers/utils** | Funciones puras reutilizables (reemplazar ids por nombres, ordenar, formatear) | Llamadas HTTP con estado |

Si una lógica se repite en dos services, muévela a un helper o servicio compartido en vez de copiarla.

## 2. Controller

```ts
@ApiTags('<Recurso>')
@Controller('<recurso>')
export class <Recurso>Controller {
  constructor(private readonly <recurso>Service: <Recurso>Service) {}

  @Get(':id')
  @ApiOperation({ summary: '<qué hace>' })
  @ApiParam({ name: 'id', required: true, description: '...' })
  @ApiResponse({ status: HttpStatus.OK, description: '...' })
  @ApiResponse({ status: HttpStatus.NOT_FOUND, description: '...' })
  async getById(@Param('id') id: string) {
    return this.<recurso>Service.getOne(id);
  }
}
```

Para `POST`/`PUT` define un **DTO** en `dto/` con `@ApiProperty` en vez de `@Body() body: any` (si el módulo existente usa `any`, al menos documenta el body con `@ApiBody({ schema: … })`).

## 3. Service y respuesta

- Respuesta estándar `{ Success, Status, Message, Data }`. Si reenvías la respuesta del CRUD, ya viene con ese formato: transforma `Data` y conserva la envoltura. Si construyes una nueva, usa la misma forma y mayúsculas.
- **Errores con excepciones de Nest** (las formatea el filtro global):
  - `BadRequestException` → parámetros o body inválidos (validar al inicio: ids requeridos, tipos, estados permitidos).
  - `NotFoundException` → el recurso pedido no existe (`data?.Data == null`).
  - `HttpException(..., HttpStatus.BAD_GATEWAY | INTERNAL_SERVER_ERROR)` → falla de un servicio externo.
  - Mensajes en español, específicos: `No se encontró plan de mejoramiento con id ${id}`.
- No te tragues errores: si capturas uno para enriquecerlo, relánzalo. Un `catch` que sólo hace `console.error` y sigue devuelve datos incompletos sin avisar; úsalo sólo para datos **opcionales** (p. ej. nombre de un tercero) y registra con el logger.
- Lista vacía = `200` con `Data: []`, no error.
- IDs de negocio (estados, tipos, roles) **sólo** desde `config.*.ts` (`environment.X`), nunca números mágicos; si agregas uno, agrégalo en **default/development/production** según corresponda.
- URLs base desde variables de entorno (`<API>_SERVICE`), vía `ConfigService` o `env()`.

## 4. Concurrencia (equivalente Nest del lineamiento de go routines)

El lineamiento recomienda paralelizar **sólo lecturas (GET)**; las escrituras (POST/PUT/DELETE) requieren control porque pueden dejar datos inconsistentes.

- **Lecturas independientes** → `Promise.all([...])`. Si fallar una no debe tumbar todo, `Promise.allSettled` y trata los `rejected` explícitamente.
- **Muchas lecturas sobre una lista** (equivalente a `SetLimit`): no lances cientos de peticiones a la vez; procesa en lotes:
  ```ts
  for (let i = 0; i < items.length; i += 10) {
    await Promise.all(items.slice(i, i + 10).map((it) => this.enriquecer(it)));
  }
  ```
  Mejor aún: evita N+1 consultando en bloque al CRUD (`query=campo__in:a|b|c`, `limit=0`) y cruzando en memoria con un `Map`.
- **Estado compartido** (equivalente a mutex): no mutes un arreglo/objeto externo desde callbacks concurrentes; haz que cada promesa **retorne** su resultado y combina después.
- Cachea dentro de la petición lo que se repite (p. ej. lista de parámetros de estados) en vez de pedirlo por elemento, y no lo guardes en propiedades del service (los services son singleton: un `this.estados.push(...)` acumula entre peticiones).

## 5. Escrituras en varios pasos

Mongo vía CRUD no da transacciones entre llamadas. Cuando una operación del MID hace varias escrituras (crear registro + historial de estado + actualizar padre):

1. **Valida todo antes** de escribir (existencia, estado actual permitido, permisos de rol).
2. Ordena los pasos de forma que un fallo intermedio deje el menor daño (primero lo que es fácil de revertir).
3. Guarda lo creado y, si un paso posterior falla, **compensa** (borrado lógico o restaurar valor anterior) y luego lanza la excepción con un mensaje que diga qué quedó hecho y qué no.
4. Cambios de estado: `POST` a la colección de historial (`<recurso>-estado`); el CRUD marca el anterior como `actual: false`.
5. Escrituras secuenciales (`await` una por una); nunca `Promise.all` de escrituras dependientes.

## 6. Logs

- Usa el logger del repo (`PinoLogger`/`Logger` de Nest con contexto del service), no `console.log`. Los errores de Axios ya los registra el interceptor del `LoggerService`: no los dupliques.
- Registra contexto útil (ids, operación), **nunca** tokens, contraseñas, documentos en base64 ni datos personales completos.

## 7. Configuración nueva

- Variable de entorno nueva: agrégala en `configuration.ts` (`env()`), en el `.env` local (no versionado) y documenta en el README; nombre en MAYÚSCULAS (`<API>_SERVICE`, `<NOMBRE_MID>_PORT`).
- Dependencia nueva de otra API: crea su cliente en `shared/services/` y expórtalo en `ServicesModule`.

## 8. Pruebas

`*.service.spec.ts` con los servicios compartidos mockeados (`{ provide: AuditoriaCrudService, useValue: { traerDataCrud: jest.fn(), post: jest.fn(), … } }`). Cubre: caso feliz, id faltante (`BadRequestException`), recurso inexistente (`NotFoundException`), falla del servicio externo, y para escrituras en varios pasos, que se compense si falla un paso intermedio.

## 9. Verificación

```bash
pnpm build
pnpm lint
pnpm test -- <recurso>
```

Reporta resultados reales; si algo falla por causas preexistentes, dilo. Si puedes, levanta el MID (`pnpm start:dev`) con el CRUD local y prueba el endpoint desde `/swagger` o `curl`, mostrando la respuesta.

## Salida

1. Diseño breve: endpoint(s), servicios externos que consulta, pasos y validaciones.
2. Archivos creados/modificados.
3. Resultado de build/lint/test y de la prueba manual.
4. Consumidores en el MF a actualizar (`grep` de la ruta en `Frontend/`) y recomendación de versión.

No hagas commits: al terminar sugiere `/commit-oas`.

---

## Anexo — MID en Beego

- Estructura: `controllers/` (sin lógica, llaman al service y mapean con `requestresponse.APIResponseDTO(success, status, data, message)`), `services/` (lógica), `helpers/` (reutilizable), `routers/`, `tests/helpers/...`.
- En cada controller `defer errorhandler.HandlePanic(&c.Controller)`; en services un `defer func(){ if err := recover(); err != nil { … panic(outputError) } }()` con `{"funcion": "/NombreFuncion", "err": err, "status": "502"}`.
- `beego.ErrorController(&errorhandler.ErrorHandlerController{})` en el router; health check `apistatus.Init()` en `main.go`.
- Paralelismo sólo para GET con `errgroup.Group`, `SetLimit(n)` y `sync.Mutex` al hacer `append` a resultados compartidos; `Wait()` para propagar errores.
- Logs con `github.com/astaxie/beego/logs` (`logs.Error(...)`), archivo en `/var/log/beego/<repo>/<repo>.log`.
- URLs de servicios desde `beego.AppConfig.String("<Servicio>Service")` alimentadas por variables de entorno.
