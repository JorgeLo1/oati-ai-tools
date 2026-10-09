#!/usr/bin/env python3
"""Guardián de skills para los repos bajo la carpeta udistrital (UDISTRITAL_DIR,
ver oas_config.py). Convierte las reglas de <udistrital>/AGENTS.md
en controles verificando en el transcript de la sesión qué skills se usaron y qué aprobó el usuario.

Modos (argumento):
  pre-edit   PreToolUse Edit|Write|MultiEdit|NotebookEdit
  pre-read   PreToolUse Read
  pre-bash   PreToolUse Bash (comandos analizados con shell_cmd: commits reales y archivos que se escriben)
  stop       Stop

Controles sobre un archivo de código de un repo udistrital (por herramienta de edición o por Bash):
  - rama feature/ o hotfix/ sin especificación aprobada en <udistrital>/.claude/specs que incluya el repo
  - código de un *_crud sin /crud-oas, de un *_mid sin /mid-oas
  - rutas nuevas (@Get/@Post/.../@Controller, // @router) sin /endpoint-oas (sólo con herramienta de edición)
  - .env*, lockfiles, dist/, node_modules/ -> bloqueados
Especificaciones (<udistrital>/.claude/specs/*.md):
  - sólo se editan con las herramientas de edición (no por Bash)
  - borrador -> aprobada/en-implementacion/implementada exige respuesta "Aprobar plan…" del usuario
  - -> omitida exige "Omitir planificación…"; cambiar rama/repos de una aprobada exige "Aprobar cambio…"
    (en una pregunta AskUserQuestion que mencione el nombre del archivo; cada aprobación se usa una vez)
Commits: exigen /commit-oas y, si incluyen código, /seguridad-oas. Stop: tras un commit real en un repo udistrital, /documentar-cambios.
Configuración del sistema (plugin oas-ai-tools, ~/.claude/{skills,agents,scripts,plugins}, settings, ~/.config/oas-ai-tools,
<udistrital>/CLAUDE.md y AGENTS.md, archivos -off): editar pide confirmación.
Lectura de .env: pide confirmación (herramienta Read o Bash).

Desactivar en un repo: el USUARIO crea <repo>/.claude/.skill-guard-off
"""
import json
import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shell_cmd  # noqa: E402
import oas_config  # noqa: E402

RAIZ = oas_config.udistrital_dir()
SPECS = oas_config.specs_dir()
CLAUDE_HOME = os.path.realpath(os.path.expanduser("~/.claude"))
PLUGIN_ROOT = os.path.realpath(oas_config.raiz_plugin())
CONFIG_OAS = os.path.realpath(oas_config.CONFIG_DIR)
EXT_CODIGO = (".ts", ".js", ".mjs", ".cjs", ".go", ".html", ".scss", ".css", ".json", ".sql", ".yml", ".yaml", ".conf", ".py", ".sh")
RE_RUTA = re.compile(r"@(Controller|Get|Post|Put|Patch|Delete|All)\s*\(|//\s*@router\b")
RE_ENV = re.compile(r"^\.env(\..+)?$")
RE_COMMIT_OK = re.compile(r"^\[[^\]\n]+ [0-9a-f]{7,40}\]", re.MULTILINE)  # salida de un commit real
LOCKFILES = ("pnpm-lock.yaml", "package-lock.json", "yarn.lock", "go.sum")
ESTADOS_ACTIVOS = ("aprobada", "en-implementacion", "implementada")
PESO = {None: 0, "ask": 1, "deny": 2}


# ---------------------------------------------------------------- utilidades

def bajo(path, raiz):
    p = os.path.realpath(path)
    return p == raiz or p.startswith(raiz + os.sep)


def repo_de(path):
    d = path if os.path.isdir(path) else os.path.dirname(path)
    while d and not os.path.isdir(d):
        d = os.path.dirname(d)
    r = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=d or "/", capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def desactivado(repo):
    return bool(repo) and os.path.exists(os.path.join(repo, ".claude", ".skill-guard-off"))


