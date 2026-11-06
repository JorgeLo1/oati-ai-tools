#!/usr/bin/env python3
"""Pruebas del aviso de contexto-proyecto.py tras traer cambios (A2): cuándo pide MODO actualizar y cuándo
lanzar también el agente impacto-e2e. Repos sintéticos en una carpeta temporal; no toca repos reales.
Uso: python3 scripts/tests/test_contexto_proyecto.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "contexto-proyecto.py")
ok = fallos = 0


def git(repo, *args, autor=None):
    env = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null")
    if autor:
        env.update(GIT_AUTHOR_NAME=autor, GIT_AUTHOR_EMAIL=f"{autor}@x", GIT_COMMITTER_NAME=autor, GIT_COMMITTER_EMAIL=f"{autor}@x")
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True, env=env).stdout.strip()


def escribir(repo, archivos):
    for rel, texto in archivos.items():
        p = os.path.join(repo, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(texto)


def preparar(base, con_e2e):
    repo = os.path.join(base, f"demo_mf_{uuid.uuid4().hex[:6]}")
    os.makedirs(repo)
    git(repo, "init", "-q", "-b", "develop")
    git(repo, "config", "user.email", "yo@x")
    git(repo, "config", "user.name", "yo")
    git(repo, "config", "commit.gpgsign", "false")
    git(repo, "config", "core.hooksPath", "/dev/null")
    archivos = {"angular.json": "{}", "src/app/modules/plan/plan.component.html": "<button>Guardar</button>\n",
                ".claude/CLAUDE.md": "# ctx\n", ".claude/docs/README.md": "# docs\n"}
    if con_e2e:
        archivos.update({"e2e/playwright.config.ts": "export default {};\n", "e2e/tests/plan/x.spec.ts": "// @plan\n"})
    escribir(repo, archivos)
    open(os.path.join(repo, ".git", "info", "exclude"), "a").write(".claude/\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "feat: base")
    open(os.path.join(repo, ".claude", ".contexto-sync"), "w").write(git(repo, "rev-parse", "HEAD"))
    return repo


def aviso(repo):
    datos = {"hook_event_name": "UserPromptSubmit", "cwd": repo, "session_id": f"test-{uuid.uuid4().hex}"}
    r = subprocess.run(["python3", SCRIPT, "hook"], input=json.dumps(datos), capture_output=True, text=True)
    if not r.stdout.strip():
        return ""
    return json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]


def caso(nombre, base, con_e2e, cambios, autor, debe_actualizar, debe_e2e):
    global ok, fallos
    repo = preparar(base, con_e2e)
    escribir(repo, cambios)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "feat: cambio", autor=autor)
    texto = aviso(repo)
    obtenido = ("MODO: actualizar" in texto, "impacto-e2e" in texto)
    bien = obtenido == (debe_actualizar, debe_e2e)
    if bien and debe_e2e:
        bien = "ORIGEN: pull" in texto and "RANGO: " in texto and "MODULOS: plan" in texto
    ok += bien
    fallos += not bien
    print(f"{'✅' if bien else '❌'} {nombre}")
    if not bien:
        print(f"   esperado actualizar={debe_actualizar} e2e={debe_e2e}, obtenido {obtenido}\n   {texto[:400]}")


def main():
    base = tempfile.mkdtemp(prefix="oas-ctx-")
    try:
        html = {"src/app/modules/plan/plan.component.html": "<button>Registrar</button>\n"}
        caso("cambio de otra persona en un .html de un MF con e2e → actualizar + impacto-e2e", base, True, html, "otra", True, True)
        caso("cambio de otra persona en un MF sin e2e → sólo actualizar", base, False, html, "otra", True, False)
        caso("cambio propio → sin aviso", base, True, html, "yo", False, False)
        caso("sólo documentación → actualizar sin impacto-e2e", base, True, {"README.md": "# x\n"}, "otra", True, False)
        caso("cambio en e2e/pages de otra persona → impacto-e2e", base, True,
             {"e2e/pages/plan.page.ts": "export class PlanPage {}\n", "e2e/tests/plan/y.spec.ts": "// y\n"}, "otra", True, True)
        caso("textos de i18n → impacto-e2e", base, True,
             {"src/assets/i18n/es.json": "{}\n", "src/app/modules/plan/plan.component.ts": "export class A {}\n"}, "otra", True, True)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n{ok}/{ok + fallos} OK")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
