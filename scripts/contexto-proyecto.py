#!/usr/bin/env python3
"""Detecta si el contexto local de un proyecto (.claude/) falta o quedó desactualizado
tras traer cambios (pull/merge/rebase/checkout) y le indica a Claude que lance el agente
`contexto-proyecto`. Funciona en cualquier proyecto: repos con historia, repos recién
clonados, `git init` sin commits y carpetas de proyecto sin git.

Uso:
  contexto-proyecto.py hook      # desde los hooks SessionStart / UserPromptSubmit / PostToolUse (JSON por stdin)
  contexto-proyecto.py estado    # muestra el estado actual (diagnóstico)
  contexto-proyecto.py marcar    # registra HEAD como sincronizado (lo llama el agente al terminar)
  contexto-proyecto.py excluir   # agrega .claude/ a .git/info/exclude (contexto sólo local)

Archivos de estado (dentro de <proyecto>/.claude/, nunca se versionan):
  .contexto-sync    commit hasta el cual el contexto está al día
  .contexto-off     si existe, el hook no hace nada en este proyecto
"""
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oas_config  # noqa: E402

SCRIPT = os.path.abspath(__file__)

MAX_ARCHIVOS = 60
MAX_COMMITS = 30

# Indicadores de que una carpeta sin git es un proyecto de código
MANIFIESTOS = (
    "package.json", "go.mod", "angular.json", "pom.xml", "build.gradle", "build.gradle.kts",
    "pyproject.toml", "requirements.txt", "setup.py", "Cargo.toml", "composer.json", "Gemfile",
    "Makefile", "CMakeLists.txt", "Dockerfile", "docker-compose.yml", "pubspec.yaml",
    "mix.exs", "deno.json", "tsconfig.json", "main.go",
)
NO_PROYECTO = {os.path.expanduser("~"), "/", "/tmp", tempfile.gettempdir()}

# Comandos git que pueden traer cambios ajenos o crear repos nuevos
RE_GIT = re.compile(r"\bgit\b[^;&|]*\b(clone|pull|merge|rebase|checkout|switch|reset|init|am|cherry-pick)\b")


def git(*args, cwd=None):
    try:
        r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def es_repo(root):
    return git("rev-parse", "--is-inside-work-tree", cwd=root) == "true"


def raiz_proyecto(cwd):
    """Raíz del repo git, o la carpeta misma si parece un proyecto sin git."""
    if not cwd or not os.path.isdir(cwd):
        return None
    top = git("rev-parse", "--show-toplevel", cwd=cwd)
    if top:
        return top
    cwd = os.path.realpath(cwd)
    if cwd in NO_PROYECTO:
        return None
    if any(os.path.exists(os.path.join(cwd, m)) for m in MANIFIESTOS) or os.path.isdir(os.path.join(cwd, "src")):
        return cwd
    return None


def rutas(root):
    claude = os.path.join(root, ".claude")
    return claude, os.path.join(claude, ".contexto-sync"), os.path.join(claude, ".contexto-off")


def tiene_contexto(root):
    claude = os.path.join(root, ".claude")
    return os.path.isfile(os.path.join(claude, "CLAUDE.md")) and os.path.isdir(os.path.join(claude, "docs"))