def tipo_api(repo):
    nombre = os.path.basename(repo)
    pkg = os.path.join(repo, "package.json")
    deps = open(pkg, errors="ignore").read() if os.path.exists(pkg) else ""
    if os.path.exists(os.path.join(repo, "angular.json")):
        return "mf"
    if nombre.endswith("_crud") or "@nestjs/mongoose" in deps:
        return "crud"
    if nombre.endswith("_mid") or "@nestjs/axios" in deps:
        return "mid"
    return None


def rama_actual(repo):
    return subprocess.run(["git", "branch", "--show-current"], cwd=repo, capture_output=True, text=True).stdout.strip()


def leer_transcript(transcript):
    """(eventos, aprobaciones, resultados).
    eventos: ('skill', nombre) | ('bash', comando, tool_use_id) en orden.
    aprobaciones: [(tool_use_id, pregunta, respuesta)] de AskUserQuestion.
    resultados: tool_use_id -> (es_error, texto)."""
    eventos, aprobaciones, resultados = [], [], {}
    if not transcript or not os.path.exists(transcript):
        return eventos, aprobaciones, resultados
    for linea in open(transcript, errors="ignore"):
        try:
            d = json.loads(linea)
        except Exception:
            continue
        cont = (d.get("message") or {}).get("content")
        tur = d.get("toolUseResult")
        if isinstance(cont, str):
            eventos += [("skill", n.split(":")[-1]) for n in re.findall(r"<command-name>/?([^<\s]+)</command-name>", cont)]
            continue
        if not isinstance(cont, list):
            continue
        for it in cont:
            if not isinstance(it, dict):
                continue
            tipo = it.get("type")
            if tipo == "tool_use" and it.get("name") == "Skill":
                eventos.append(("skill", str((it.get("input") or {}).get("skill", "")).split(":")[-1]))
            elif tipo == "tool_use" and it.get("name") == "Bash":
                eventos.append(("bash", (it.get("input") or {}).get("command", ""), it.get("id", ""), d.get("cwd")))
            elif tipo == "text":
                eventos += [("skill", n.split(":")[-1]) for n in re.findall(r"<command-name>/?([^<\s]+)</command-name>", it.get("text", ""))]
            elif tipo == "tool_result":
                c = it.get("content")
                texto = c if isinstance(c, str) else " ".join(x.get("text", "") for x in c or [] if isinstance(x, dict))
                resultados[it.get("tool_use_id")] = (bool(it.get("is_error")), texto)
                if isinstance(tur, dict) and isinstance(tur.get("answers"), dict):
                    for pregunta, respuesta in tur["answers"].items():
                        aprobaciones.append((it.get("tool_use_id"), str(pregunta), str(respuesta)))
    return eventos, aprobaciones, resultados


def uso_skill(evs, nombre):
    return any(e[0] == "skill" and e[1] == nombre for e in evs)


def dirs_commit(cmd, cwd):
    """Directorios donde el comando hace `git commit` (resuelve cd, git -C, bash -c, alias)."""
    segs = shell_cmd.segmentos(cmd, cwd)
    if segs is None:
        return [cwd] if re.search(r"\bgit(?:\s+-[cC]\s+\S+)*\s+commit\b", cmd) else []
    return [g[2] for s in segs if (g := shell_cmd.git_subcomando(s)) and g[0] == "commit"]


def cabecera(texto):
    m = re.match(r"^---\n(.*?)\n---", texto or "", re.S)
    if not m:
        return None
    cab = m.group(1)

    def campo(n):
        x = re.search(rf"^{n}:\s*(.+?)\s*$", cab, re.M)
        return x.group(1).strip().strip("'\"") if x else None

    repos = re.search(r"^repos:\s*\[(.*?)\]", cab, re.M)
    return {
        "estado": (campo("estado") or "borrador").split()[0],
        "rama": campo("rama"),
        "repos": sorted(x.strip().strip("'\"") for x in repos.group(1).split(",") if x.strip()) if repos else [],
    }


