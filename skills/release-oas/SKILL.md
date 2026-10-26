---
name: release-oas
description: Prepara y verifica un release de un microservicio o cliente udistrital según los lineamientos OAS de despliegues, ramas GitFlow y versionado — versión SemVer, rama release/X.Y.Z, Swagger actualizado y su conversión a OpenAPI 2.0 para el registro en WSO2, checklist por ambiente (Drone, variables de entorno, WSO2, pruebas, BD), PR a master y develop, tag de versión, plan de rollback (N y N−1) y limpieza posterior. Es un checklist: no despliega, no hace push, no crea tags ni PR. Úsala cuando el usuario diga "/release-oas", "preparemos el release", "vamos a pasar a pruebas/producción", "qué falta para desplegar", "sube la versión", "pedir registro en WSO2", "rollback".
---

# Release OAS (preparación y verificación de despliegues)

Acompaña al líder técnico o Maintainer a preparar un release y deja un checklist verificable. **No ejecuta nada fuera del repo local**: los PR, el push, los tags, los registros en Drone/WSO2 y los despliegues los hacen las personas responsables. Las ramas y commits se hacen con `/commit-oas`.

Fuentes (léelas con `gh api repos/udistrital/lineamientos_oas/contents/<ruta> -H "Accept: application/vnd.github.raw"` para confirmar que no cambiaron):

- `despliegues/lineamientos.md` — prerrequisitos, pasos y responsables por ambiente (desarrollo, pruebas, producción).
- `repositorios_institucionales/nombre_branch.md` y `limpieza_branch.md` — GitFlow, tag en `master`, limpieza.
- `generacion_de_apis/versionado-apis-XYZ.md` — SemVer.

**Precedencia**: manda el lineamiento OAS. La guía del proyecto `udistrital/sisifo_documentacion` (`docs/backend/backend_guide.md`, sección 4) sólo complementa lo que el lineamiento no define: Swagger en OpenAPI 2.0 para Arquitectura, candidatos `-rc.N`, conservación de N y N−1, plan de rollback y poda. Lo que contradice el lineamiento **no se aplica**: rama `fix/`, ramas de corrección desde `release/*`, paso a `master` sin tag, distintivo `X.Y.Z.prod` (no es SemVer válido).

`release/`, `hotfix/`, la etiqueta `management` y los tags son del rol **Master/Maintainer**: confírmalo con el usuario antes de proponerlos.

## Paso 0 — Alcance

1. Repos incluidos en el release (MF, MID, CRUD). Si son varios, repite los pasos por repo y verifica el orden de despliegue: CRUD → MID → MF.
2. Estado de cada repo (en paralelo):
   ```bash
   git status --short
   git branch --show-current
   git tag --sort=-v:refname | head -5        # último tag y formato (con o sin "v")
   git log --oneline <ultimo-tag>..develop     # lo que entra en el release
   ```
3. Versión declarada: `package.json` y `DocumentBuilder().setVersion(...)` de `main.ts` en Nest; README o tag en Beego. Si no coinciden, anótalo.
4. Ambiente destino y qué ramas disparan cada despliegue: revisa `.drone.yml` (el lineamiento de despliegues habla de ramas `dev`/`test`/`master`; en GitFlow son `develop`/`release/*`/`master`). Si no está claro, pregúntalo; no lo supongas.

## Paso 1 — Versión

- Clasifica los commits del alcance con la tabla de `/endpoint-oas` (Paso 6): **MAJOR** si rompe el contrato (quitar o renombrar un endpoint o campo, cambiar un tipo, agregar un campo obligatorio a una petición), **MINOR** si agrega funcionalidad compatible, **PATCH** si corrige sin cambiar el contrato.
- Reglas OAS: primera salida a producción `0.1.0`; mientras no sea estable `0.Y.Z`; estable y en uso oficial `1.0.0`.
- Propón `X.Y.Z` y dónde actualizarla (`package.json`, `setVersion`, changelog si existe). No la edites sin confirmación.
- Candidatos para el ambiente de pruebas (complemento): identifícalos como `X.Y.Z-rc.N` en la imagen o artefacto; la rama sigue siendo `release/X.Y.Z`. Una corrección posterior genera un nuevo `rc`, nunca sobrescribe uno publicado.

## Paso 2 — Rama release

- `release/X.Y.Z` desde `develop`, con `/commit-oas` (Fase A, rol Maintainer).
- Desde ese momento **no entran features**: sólo correcciones, documentación y tareas de versión (lineamiento). Las correcciones encontradas en pruebas se hacen sobre la rama release o en `feature/` desde `develop` según decida el Maintainer, siempre con PR y reintegrándose a `develop`.

## Paso 3 — Swagger actualizado y OpenAPI 2.0

El lineamiento exige Swagger actualizado en el repo en cada ambiente.

1. Regenera el Swagger del framework (en Nest, al levantar la API o con el script del repo) y verifica que incluya las rutas nuevas o cambiadas del release: `python3 .claude/scripts/generar_endpoints.py src` si el repo tiene contexto, o `grep` de los `@Controller`/`@Get`/… contra `swagger/swagger.json`.
2. **Entregable para Arquitectura** (complemento de la guía): un JSON en **OpenAPI 2.0 (Swagger 2.0)**. Nest genera OpenAPI 3 (`"openapi": "3.0.0"`), así que hay que convertirlo:
   - Usa el convertidor que el equipo haya acordado (p. ej. `api-spec-converter`); no instales paquetes globales ni agregues dependencias al repo sin confirmación. Escribe la salida en el scratchpad o donde el equipo indique: **no reemplaza** el `swagger.json` del framework.
   - Valida el resultado: que tenga `"swagger": "2.0"`, que pase un validador (p. ej. `swagger-cli validate`) y que tenga las **mismas rutas y métodos** que el original. Compáralos con un script corto (`paths` × métodos de ambos archivos) y reporta las diferencias.
   - Revisa a mano lo que la conversión suele perder: `requestBody` con varios tipos de contenido, `oneOf`/`anyOf`, `nullable`, respuestas de archivos (PDF/Excel) y esquemas de seguridad.
