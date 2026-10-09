#!/usr/bin/env python3
"""Hook UserPromptSubmit/SessionStart: si se trabaja bajo la carpeta udistrital, recuerda a Claude
qué skills/agentes son obligatorios según el tipo de repo (las reglas completas están en
<udistrital>/CLAUDE.md).

Carpeta raíz: ver oas_config.py (UDISTRITAL_DIR, ~/.config/oas-ai-tools/config.json o ~/go/src/github.com/udistrital).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import oas_config  # noqa: E402

RAIZ = oas_config.udistrital_dir()


def tipo_repo(cwd):
    top = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True)
    root = top.stdout.strip() if top.returncode == 0 else cwd
    nombre = os.path.basename(root)
    pkg = os.path.join(root, "package.json")
    deps = open(pkg).read() if os.path.exists(pkg) else ""
    if os.path.exists(os.path.join(root, "angular.json")):
        return nombre, "MF Angular", "/endpoint-oas si cambias rutas que consume; la lógica de backend va en el MID"
    stack = "Go/Beego" if os.path.exists(os.path.join(root, "go.mod")) else "NestJS" if "@nestjs/core" in deps else None
    if nombre.endswith("_crud") or "@nestjs/mongoose" in deps:
        return nombre, f"API CRUD ({stack or '?'})", "/crud-oas + /endpoint-oas"
    if nombre.endswith("_mid") or "@nestjs/axios" in deps:
        return nombre, f"API MID ({stack or '?'})", "/mid-oas + /endpoint-oas"
    return nombre, "carpeta de trabajo", "según el repo que toques: /crud-oas, /mid-oas, /endpoint-oas"


def main():
    try:
        datos = json.load(sys.stdin)
    except Exception:
        datos = {}
    cwd = os.path.realpath(datos.get("cwd") or os.getcwd())
    if cwd != RAIZ and not cwd.startswith(RAIZ + os.sep):
        return
    nombre, tipo, skills = tipo_repo(cwd)
    texto = (
        f"[reglas-udistrital] Repo `{nombre}` ({tipo}). Aplica sin esperar a que el usuario lo pida "
        f"(detalle en {RAIZ}/AGENTS.md): tarea nueva → /commit-oas (rama) y /planificar-issue (especificación aprobada antes de codificar); código → {skills}; "
        "al terminar de implementar → /seguridad-oas sobre el diff; commit → /commit-oas con confirmación; "
        "tarea cerrada → /documentar-cambios; lee .claude/docs antes de tocar un módulo. "
        "Si el mensaje del usuario no implica trabajo de código (pregunta, charla), ignora este recordatorio."
    )
    evento = datos.get("hook_event_name", "UserPromptSubmit")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": evento, "additionalContext": oas_config.adaptar(texto)}}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # nunca bloquear el prompt
        print(f"[reglas-udistrital] error: {e}", file=sys.stderr)