def spec_de(repo, rama):
    """(archivo, estado) de la especificación que cubre repo+rama; estado 'repo-no-listado' si la rama
    coincide pero el repo no está en repos:. (None, None) si no hay."""
    if not os.path.isdir(SPECS):
        return None, None
    nombre, mejor = os.path.basename(repo), (None, None)
    for f in sorted(os.listdir(SPECS)):
        if not f.endswith(".md"):
            continue
        cab = cabecera(open(os.path.join(SPECS, f), errors="ignore").read())
        if not cab or cab["rama"] != rama:
            continue
        if nombre not in cab["repos"]:
            mejor = mejor if mejor[0] else (f, "repo-no-listado")
            continue
        if cab["estado"] != "borrador":
            return f, cab["estado"]
        mejor = (f, "borrador")
    return mejor


def consumir_aprobacion(datos, aprobaciones, stem, prefijo):
    """Usa (una sola vez) una respuesta del usuario que empiece por `prefijo` a una pregunta que mencione `stem`."""
    marca = os.path.join(tempfile.gettempdir(), f"claude-skill-guard-aprob-{datos.get('session_id', 'x')}")
    usadas = set(open(marca).read().split("\n")) if os.path.exists(marca) else set()
    for tid, pregunta, respuesta in aprobaciones:
        clave = f"{tid}:{pregunta}"
        if clave in usadas:
            continue
        if stem in pregunta and respuesta.strip().lower().startswith(prefijo.lower()):
            with open(marca, "a") as f:
                f.write(clave + "\n")
            return True
    return False


# ---------------------------------------------------------------- reglas sobre un archivo