3. Si el contrato cambia durante la estabilización, regenera y vuelve a convertir.

## Paso 4 — Checklist del ambiente (lineamiento de despliegues)

Marca cada ítem con su responsable. **APIs o clientes nuevos** llevan todos los pasos; los **existentes**, los marcados "de ser necesario".

| # | Actividad | Responsable |
|---|---|---|
| 1 | `.drone.yml` creado o actualizado | Líder o grupo de desarrollo |
| 2 | Variables de entorno registradas (el lineamiento menciona Tuleap; confirma qué repositorio de variables sigue vigente). Sólo nombres, nunca valores en Git | Líder o grupo de desarrollo |
| 3 | Solicitud y registro del despliegue en Drone | Desarrollo solicita, Infraestructura registra |
| 4 | Solicitud de registro en WSO2 y registro (APIs nuevas o endpoints nuevos). Complemento: enviar el enlace del repo, el `swagger.json` en OpenAPI 2.0, el release o commit, el ambiente y la lista de endpoints nuevos; confirmar el registro antes de probar por el gateway | Líder solicita, Arquitectura registra |
| 5 | PR a la rama del ambiente | Líder de desarrollo |
| 6 | Verificación del PR | Arquitectura |
| 7 | Pruebas: unitarias (líder de desarrollo), carga (líder de seguridad), funcionales (grupo de soporte), de usuario (centro de servicios) | Según cada tipo |
| 8 | Producción: creación o actualización de BD solicitada a Arquitectura y ejecutada por DBA | Arquitectura / DBA |

Prerrequisitos de producción (lineamiento): Swagger actualizado, refactor de APIs, `.drone.yml` actualizado y **resultado correcto** de las cuatro pruebas. Antes de pedir revisión a Seguridad, corre `/seguridad-oas` sobre el alcance del release.

## Paso 5 — Rollback (complemento de la guía)

- **N** es el release que se va a desplegar; **N−1** es el último release que pasó a producción y quedó estable (por historial de despliegues, no por numeración). Identifícalo con el último tag de `master` y confírmalo con el usuario.
- Verifica que N−1 siga recuperable: commit con tag en `master`, imagen o artefacto, configuración y variables.
- Si N trae migraciones o cambios de datos, evalúa si N−1 funciona con los datos que quedarán. Si no, **no modifiques N−1**: documenta el impacto y define con Arquitectura y DBA cómo recuperar (respaldos, operaciones registradas durante N, posible pérdida de datos, tiempos y responsables). Prefiere migraciones *expandir → migrar → contraer*.
- Criterios para activar el retorno (fallas en procesos críticos, aumento de errores) y quién lo decide. Un rollback de aplicación no revierte datos.

## Paso 6 — Promoción

Comandos que ejecuta el Maintainer (sólo muéstralos):

```bash
# PR release/X.Y.Z → master y release/X.Y.Z → develop (en GitHub)
git checkout master && git pull --ff-only
git tag -a <vX.Y.Z según el formato del repo> -m "<descripción del release>"
git push origin <tag>
```

- El lineamiento pide etiquetar con la versión los commits de `master` (también tras un `hotfix/`). Sigue el formato de tags que ya use el repo. **Nunca** reescribas ni muevas un tag publicado: una corrección es una versión nueva.
- Tras desplegar, verifica por el gateway: health check, endpoints críticos, errores y latencia.

## Paso 7 — Cierre y limpieza

- Registra evidencias: versión, commit, tag, artefacto, ambiente, resultado de las pruebas y aprobación.
- Elimina la rama `release/X.Y.Z` cuando esté integrada en `master` y `develop` (lineamiento de limpieza); el tag la conserva.
- Poda (complemento de la guía): sólo con el despliegue y las pruebas funcionales en producción satisfactorios y sin rollback pendiente, retira los artefactos de rollback obsoletos (normalmente N−2 y anteriores) y registra qué se retiró. Se conservan N y N−1, los tags, las notas y las evidencias.

## Salida

Escribe el informe en el chat y guárdalo en `.claude/docs/releases/<repo>-<X.Y.Z>.md` (local, no versionado; crea la carpeta si no existe):

```markdown
# Release <repo> <X.Y.Z> · <ambiente> · <AAAA-MM-DD>
Versión anterior: <tag> · Nivel: MAJOR | MINOR | PATCH · N−1: <tag>

## Alcance
| Commit | Tipo | Cambio de contrato |

## Swagger
- Framework: <ruta> (<versión OpenAPI>) · Rutas: N
- OpenAPI 2.0: <ruta> · validado ✅/❌ · diferencias: …

## Checklist del ambiente
| # | Actividad | Responsable | Estado | Evidencia |

## Rollback
## Comandos para el Maintainer
## Pendientes
```

No hagas commits: si el release cambia archivos del repo (versión, changelog), sugiere `/commit-oas`.
