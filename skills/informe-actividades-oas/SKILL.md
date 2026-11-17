---
name: informe-actividades-oas
description: >-
  Genera el informe de actividades de contratista a partir de los comentarios "Avances issue" que la persona dejó en las issues de udistrital/sisifo_documentacion dentro de un rango de fechas. Clasifica cada issue en las actividades específicas del contrato (solo donde encaja de forma directa, sin forzar) y entrega, por actividad, la actividad realizada, el producto asociado y el link de la issue como evidencia. Úsala cuando el usuario diga "informe de actividades", "actividades del contrato", "evidencias del periodo", "qué hice entre fecha y fecha", "cuenta de cobro/informe mensual", "/informe-actividades-oas".
---

# Informe de actividades por rango de fechas (SISIFO / OAS)

Convierte el trabajo documentado en las issues en el informe de actividades del contrato: por cada **actividad específica**, las issues que la abordan, con **actividad realizada**, **producto asociado** y **evidencia** (link). Es de solo lectura: no comenta, no edita ni cierra issues.

## Entradas

Pídelas si el usuario no las dio:

1. **Rango de fechas** (inicio y fin, `DD/MM/YYYY`).
2. **Actividades específicas del contrato**: texto numerado tal como está en el contrato. Si el usuario no las pega, usa el archivo `~/docs-issues/actividades-contrato.md` si existe; si no existe, pídelas y guárdalas ahí para la próxima vez (varían por contrato, no las inventes ni uses las de otra persona).
3. **Repo**: por defecto `udistrital/sisifo_documentacion`.
4. **Formato de entrega**: chat (por defecto), Markdown, CSV o Excel.

## Paso 1 — Qué issues cuentan

Cuenta solo trabajo **evidenciado**: issues donde la persona escribió comentarios de avance dentro del rango. Una issue que solo está asignada, o cuyo estado cambió sin comentarios suyos, **no entra** aunque su fecha de actualización caiga en el rango.

```bash
LOGIN=$(gh api user --jq .login)
# candidatas: issues donde comentó o está asignada y se actualizaron desde el inicio del rango
{ gh search issues --owner udistrital --commenter "$LOGIN" --updated ">=AAAA-MM-DD" --limit 200 \
    --json number,repository --jq '.[]|select(.repository.name=="sisifo_documentacion")|.number'
  gh search issues --owner udistrital --assignee "$LOGIN" --updated ">=AAAA-MM-DD" --limit 200 \
    --json number,repository --jq '.[]|select(.repository.name=="sisifo_documentacion")|.number'
} | sort -un
```

Para cada candidata, trae **solo los comentarios de la persona dentro del rango** (fin exclusivo: usa el día siguiente):

```bash
gh api --paginate "repos/udistrital/sisifo_documentacion/issues/<N>/comments" \
  --jq '.[]|select(.user.login=="<LOGIN>")|select(.created_at>="AAAA-MM-DD" and .created_at<"AAAA-MM-DD")|"\(.created_at[0:10])\n\(.body)"'
```

Quédate con las issues que tengan al menos un comentario de avance (los de la forma `> Avances issue DD/MM/YYYY`). Lee además el título y el cuerpo de la issue (`gh issue view <N> -R … --json title,body,url`) para el contexto y los nombres de repos y módulos. Si `gh` no está autenticado, pide `gh auth login`.

En multi-línea desde PowerShell/WSL, escribe un `.sh` en el scratchpad y ejecútalo; los `$` y `&&` en línea se rompen.

## Paso 2 — Entender lo que se hizo

Lee los comentarios de avance completos: dicen qué se cambió, en qué repos (`*_mf`, `*_mid`, `*_crud`), qué decisiones se tomaron, qué pruebas se hicieron y qué quedó pendiente. La **actividad realizada** y el **producto asociado** salen de ahí, no del título de la issue. No inventes trabajo: si el comentario no lo dice, no lo afirmes.

## Paso 3 — Clasificar sin forzar

Una issue puede encajar en **una o más** actividades. Asígnala a una actividad solo si lo que se hizo **es** esa actividad de forma directa; si la relación es tangencial, no la incluyas ahí. Ejemplos del criterio:

| Actividad (tipo) | Encaja cuando el avance… | No encaja cuando… |
|---|---|---|
| Diseños técnicos, diagramas, modelado de datos, especificaciones | produjo diagramas de arquitectura/secuencia, cambió el modelo de datos o definió una especificación técnica | solo hubo un mockup de interfaz, o la documentación se limita a un README |
| Implementar componentes (microservicios, APIs, estándares) | se desarrollaron o modificaron endpoints, servicios, colecciones o vistas | la issue fue solo pruebas, documentación o una corrección menor de producción |
| Compatibilidad e integración con plataformas institucionales | se trabajó la integración real con autenticación, gestor documental, gateway, firma, BD | solo se consume una API propia del sistema |
| Pruebas unitarias, integración, funcionales | se escribieron, corrigieron o ejecutaron pruebas | se menciona probar manualmente algo sin que sea el trabajo |
| Documentación técnica, manuales, guías de despliegue | se entregó README, diccionario, guía, plantilla o diagramas versionados | la documentación es el comentario de avance mismo |
| Atender requerimientos, incidencias o ajustes | hubo una incidencia, corrección o ajuste pedido por un área, la daily o el líder | era desarrollo planificado de la issue |
| Funciones derivadas del contrato asignadas por el supervisor | el trabajo fue pedido o aprobado por el líder o supervisor y no entra en las demás (propuestas, estándares, demos, estimaciones) | ya está cubierto por una actividad específica |

Si una actividad queda sin issues, díselo al usuario en lugar de rellenarla.

## Paso 4 — Redactar

Español, tercera persona o infinitivo sustantivado, concreto y verificable. Una entrada por issue y actividad:

```markdown
## Actividad <N>. <texto de la actividad>

**#<issue>**
- **Actividad realizada:** <qué se hizo, con nombres de componentes y archivos relevantes>
- **Producto asociado:** <entregable: componente, vista, documento, suite, repositorio y módulo>
- **Evidencias:** https://github.com/udistrital/sisifo_documentacion/issues/<issue>
```

- Si la misma issue aplica a varias actividades, describe en cada una **solo lo que corresponde a esa actividad** (no repitas el mismo texto).
- Marca `(abierta)` las issues que siguen abiertas; no presentes como terminado lo que está pendiente (casillas sin marcar, subtareas sin hacer).
- Agrupa por actividad, en el orden del contrato.
- Cierra con una sección **Lo que no se incluyó**: issues descartadas y por qué (sin comentarios en el rango, o encaje débil en cierta actividad).

## Paso 5 — Entregar

1. Muestra el informe y guárdalo en `~/docs-issues/informe-actividades-<AAAA-MM-DD>_<AAAA-MM-DD>.md` (fuera de los repos). Si pidió Excel o CSV, genera además la tabla `actividad, issue, actividad realizada, producto asociado, evidencia`.
2. Lista los supuestos (fechas, criterio de filtro) y las dudas de clasificación para que el usuario las confirme.
3. Si el usuario corrige una clasificación, aplícala solo a este informe; no cambies el criterio general salvo que lo pida.
4. No publiques nada en GitHub ni modifiques issues.