def revisar_destino(path, datos, ctx, nuevo=None, viejo=None, via_bash=False):
    """Devuelve (decision, razon) o (None, None)."""
    path = os.path.realpath(path)
    base = os.path.basename(path)

    # Configuración del propio sistema: siempre con confirmación del usuario
    config = (bajo(path, os.path.join(CLAUDE_HOME, "skills")) or bajo(path, os.path.join(CLAUDE_HOME, "agents"))
              or bajo(path, os.path.join(CLAUDE_HOME, "scripts")) or re.match(r"^settings(\.local)?\.json$", base) and bajo(path, CLAUDE_HOME)
              or bajo(path, PLUGIN_ROOT) or bajo(path, CONFIG_OAS) or bajo(path, os.path.join(CLAUDE_HOME, "plugins"))
              or path in (os.path.join(RAIZ, "CLAUDE.md"), os.path.join(RAIZ, "AGENTS.md"))
              or base in (".skill-guard-off", ".contexto-off"))
    if config:
        return "ask", (f"[skill-guard] {path} es configuración de las reglas/guardianes. "
                       "Modificarla requiere tu confirmación explícita.")

    if not bajo(path, RAIZ):
        return None, None

    if bajo(path, SPECS):
        if via_bash:
            return "deny", ("[skill-guard] Las especificaciones se editan sólo con las herramientas de edición (Edit/Write), "
                            "no por Bash, para que el guardián valide las aprobaciones.")
        return revisar_spec(path, datos, ctx, nuevo, viejo)

    if "/.claude/" in path:  # contexto local del repo (docs, cambios, seguridad): libre
        return None, None

    repo = repo_de(path)
    if desactivado(repo):
        return None, None

    if RE_ENV.match(base) and not base.endswith(".example"):
        return "deny", (f"[skill-guard] {base} contiene secretos/configuración local: no se edita desde Claude. "
                        "Indica al usuario qué variable agregar y que la ponga él.")
    if base in LOCKFILES:
        return "deny", f"[skill-guard] {base} sólo se modifica con el gestor de paquetes (pnpm/npm/go), no a mano."
    if "/node_modules/" in path or "/dist/" in path:
        return "deny", "[skill-guard] node_modules/ y dist/ son generados: no se editan."

    if not repo or not (path.endswith(EXT_CODIGO) or base == "__xargs__"):
        return None, None

    rama = rama_actual(repo)
    if re.match(r"^(feature|hotfix)/", rama):
        archivo, estado = spec_de(repo, rama)
        if not archivo:
            return "deny", (f"[skill-guard] La rama `{rama}` no tiene especificación en {SPECS}/. Antes de escribir "
                            "código invoca la skill `planificar-issue` y obtén la aprobación del usuario.")
        if estado == "repo-no-listado":
            return "deny", (f"[skill-guard] La especificación {archivo} de `{rama}` no incluye el repo "
                            f"`{os.path.basename(repo)}` en `repos:`. Actualiza alcance/plan y pide al usuario "
                            "\"Aprobar cambio\" antes de editar.")
        if estado == "borrador":
            return "deny", (f"[skill-guard] La especificación {archivo} sigue en `borrador`. Termina /planificar-issue "
                            "y consigue la aprobación del plan del usuario antes de escribir código.")

    tipo = tipo_api(repo)
    requerida = {"crud": "crud-oas", "mid": "mid-oas"}.get(tipo)
    if requerida and not uso_skill(ctx["eventos"], requerida):
        return "deny", (f"[skill-guard] Vas a modificar código de un {tipo.upper()} ({os.path.basename(repo)}) sin haber "
                        f"cargado /{requerida}. Invoca la skill `{requerida}` (herramienta Skill), sigue sus pasos y reintenta.")
    if tipo in ("crud", "mid") and nuevo is not None and len(RE_RUTA.findall(nuevo)) > len(RE_RUTA.findall(viejo or "")) \
            and not uso_skill(ctx["eventos"], "endpoint-oas"):
        return "deny", ("[skill-guard] El cambio agrega o modifica rutas HTTP sin haber pasado por /endpoint-oas. "
                        "Invoca la skill `endpoint-oas`, valida nombre/verbo/status/Swagger/consumidores y reintenta.")
    return None, None


def revisar_spec(path, datos, ctx, nuevo, viejo_fragmento):
    stem = os.path.splitext(os.path.basename(path))[0]
    anterior = open(path, errors="ignore").read() if os.path.exists(path) else None
    contenido = nuevo
    ti = datos.get("tool_input") or {}
    if datos.get("tool_name") in ("Edit", "MultiEdit") and anterior is not None:
        contenido = anterior
        ediciones = ti.get("edits") or [{"old_string": ti.get("old_string", ""), "new_string": ti.get("new_string", ""),
                                         "replace_all": ti.get("replace_all", False)}]
        for e in ediciones:
            o, n = e.get("old_string", ""), e.get("new_string", "")
            if o not in contenido:
                return None, None  # la edición fallará sola
            contenido = contenido.replace(o, n) if e.get("replace_all") else contenido.replace(o, n, 1)
    if contenido is None:
        return None, None
    cab_n = cabecera(contenido)
    if not cab_n or not cab_n["rama"] or not cab_n["repos"]:
        return "deny", (f"[skill-guard] {stem}.md debe empezar con la cabecera YAML (issue, titulo, rama, repos, estado, "
                        "actualizado). Ver la skill planificar-issue.")
    cab_v = cabecera(anterior) if anterior else None
    est_v = cab_v["estado"] if cab_v else None
    est_n = cab_n["estado"]
    if est_n not in ("borrador", "omitida") + ESTADOS_ACTIVOS:
        return "deny", f"[skill-guard] estado `{est_n}` no válido (borrador | aprobada | en-implementacion | implementada | omitida)."

    necesita = None
    if est_n in ESTADOS_ACTIVOS and est_v in (None, "borrador"):
        necesita = "Aprobar plan"
    elif est_n == "omitida" and est_v != "omitida":
        necesita = "Omitir planificación"
    elif est_v in ESTADOS_ACTIVOS + ("omitida",) and (cab_n["rama"] != cab_v["rama"] or cab_n["repos"] != cab_v["repos"]):
        necesita = "Aprobar cambio"
    if necesita and not consumir_aprobacion(datos, ctx["aprobaciones"], stem, necesita):
        return "deny", (f"[skill-guard] Este cambio en {stem}.md requiere la aprobación explícita del usuario: pregúntale "
                        f"con AskUserQuestion mencionando `{stem}` en la pregunta y con una opción cuya etiqueta empiece por "
                        f"\"{necesita}\". Si la elige, reintenta.")
    return None, None


