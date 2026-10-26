#!/usr/bin/env python3
"""Corre las pruebas unitarias relacionadas con un conjunto de archivos cambiados.

Lo usan el pre-commit del equipo (archivos en stage) y el aviso de `contexto-proyecto` tras traer cambios de
otras personas (archivos de un rango de commits). Sólo corre lo relacionado con el cambio, no la suite completa.

  oas_pruebas.py --staged [--repo <dir>]          # archivos en stage (pre-commit)
  oas_pruebas.py --desde <commit> [--repo <dir>]  # archivos cambiados en <commit>..HEAD (tras un pull)

Soporta repos con Jest invocado desde `scripts.test` del package.json (MID, CRUD, root MF) y repos Go
(`go test` de los paquetes tocados). Los MF con `ng test` (Karma o builder de Angular) se omiten con aviso:
el builder no admite filtrar por archivos relacionados.

Códigos de salida:
  0  pasan, o no hay nada que probar
  1  hay pruebas que fallan (el pre-commit bloquea)
  2  no se pudo evaluar: runner roto (la suite no arranca), sin dependencias instaladas o tiempo agotado (aviso)
"""
import argparse
import json
import os
import re
import subprocess
import sys

EXT_JS = (".ts", ".js", ".mjs", ".cjs")
TIMEOUT = int(os.environ.get("OAS_PRUEBAS_TIMEOUT", "180"))
MAX_LISTA = 15


def git(*args, cwd=None):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def archivos_cambiados(repo, staged, desde):
    if staged:
        salida = git("diff", "--cached", "--name-only", "--diff-filter=ACMR", cwd=repo)
    else:
        salida = git("diff", "--name-only", "--diff-filter=ACMR", f"{desde}..HEAD", cwd=repo)
    return [f for f in salida.splitlines() if f and os.path.exists(os.path.join(repo, f))]


def script_test(repo):
    try:
        with open(os.path.join(repo, "package.json"), encoding="utf-8") as f:
            return (json.load(f).get("scripts") or {}).get("test", "")
    except Exception:
        return ""


def resultado(codigo, mensaje, detalle=()):
    return codigo, mensaje, list(detalle)


def correr(cmd, repo, env=None):
    try:
        r = subprocess.run(cmd, cwd=repo, shell=isinstance(cmd, str), capture_output=True, text=True,
                           timeout=TIMEOUT, env=env)
    except subprocess.TimeoutExpired:
        return None
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def jest(repo, script, archivos):
    codigo = [f for f in archivos if f.endswith(EXT_JS) and "node_modules/" not in f and not f.startswith("dist/")]
    if not codigo:
        return resultado(0, "sin archivos de código que probar")
    if not os.path.isdir(os.path.join(repo, "node_modules")):
        return resultado(2, "no hay node_modules: instala dependencias para correr las pruebas relacionadas")
    env = dict(os.environ, CI="true", PATH=os.path.join(repo, "node_modules", ".bin") + os.pathsep + os.environ.get("PATH", ""))
    cmd = f"{script} --findRelatedTests {' '.join(_shq(f) for f in codigo)} --passWithNoTests"
    r = correr(cmd, repo, env)
    if r is None:
        return resultado(2, f"las pruebas relacionadas superaron {TIMEOUT}s (OAS_PRUEBAS_TIMEOUT)")
    rc, out = r
    fallidos = sorted(set(re.findall(r"^\s*FAIL\s+(\S+)", out, re.M)))
    resumen = next((l.strip() for l in out.splitlines() if l.strip().startswith("Tests:")), "")
    if rc == 0:
        return resultado(0, f"pasan las pruebas relacionadas ({resumen or 'sin pruebas relacionadas'})")
    total = re.search(r"Tests:.*?(\d+) total", resumen)
    if "Test suite failed to run" in out and (not total or total.group(1) == "0"):
        return resultado(2, "la suite no arranca (configuración de pruebas rota, deuda preexistente): no se pudo evaluar",
                         [_primera_causa(out)])
    return resultado(1, f"fallan pruebas relacionadas con el cambio ({resumen or 'ver salida'})", fallidos[:MAX_LISTA])


def go(repo, archivos):
    paquetes = sorted({"./" + (os.path.dirname(f) or ".") for f in archivos if f.endswith(".go")})
    if not paquetes:
        return resultado(0, "sin archivos Go que probar")
    r = correr(["go", "test", *paquetes], repo)
    if r is None:
        return resultado(2, f"go test superó {TIMEOUT}s (OAS_PRUEBAS_TIMEOUT)")
    rc, out = r
    if rc == 0:
        return resultado(0, "pasan las pruebas de los paquetes tocados")
    fallidos = sorted(set(re.findall(r"^(?:FAIL|---\s*FAIL:)\s+(\S+)", out, re.M)))
    if not fallidos:
        return resultado(2, "go test no pudo compilar o ejecutar los paquetes", [_primera_causa(out)])
    return resultado(1, "fallan pruebas de los paquetes tocados", fallidos[:MAX_LISTA])


def _shq(s):
    return "'" + s.replace("'", "'\\''") + "'"


def _primera_causa(out):
    for l in out.splitlines():
        if re.search(r"Error|error:|cannot|failed", l) and "Test suite failed to run" not in l:
            return l.strip()[:160]
    return ""


def evaluar(repo, staged=False, desde=None):
    archivos = archivos_cambiados(repo, staged, desde)
    if not archivos:
        return resultado(0, "sin archivos cambiados")
    script = script_test(repo)
    if script:
        if re.search(r"\bng\s+test\b", script):
            return resultado(0, "el repo usa `ng test`: las pruebas relacionadas no se filtran por archivo (corre la suite antes del PR)")
        if re.search(r"\bjest\b", script):
            return jest(repo, script, archivos)
        return resultado(0, f"runner de pruebas no soportado (`{script[:60]}`): corre las pruebas a mano")
    if os.path.exists(os.path.join(repo, "go.mod")):
        return go(repo, archivos)
    return resultado(0, "el repo no define pruebas")


def main():
    p = argparse.ArgumentParser(description="Pruebas relacionadas con los archivos cambiados")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--staged", action="store_true")
    g.add_argument("--desde")
    p.add_argument("--repo", default=None)
    a = p.parse_args()
    repo = a.repo or git("rev-parse", "--show-toplevel") or os.getcwd()
    codigo, mensaje, detalle = evaluar(repo, a.staged, a.desde)
    print(f"[oas-pruebas] {mensaje}")
    for d in filter(None, detalle):
        print(f"   - {d}")
    sys.exit(codigo)


if __name__ == "__main__":
    main()