def tiene_archivos(root):
    """Evita generar contexto para un proyecto vacío (recién creado, sin código aún)."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "node_modules"]
        if any(not f.startswith(".") for f in filenames):
            return True
    return False


def head(root):
    return git("rev-parse", "--verify", "-q", "HEAD", cwd=root) if es_repo(root) else None


def marcar(root):
    claude, sync, _ = rutas(root)
    os.makedirs(claude, exist_ok=True)
    h = head(root)
    if h:
        with open(sync, "w") as f:
            f.write(h + "\n")
    return h


def excluir(root):
    if not es_repo(root):
        return False
    gitdir = git("rev-parse", "--git-common-dir", cwd=root)
    if not gitdir:
        return False
    if not os.path.isabs(gitdir):
        gitdir = os.path.join(root, gitdir)
    info = os.path.join(gitdir, "info")
    os.makedirs(info, exist_ok=True)
    exclude = os.path.join(info, "exclude")
    actual = open(exclude).read() if os.path.exists(exclude) else ""
    if ".claude/" not in actual.split():
        with open(exclude, "a") as f:
            f.write("\n# Documentación y configuración local de Claude Code\n.claude/\n")
    return True


def cambios_traidos(root, desde):
    """Commits en desde..HEAD que no son del usuario local, y archivos que tocan (fuera de .claude/)."""
    yo = (git("config", "user.email", cwd=root) or "").lower()
    log = git("log", "--no-merges", "--format=%H%x09%ae%x09%an%x09%s", f"{desde}..HEAD", cwd=root)
    if log is None:
        return None, None
    commits = []
    for linea in filter(None, log.splitlines()):
        h, email, autor, asunto = (linea.split("\t", 3) + ["", "", ""])[:4]
        if not yo or email.lower() != yo:
            commits.append((h, autor, asunto))
    archivos = set()
    for h, _, _ in commits:
        out = git("diff-tree", "--no-commit-id", "--name-only", "-r", h, cwd=root) or ""
        archivos.update(a for a in out.splitlines() if a and not a.startswith(".claude/"))
    return commits, sorted(archivos)


def ya_notificado(session_id, clave):
    """Evita repetir el aviso en la misma sesión para el mismo proyecto+HEAD."""
    marca = os.path.join(tempfile.gettempdir(), f"claude-contexto-{session_id or 'sin-sesion'}")
    previas = set(open(marca).read().split("\n")) if os.path.exists(marca) else set()
    if clave in previas:
        return True
    with open(marca, "a") as f:
        f.write(clave + "\n")
    return False


def revisar(root, sesion):
    """Devuelve el aviso para Claude sobre `root`, o None si no hay nada que hacer."""
    _, sync, off = rutas(root)
    if os.path.exists(off):
        return None
    h = head(root)

    if not tiene_contexto(root):
        if not tiene_archivos(root) or ya_notificado(sesion, f"{root}:sin-contexto"):
            return None
        origen = "repositorio git" if es_repo(root) else "proyecto (sin git)"
        return (
            f"[contexto-proyecto] El {origen} {root} no tiene contexto local (.claude/CLAUDE.md + .claude/docs/).\n"
            "Lanza el agente `contexto-proyecto` (subagent_type: contexto-proyecto) en segundo plano "
            f"con el prompt: \"MODO: generar. REPO: {root}. SCRIPT: {SCRIPT}\". Avísale al usuario en una línea y sigue con su tarea; "
            "si la tarea depende del contexto, espera a que el agente termine."
        )

    if not h:
        return None  # sin git o sin commits: no hay cambios traídos que detectar
    if not os.path.exists(sync):
        marcar(root)  # primer uso con contexto existente: se asume al día
        return None
    desde = open(sync).read().strip()
    if desde == h:
        return None

    desde_valido = desde if git("cat-file", "-e", f"{desde}^{{commit}}", cwd=root) is not None else None
    commits, archivos = cambios_traidos(root, desde_valido) if desde_valido else (None, None)

    if commits is not None and not archivos:
        marcar(root)  # sólo commits propios o sin cambios relevantes
        return None
    if ya_notificado(sesion, f"{root}:{h}"):
        return None

    if commits is None:
        rango = "desconocido"
        detalle = (f"El commit sincronizado ({desde[:8]}) ya no existe (rebase/force-push). "
                   "El agente debe revisar los cambios recientes con `git log` y decidir qué actualizar.")
    else:
        rango = f"{desde_valido}..{h}"
        lista_c = "\n".join(f"  - {c[:8]} {a}: {s}" for c, a, s in commits[:MAX_COMMITS])
        if len(commits) > MAX_COMMITS:
            lista_c += f"\n  - … y {len(commits) - MAX_COMMITS} más"
        lista_a = "\n".join(f"  - {a}" for a in archivos[:MAX_ARCHIVOS])
        if len(archivos) > MAX_ARCHIVOS:
            lista_a += f"\n  - … y {len(archivos) - MAX_ARCHIVOS} más"
        detalle = f"Commits traídos ({len(commits)}):\n{lista_c}\nArchivos tocados ({len(archivos)}):\n{lista_a}"

    return (
        f"[contexto-proyecto] Se detectaron cambios traídos (pull/merge/checkout) en {root} desde la última sincronización del contexto.\n"
        f"{detalle}\n"
        "ANTES de seguir con la tarea del usuario, lanza el agente `contexto-proyecto` (subagent_type: contexto-proyecto, "
        f"en primer plano) con el prompt: \"MODO: actualizar. REPO: {root}. RANGO: {rango}. SCRIPT: {SCRIPT}\". "
        "Cuando termine, resume en una línea qué documentos cambió y continúa con la tarea."
    )


def destinos_de_comando(comando, cwd):
    """Carpetas afectadas por un comando git ejecutado por Claude (incluye el destino de `git clone`)."""
    dirs = []
    base = cwd
    for parte in re.split(r"&&|\|\||;|\n", comando):
        try:
            tokens = shlex.split(parte)
        except ValueError:
            continue
        if not tokens:
            continue
        if tokens[0] == "cd" and len(tokens) > 1:
            base = os.path.normpath(os.path.join(base, os.path.expanduser(tokens[1])))
            continue
        if tokens[0] != "git":
            continue
        rest = tokens[1:]
        ctx = base
        while len(rest) >= 2 and rest[0] == "-C":  # git -C <dir> ...
            ctx = os.path.normpath(os.path.join(ctx, os.path.expanduser(rest[1])))
            rest = rest[2:]
        if not rest:
            continue
        if rest[0] == "clone":
            posicionales, i = [], 1
            con_valor = {"-b", "--branch", "-o", "--origin", "--depth", "--reference", "-c", "--config",
                         "--separate-git-dir", "-j", "--jobs", "--filter", "-u", "--upload-pack", "--template"}
            while i < len(rest):
                t = rest[i]
                if t in con_valor:
                    i += 2
                    continue
                if not t.startswith("-"):
                    posicionales.append(t)
                i += 1
            if posicionales:
                destino = posicionales[1] if len(posicionales) > 1 else \
                    re.sub(r"\.git$", "", posicionales[0].rstrip("/").split("/")[-1].split(":")[-1])
                dirs.append(os.path.normpath(os.path.join(ctx, os.path.expanduser(destino))))
        elif rest[0] == "init":
            pos = [t for t in rest[1:] if not t.startswith("-")]
            dirs.append(os.path.normpath(os.path.join(ctx, pos[0])) if pos else ctx)
        else:
            dirs.append(ctx)
    return dirs


def hook():
    try:
        datos = json.load(sys.stdin)
    except Exception:
        datos = {}
    evento = datos.get("hook_event_name", "UserPromptSubmit")
    cwd = datos.get("cwd") or os.getcwd()
    sesion = datos.get("session_id", "")

    candidatos = []
    if evento == "PostToolUse":
        comando = (datos.get("tool_input") or {}).get("command", "")
        if not RE_GIT.search(comando):
            return
        candidatos = destinos_de_comando(comando, cwd)
    candidatos.append(cwd)

    avisos, vistos = [], set()
    for d in candidatos:
        root = raiz_proyecto(d)
        if not root or root in vistos:
            continue
        vistos.add(root)
        aviso = revisar(root, sesion)
        if aviso:
            avisos.append(aviso)
    if avisos:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": evento, "additionalContext": oas_config.adaptar("\n\n".join(avisos))}}, ensure_ascii=False))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "hook"
    if cmd == "hook":
        try:
            hook()
        except Exception as e:  # un fallo del hook nunca debe bloquear a Claude
            print(f"[contexto-proyecto] error en hook: {e}", file=sys.stderr)
        return
    root = raiz_proyecto(os.getcwd()) or os.getcwd()
    if cmd == "marcar":
        h = marcar(root)
        print(f"Contexto sincronizado en {h}" if h else "Proyecto sin commits/git: nada que marcar.")
    elif cmd == "excluir":
        print(".claude/ excluido en .git/info/exclude" if excluir(root) else "No es repo git: nada que excluir.")
    elif cmd == "estado":
        _, sync, off = rutas(root)
        print(f"proyecto: {root}\ngit: {'sí' if es_repo(root) else 'no'}\n"
              f"contexto: {'sí' if tiene_contexto(root) else 'no'}\n"
              f"desactivado: {'sí' if os.path.exists(off) else 'no'}\n"
              f"sync: {open(sync).read().strip() if os.path.exists(sync) else '(sin marcar)'}\n"
              f"HEAD: {head(root) or '(sin commits)'}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