def emitir(decision, razon):
    if decision:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                                 "permissionDecisionReason": oas_config.adaptar(razon)}}, ensure_ascii=False))


def contexto(datos):
    ev, ap, res = leer_transcript(datos.get("transcript_path"))
    return {"eventos": ev, "aprobaciones": ap, "resultados": res}


# ---------------------------------------------------------------- modos

def pre_edit(datos):
    ti = datos.get("tool_input") or {}
    path = ti.get("file_path") or ti.get("notebook_path") or ""
    if not path:
        return
    nuevo = ti.get("content") if "content" in ti else ti.get("new_string") or ti.get("new_source") or \
        "\n".join(e.get("new_string", "") for e in ti.get("edits") or [])
    viejo = ti.get("old_string") or "\n".join(e.get("old_string", "") for e in ti.get("edits") or [])
    emitir(*revisar_destino(path, datos, contexto(datos), nuevo=nuevo, viejo=viejo))


def pre_read(datos):
    path = (datos.get("tool_input") or {}).get("file_path") or ""
    base = os.path.basename(path)
    if path and bajo(path, RAIZ) and RE_ENV.match(base) and not base.endswith(".example"):
        emitir("ask", f"[skill-guard] {base} puede contener secretos; leerlo los deja en la conversación. ¿Permitir?")


def pre_bash(datos):
    cmd = (datos.get("tool_input") or {}).get("command", "")
    cwd = datos.get("cwd") or os.getcwd()
    segs = shell_cmd.segmentos(cmd, cwd)
    if segs is None:
        if bajo(cwd, RAIZ) or RAIZ in cmd:
            emitir("ask", "[skill-guard] No pude analizar el comando (comillas o sintaxis inusual) y se ejecuta en un "
                          "repo udistrital. Revísalo antes de permitirlo.")
        return
    ctx = None
    peor = (None, None)

    def considerar(res):
        nonlocal peor
        if PESO[res[0]] > PESO[peor[0]]:
            peor = res

    for seg in segs:
        g = shell_cmd.git_subcomando(seg)
        if g and g[0] == "commit" and bajo(g[2], RAIZ):
            ctx = ctx or contexto(datos)
            considerar(revisar_commit(g, cmd, ctx))
        destinos = shell_cmd.escrituras(seg)
        xargs = "xargs" in seg.tokens or (seg.prog == "find" and ("-delete" in seg.args or any(
            x in seg.args for x in ("-exec", "-execdir")) and re.search(r"\b(sed|perl|rm|mv|cp|tee)\b", " ".join(seg.args))))
        if xargs and (seg.prog in ("sed", "perl", "rm", "mv", "cp", "tee", "find") or "-i" in " ".join(seg.args)):
            destinos.append(os.path.join(seg.cwd, "__xargs__"))  # archivos desconocidos dentro del directorio
        for d in destinos:
            ctx = ctx or contexto(datos)
            considerar(revisar_destino(d, datos, ctx, via_bash=True))
        for p in shell_cmd.lecturas(seg):
            b = os.path.basename(p)
            if bajo(p, RAIZ) and RE_ENV.match(b) and not b.endswith(".example") and p not in destinos:
                considerar(("ask", f"[skill-guard] El comando lee {b}, que puede contener secretos. ¿Permitir?"))
    emitir(*peor)


