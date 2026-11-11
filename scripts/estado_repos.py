#!/usr/bin/env python3
"""Estado de los repos de una issue antes de planificar o retomar: ¿están en develop y al día con el remoto?

Uso:
  estado_repos.py [--sistema <repo>] [--rama feature/<x>] [--base develop] [--sin-fetch] [--json] [<repo> ...]

<repo> es una ruta o un nombre (se busca bajo la carpeta udistrital, ver oas_config.py).
--sistema <repo> agrega todos los repos hermanos de <repo>: los que comparten su prefijo con otro sufijo de tipo
(`plan_anual_auditoria_mf` → `plan_anual_auditoria_mf`, `_mid`, `_crud`, `_cliente`), buscados en la carpeta del
sistema (la primera carpeta bajo la de udistrital, p. ej. SISIFO/, en Frontend/ y Backend/). Así se revisan desde el
inicio aunque todavía no se sepa cuáles tocará la issue. Los repos compartidos con otro nombre (plantillas_mid,
usuario_rol_crud…) se agregan nombrándolos.
Por cada repo: hace `git fetch` del remoto (salvo --sin-fetch), y reporta la rama actual, los cambios sin
commitear, cuántos commits le faltan a la base local respecto a origin/<base>, si existe la rama de la issue
(local o remota) y cuánto va atrás de la base, con la acción recomendada. NUNCA cambia de rama, ni hace pull,
merge, stash o commit: eso lo propone la IA y lo confirma el usuario.

Acciones posibles:
  al-dia             en <base>, sin cambios y sin commits por traer
  actualizar         en <base> sin cambios, pero faltan commits: git pull --ff-only origin <base>
  ir-a-base          en otra rama, sin cambios: git checkout <base> && git pull --ff-only origin <base>
  rama-issue         ya está en la rama de la issue: actualizar <base> sin cambiar de rama
                     (git fetch origin <base>:<base>) y preguntar si se trae <base> a la rama
  ir-a-rama-issue    la rama de la issue existe (local o remota) y el repo está en otra: cambiar a ella y
                     actualizar <base> sin cambiar de rama
  cambios-pendientes hay cambios sin commitear: el usuario decide (commitear, stash, dejarlos)
  base-divergente    la base local tiene commits que no están en el remoto: no se hace pull; avisar
  sin-remoto         no hay remoto o no tiene <base>: sólo se informa
  sin-red            falló el fetch (red/VPN): el estado del remoto puede ser viejo
  no-existe          no se encontró el repo
Sale con 0 si todos están al-dia, 1 si alguno requiere acción, 2 si no se pudo evaluar alguno.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oas_config  # noqa: E402

TIMEOUT_FETCH = 30
RE_TIPO = re.compile(r"^(.+?)_(mf|mid|crud|cliente)(?:_[a-z0-9]+)*$")


def git(repo, *args, timeout=15):
    try:
        r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, timeout=timeout)
    except Exception as e:  # timeout, git ausente
        return 1, "", str(e)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def resolver(nombre):
    """Ruta del repo: tal cual si existe; si no, el primer `<udistrital>/**/<nombre>` con .git (hasta 3 niveles)."""
    p = os.path.realpath(os.path.expanduser(nombre))
    if os.path.isdir(p):
        return p
    raiz = oas_config.udistrital_dir()
    base = os.path.basename(nombre.rstrip("/"))
    for dirpath, dirnames, _ in os.walk(raiz):
        nivel = dirpath[len(raiz):].count(os.sep)
        if base in dirnames and os.path.exists(os.path.join(dirpath, base, ".git")):
            return os.path.join(dirpath, base)
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"] if nivel < 3 else []
    return None


def es_repo(ruta):
    return os.path.exists(os.path.join(ruta, ".git"))


def hermanos(nombre):
    """Repos del mismo sistema con el mismo prefijo (ordenados: crud, mid, mf, cliente, otros)."""
    ruta = resolver(nombre)
    if not ruta:
        return [nombre]
    m = RE_TIPO.match(os.path.basename(ruta))
    if not m:
        return [ruta]
    prefijo = m.group(1)
    raiz = oas_config.udistrital_dir()
    rel = os.path.relpath(ruta, raiz)
    sistema = os.path.join(raiz, rel.split(os.sep)[0]) if not rel.startswith("..") and os.sep in rel else os.path.dirname(ruta)
    encontrados = set()
    for dirpath, dirnames, _ in os.walk(sistema):
        nivel = dirpath[len(sistema):].count(os.sep)
        for d in dirnames:
            m2 = RE_TIPO.match(d)
            if m2 and m2.group(1) == prefijo and es_repo(os.path.join(dirpath, d)):
                encontrados.add(os.path.join(dirpath, d))
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules" and not es_repo(os.path.join(dirpath, d))] \
            if nivel < 2 else []
    orden = {"crud": 0, "mid": 1, "mf": 2, "cliente": 3}
    return sorted(encontrados | {ruta}, key=lambda p: (orden.get(RE_TIPO.match(os.path.basename(p)).group(2), 9), p))


def contar(repo, rango):
    c, out, _ = git(repo, "rev-list", "--count", rango)
    return int(out) if c == 0 and out.isdigit() else None


def existe_ref(repo, ref):
    return git(repo, "rev-parse", "--verify", "-q", ref)[0] == 0


def estado(nombre, base, rama_issue, fetch):
    ruta = resolver(nombre)
    e = {"repo": os.path.basename(nombre.rstrip("/")), "ruta": ruta, "base": base}
    if not ruta or git(ruta, "rev-parse", "--is-inside-work-tree")[1] != "true":
        e["accion"] = "no-existe"
        return e
    e["repo"] = os.path.basename(ruta)
    e["rama"] = git(ruta, "branch", "--show-current")[1] or "(HEAD separado)"
    cambios = [l for l in git(ruta, "status", "--porcelain")[1].splitlines() if l.strip()]
    e["cambios"] = len(cambios)
    e["cambios_muestra"] = [l.split(None, 1)[-1] for l in cambios[:8]]  # "XY ruta" (strip quita el espacio inicial)
    tiene_remoto = git(ruta, "remote", "get-url", "origin")[0] == 0
    e["fetch"] = "omitido"
    if tiene_remoto and fetch:
        c, _, err = git(ruta, "fetch", "--quiet", "origin", timeout=TIMEOUT_FETCH)
        e["fetch"] = "ok" if c == 0 else f"falló: {err.splitlines()[-1] if err else 'sin detalle'}"
    remota = f"origin/{base}"
    e["base_local"] = existe_ref(ruta, f"refs/heads/{base}")
    e["base_remota"] = existe_ref(ruta, f"refs/remotes/{remota}")
    if e["base_remota"]:
        e["commit_remoto"] = git(ruta, "rev-parse", "--short", remota)[1]
    if e["base_local"] and e["base_remota"]:
        e["base_atras"] = contar(ruta, f"{base}..{remota}")
        e["base_adelante"] = contar(ruta, f"{remota}..{base}")
    if rama_issue:
        e["rama_issue"] = rama_issue
        e["rama_issue_local"] = existe_ref(ruta, f"refs/heads/{rama_issue}")
        e["rama_issue_remota"] = existe_ref(ruta, f"refs/remotes/origin/{rama_issue}")
        ref = rama_issue if e["rama_issue_local"] else f"origin/{rama_issue}" if e["rama_issue_remota"] else None
        if ref and e["base_remota"]:
            e["rama_issue_atras"] = contar(ruta, f"{ref}..{remota}")

    if e["cambios"]:
        e["accion"] = "cambios-pendientes"
    elif not tiene_remoto or not e["base_remota"]:
        e["accion"] = "sin-remoto"
    elif e["fetch"].startswith("falló"):
        e["accion"] = "sin-red"
    elif e.get("base_adelante"):
        e["accion"] = "base-divergente"
    elif rama_issue and e["rama"] == rama_issue:
        e["accion"] = "rama-issue"
    elif rama_issue and (e["rama_issue_local"] or e["rama_issue_remota"]):
        e["accion"] = "ir-a-rama-issue"
    elif e["rama"] == base:
        e["accion"] = "actualizar" if e.get("base_atras") else "al-dia"
    else:
        e["accion"] = "ir-a-base"
    return e


SUGERENCIA = {
    "al-dia": "Al día: nada que hacer.",
    "actualizar": "git -C {ruta} pull --ff-only origin {base}",
    "ir-a-base": "git -C {ruta} checkout {base} && git -C {ruta} pull --ff-only origin {base}",
    "rama-issue": "git -C {ruta} fetch origin {base}:{base} (actualiza {base} sin cambiar de rama); "
                  "preguntar si se trae {base} a la rama de la issue",
    "ir-a-rama-issue": "git -C {ruta} checkout {rama} && git -C {ruta} fetch origin {base}:{base}; "
                       "preguntar si se trae {base} a la rama de la issue",
    "cambios-pendientes": "Hay cambios sin commitear: el usuario decide (commitear con /commit-oas, stash o dejarlos) "
                          "antes de cambiar de rama.",
    "base-divergente": "{base} local tiene commits que no están en origin/{base}: no hagas pull; avisa al usuario.",
    "sin-remoto": "Sin remoto origin o sin origin/{base}: se planifica con lo local y se dice en la especificación.",
    "sin-red": "No se pudo hacer fetch (red/VPN): el estado del remoto puede estar viejo; avisa y reintenta.",
    "no-existe": "No se encontró el repo bajo la carpeta udistrital: clónalo o corrige el nombre.",
}


def texto(e):
    linea = [f"■ {e['repo']}: {e['accion']}"]
    if e["accion"] != "no-existe":
        det = [f"rama {e['rama']}", f"{e['cambios']} cambio(s) sin commitear"]
        if "base_atras" in e:
            det.append(f"{e['base']} {e['base_atras']} commit(s) atrás de origin/{e['base']} ({e.get('commit_remoto', '?')})")
        elif e.get("base_remota") and not e.get("base_local"):
            det.append(f"sin {e['base']} local (origin/{e['base']} en {e.get('commit_remoto', '?')})")
        if e.get("rama_issue"):
            donde = "local" if e["rama_issue_local"] else "remota" if e["rama_issue_remota"] else "no existe"
            extra = f", {e['rama_issue_atras']} commit(s) atrás de origin/{e['base']}" if e.get("rama_issue_atras") is not None else ""
            det.append(f"rama de la issue {e['rama_issue']}: {donde}{extra}")
        det.append(f"fetch {e['fetch']}")
        linea.append("  " + " · ".join(det))
        if e["cambios_muestra"]:
            linea.append("  cambios: " + ", ".join(e["cambios_muestra"]) + (" …" if e["cambios"] > len(e["cambios_muestra"]) else ""))
    linea.append("  → " + SUGERENCIA[e["accion"]].format(ruta=e.get("ruta") or e["repo"], base=e["base"], rama=e.get("rama_issue", "")))
    return "\n".join(linea)


def main(argv):
    base, rama, fetch, como_json, repos = "develop", None, True, False, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("--base", "--rama") and i + 1 < len(argv):
            base, rama = (argv[i + 1], rama) if a == "--base" else (base, argv[i + 1])
            i += 2
            continue
        if a == "--sistema" and i + 1 < len(argv):
            repos[:0] = hermanos(argv[i + 1])
            i += 2
            continue
        if a == "--sin-fetch":
            fetch = False
        elif a == "--json":
            como_json = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            repos.append(a)
        i += 1
    if not repos:
        print(__doc__, file=sys.stderr)
        return 2
    vistos, unicos = set(), []
    for r in repos:  # sin repetidos (el mismo repo por nombre y por ruta)
        clave = resolver(r) or r
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(r)
    estados = [estado(r, base, rama, fetch) for r in unicos]
    if como_json:
        print(json.dumps(estados, ensure_ascii=False, indent=1))
    else:
        print("\n".join(texto(e) for e in estados))
    acciones = {e["accion"] for e in estados}
    if acciones & {"no-existe", "sin-red"}:
        return 2
    return 0 if acciones <= {"al-dia"} else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except Exception as ex:  # nunca deja a la IA sin respuesta
        print(f"[estado_repos] error: {ex}", file=sys.stderr)
        sys.exit(2)
