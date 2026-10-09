#!/usr/bin/env python3
"""
Hook PreToolUse (Bash) que protege el flujo git de los lineamientos OAS.

- git push / gh pr create          -> se bloquean (los hace el usuario manualmente).
- git commit con atribución de IA   -> se bloquea si el MENSAJE contiene Co-Authored-By, Claude, Anthropic,
                                      "Generated with", 🤖, IA, AI o LLM (no se mira el resto del comando).
- git commit                        -> pide confirmación al usuario (debe pasar por /commit-oas).
- git pull / git rebase / git reset --hard -> piden confirmación.
- --no-verify (o -n en commit)       -> se bloquea: saltaría los hooks de git del equipo.

Sólo reacciona a comandos git reales (analizados con shell_cmd: comillas, heredocs, `bash -c`, `git -C`,
alias de git), no a textos que mencionen esas palabras. Si el comando no se puede analizar, usa
la detección por texto (más estricta).

Lee el JSON del hook por stdin y responde con permissionDecision; sin salida = sin intervención.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shell_cmd  # noqa: E402

GIT = r"\bgit(?:\s+-[cC]\s+\S+)*\s+"
ATRIBUCION = re.compile(r"co-authored-by|claude|anthropic|generated with|noreply@anthropic|🤖", re.IGNORECASE)
ATRIBUCION_SIGLAS = re.compile(r"\b(IA|AI|LLM)\b", re.IGNORECASE)  # igual que la regla 0.8 de /commit-oas
PESO = {"ask": 1, "deny": 2}


def mensaje_commit(seg, args):
    """Texto del mensaje de un commit: -m/--message, -F/--file (archivo o heredoc) y heredocs del segmento."""
    partes, i = [], 0
    while i < len(args):
        a = args[i]
        if a in ("-m", "--message", "-F", "--file") and i + 1 < len(args):
            valor = args[i + 1]
            if a in ("-F", "--file"):
                if valor == "-":
                    partes.append(seg.heredoc)
                else:
                    ruta = os.path.join(seg.cwd, os.path.expanduser(valor))
                    if os.path.isfile(ruta):
                        partes.append(open(ruta, errors="ignore").read())
            else:
                partes.append(valor)
            i += 2
            continue
        if a.startswith("--message=") or a.startswith("--file="):
            partes.append(a.split("=", 1)[1])
        elif re.match(r"^-[A-Za-z]*m.+", a):  # -m"texto" o -am"texto"
            partes.append(a[a.index("m") + 1:])
        i += 1
    partes.append(seg.heredoc)
    return "\n".join(p for p in partes if p)


def tiene_atribucion(texto):
    return bool(ATRIBUCION.search(texto) or ATRIBUCION_SIGLAS.search(texto))


def responder(decision: str, razon: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": razon,
        }
    }, ensure_ascii=False))
    sys.exit(0)


def acciones(comando: str, cwd: str):
    """Lista de (subcomando, args, mensaje_de_commit) git y la marca 'gh-pr-create'."""
    segs = shell_cmd.segmentos(comando, cwd)
    if segs is None:  # no analizable: detección por texto
        out = []
        for sub in ("push", "commit", "pull", "rebase"):
            if re.search(GIT + sub + r"\b", comando):
                out.append((sub, [], comando))
        if re.search(GIT + r"reset\s+(?:\S+\s+)*--hard\b", comando):
            out.append(("reset", ["--hard"], ""))
        if re.search(r"\bgh\s+pr\s+create\b", comando):
            out.append(("gh-pr-create", [], ""))
        return out
    out = []
    for s in segs:
        g = shell_cmd.git_subcomando(s)
        if g:
            # los heredocs dentro de comillas ($(cat <<'EOF' … EOF)) no quedan en el segmento: se suman todos
            cuerpos = "\n".join(shell_cmd._quitar_heredocs(comando)[1])
            out.append((g[0], g[1], mensaje_commit(s, g[1]) + "\n" + cuerpos if g[0] == "commit" else ""))
        elif s.prog == "gh" and s.args[:2] == ["pr", "create"]:
            out.append(("gh-pr-create", [], ""))
    return out


def main() -> None:
    try:
        datos = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    comando = (datos.get("tool_input") or {}).get("command") or ""
    if not comando:
        sys.exit(0)
    cwd = datos.get("cwd") or os.getcwd()

    peor = None
    if re.search(r"(^|[\s;&|(])OAS_HOOKS_OMITIR=", comando):
        responder("deny", "OAS_HOOKS_OMITIR es un escape sólo para personas: la IA no puede saltarse los hooks de git del equipo.")
    for sub, args, mensaje in acciones(comando, cwd):
        res = None
        if sub == "push":
            res = ("deny", "git push está bloqueado: el push lo hace el usuario manualmente.")
        elif sub == "gh-pr-create":
            res = ("deny", "gh pr create está bloqueado: el PR lo abre el usuario manualmente.")
        elif sub in ("commit", "push", "merge", "rebase", "am", "cherry-pick") and any(
                x == "--no-verify" or (sub == "commit" and re.match(r"^-[A-Za-z]*n[A-Za-z]*$", x)) for x in args):
            res = ("deny", f"git {sub} con --no-verify/-n está bloqueado: saltaría los hooks de git del equipo "
                           "(etiquetas OAS, ramas, secretos). Corrige lo que el hook reporta.")
        elif sub == "commit":
            if tiene_atribucion(mensaje):
                res = ("deny", "Commit bloqueado: el mensaje contiene atribución a Claude/IA "
                               "(lineamiento OAS, regla 0.8 de /commit-oas). Quitar Co-Authored-By y menciones.")
            else:
                res = ("ask", "git commit: confirmar (los commits se hacen con /commit-oas y aprobación del usuario).")
        elif sub == "pull":
            res = ("ask", "git pull: confirmar antes de traer cambios del remoto.")
        elif sub == "rebase":
            res = ("ask", "git rebase: confirmar antes de reescribir el historial.")
        elif sub == "reset" and "--hard" in args:
            res = ("ask", "git reset --hard: descarta cambios; confirmar.")
        if res and (peor is None or PESO[res[0]] > PESO[peor[0]]):
            peor = res
    if peor:
        responder(*peor)
    sys.exit(0)


if __name__ == "__main__":
    main()