def revisar_commit(g, cmd, ctx):
    _, args, directorio = g
    repo = repo_de(directorio)
    if not repo or desactivado(repo):
        return None, None
    if not uso_skill(ctx["eventos"], "commit-oas"):
        return "deny", ("[skill-guard] Los commits en repos udistrital se hacen con /commit-oas. "
                        "Invoca la skill `commit-oas` y sigue su flujo (con confirmación del usuario).")
    staged = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=repo, capture_output=True, text=True).stdout
    if any(re.match(r"^-[A-Za-z]*a[A-Za-z]*$", a) or a == "--all" for a in args):
        staged += subprocess.run(["git", "diff", "--name-only"], cwd=repo, capture_output=True, text=True).stdout
    codigo = [f for f in staged.splitlines() if f.endswith(EXT_CODIGO) and not f.startswith(".claude/")
              and os.path.basename(f) not in LOCKFILES]
    if codigo and not uso_skill(ctx["eventos"], "seguridad-oas"):
        return "deny", (f"[skill-guard] El commit incluye {len(codigo)} archivo(s) de código y en esta sesión no se ha "
                        "ejecutado /seguridad-oas. Invoca la skill `seguridad-oas` sobre el diff, reporta los hallazgos "
                        "al usuario y luego retoma el commit.")
    return None, None


def stop(datos):
    if datos.get("stop_hook_active"):
        return
    cwd = datos.get("cwd") or os.getcwd()
    if not bajo(cwd, RAIZ):
        return
    repo = repo_de(cwd)
    if desactivado(repo):
        return
    ctx = contexto(datos)
    evs, res = ctx["eventos"], ctx["resultados"]

    def commit_real(e):  # en un repo udistrital, ejecutado sin error y con la salida "[rama hash] mensaje"
        if e[0] != "bash" or not any(bajo(d, RAIZ) for d in dirs_commit(e[1], e[3] or cwd)):
            return False
        error, texto = res.get(e[2], (True, ""))
        return not error and bool(RE_COMMIT_OK.search(texto))

    idx = max((i for i, e in enumerate(evs) if commit_real(e)), default=-1)
    if idx < 0 or uso_skill(evs[idx:], "documentar-cambios"):
        return
    clave = f"{datos.get('session_id', '')}:{evs[idx][2]}"
    marca = os.path.join(tempfile.gettempdir(), "claude-skill-guard-stop")
    previas = set(open(marca).read().split("\n")) if os.path.exists(marca) else set()
    if clave in previas:
        return
    with open(marca, "a") as f:
        f.write(clave + "\n")
    print(json.dumps({"decision": "block", "reason": oas_config.adaptar(
        "[skill-guard] Hubo un commit en esta sesión y no se ha ejecutado /documentar-cambios después. "
        "Si la tarea quedó cerrada, invoca la skill `documentar-cambios` ahora. Si la tarea continúa "
        "(faltan más commits o el usuario no ha confirmado), dilo en una línea y termina.")}, ensure_ascii=False))


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        datos = json.load(sys.stdin)
    except Exception:
        datos = {}
    {"pre-edit": pre_edit, "pre-read": pre_read, "pre-bash": pre_bash, "stop": stop}.get(modo, lambda d: None)(datos)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # un fallo interno no debe dejar al usuario sin poder trabajar: se pide confirmación
        if len(sys.argv) > 1 and sys.argv[1].startswith("pre-"):
            emitir("ask", f"[skill-guard] Error interno del guardián ({e}); revisa la acción antes de permitirla.")
        print(f"[skill-guard] error: {e}", file=sys.stderr)
