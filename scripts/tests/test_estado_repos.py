#!/usr/bin/env python3
"""Pruebas de estado_repos.py con un remoto local (bare) y clones sintéticos; no toca repos reales ni la red.
Uso: python3 scripts/tests/test_estado_repos.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "estado_repos.py")
ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
           GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
ok = fallos = 0


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, env=ENV)


def commit(repo, archivo, texto="x"):
    open(os.path.join(repo, archivo), "w").write(texto)
    git(repo, "add", archivo)
    git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", f"feat: {archivo}")


def clonar(base, origen, nombre):
    destino = os.path.join(base, nombre)
    git(base, "clone", "-q", origen, destino)
    git(destino, "config", "core.hooksPath", "/dev/null")
    return destino


def correr(*args, env=None):
    r = subprocess.run(["python3", SCRIPT, "--json", *args], capture_output=True, text=True, env=env or ENV)
    return r.returncode, json.loads(r.stdout) if r.stdout.strip() else []


def caso(nombre, args, accion, salida, extra=None):
    global ok, fallos
    codigo, estados = correr(*args)
    e = estados[0] if estados else {}
    bien = e.get("accion") == accion and codigo == salida and all(e.get(k) == v for k, v in (extra or {}).items())
    ok += bien
    fallos += not bien
    print(f"{'✅' if bien else '❌'} {nombre}")
    if not bien:
        print(f"   esperado accion={accion} salida={salida} {extra or ''}; obtenido salida={codigo} {json.dumps(e, ensure_ascii=False)[:500]}")


def sistema(nombre, args, env, esperados):
    global ok, fallos
    _, estados = correr("--sin-fetch", *args, env=env)
    u = env["UDISTRITAL_DIR"]
    obtenidos = [os.path.relpath(e["ruta"], u) for e in estados]
    bien = obtenidos == esperados
    ok += bien
    fallos += not bien
    print(f"{'✅' if bien else '❌'} {nombre}")
    if not bien:
        print(f"   esperado {esperados}\n   obtenido {obtenidos}")


def main():
    base = tempfile.mkdtemp(prefix="oas-estado-")
    try:
        # remoto con develop y una rama de issue
        semilla = os.path.join(base, "semilla")
        os.makedirs(semilla)
        git(semilla, "init", "-q", "-b", "develop")
        commit(semilla, "a.ts")
        remoto = os.path.join(base, "remoto.git")
        git(base, "clone", "-q", "--bare", semilla, remoto)

        al_dia = clonar(base, remoto, "repo_al_dia")
        caso("en develop y al día", [al_dia], "al-dia", 0)

        atrasado = clonar(base, remoto, "repo_atrasado")
        otro = clonar(base, remoto, "repo_otro")  # empuja commits nuevos al remoto
        commit(otro, "b.ts")
        commit(otro, "c.ts")
        git(otro, "push", "-q", "origin", "develop")
        caso("en develop con 2 commits por traer", [atrasado], "actualizar", 1, {"base_atras": 2})
        caso("--sin-fetch no ve lo nuevo del remoto", ["--sin-fetch", al_dia], "al-dia", 0)

        en_otra = clonar(base, remoto, "repo_en_otra")
        git(en_otra, "checkout", "-q", "-b", "feature/otra-cosa")
        caso("en otra rama sin cambios → ir a develop", [en_otra], "ir-a-base", 1)

        sucio = clonar(base, remoto, "repo_sucio")
        open(os.path.join(sucio, "a.ts"), "w").write("cambio local")
        caso("cambios sin commitear → el usuario decide", [sucio], "cambios-pendientes", 1,
             {"cambios": 1, "cambios_muestra": ["a.ts"]})

        # rama de la issue en el remoto
        git(otro, "checkout", "-q", "-b", "feature/zz-issue")
        commit(otro, "d.ts")
        git(otro, "push", "-q", "origin", "feature/zz-issue")
        en_develop = clonar(base, remoto, "repo_retomar")
        git(en_develop, "checkout", "-q", "-b", "feature/x")
        caso("retomar: la rama de la issue existe en el remoto → ir a ella", ["--rama", "feature/zz-issue", en_develop],
             "ir-a-rama-issue", 1, {"rama_issue_remota": True, "rama_issue_local": False})
        git(en_develop, "checkout", "-q", "feature/zz-issue")
        caso("retomar: ya en la rama de la issue", ["--rama", "feature/zz-issue", en_develop], "rama-issue", 1)

        divergente = clonar(base, remoto, "repo_divergente")
        commit(divergente, "local.ts")
        caso("develop local con commits que no están en el remoto", [divergente], "base-divergente", 1, {"base_adelante": 1})

        sin_remoto = os.path.join(base, "repo_sin_remoto")
        os.makedirs(sin_remoto)
        git(sin_remoto, "init", "-q", "-b", "develop")
        commit(sin_remoto, "a.ts")
        caso("sin remoto origin", [sin_remoto], "sin-remoto", 1)

        caso("repo que no existe", [os.path.join(base, "no_existe")], "no-existe", 2)

        # --sistema: hermanos por prefijo dentro de la carpeta del sistema
        u = os.path.join(base, "udistrital")
        for rel in ("SIS/Frontend/demo_mf", "SIS/Backend/demo_mid", "SIS/Backend/demo_crud", "SIS/Backend/demo_crud_serverless",
                    "SIS/Backend/otro_mid", "SIS/Backend/demo", "OTRO/Backend/demo_crud", "raiz_mid", "raiz_crud"):
            os.makedirs(os.path.dirname(os.path.join(u, rel)), exist_ok=True)
            git(base, "clone", "-q", remoto, os.path.join(u, rel))
        env_u = dict(ENV, UDISTRITAL_DIR=u)
        sistema("--sistema desde el MF trae el MID y el CRUD del mismo sistema (no otro_mid, demo ni OTRO/)",
                ["--sistema", os.path.join(u, "SIS/Frontend/demo_mf")], env_u,
                ["SIS/Backend/demo_crud", "SIS/Backend/demo_crud_serverless", "SIS/Backend/demo_mid", "SIS/Frontend/demo_mf"])
        sistema("--sistema por nombre y un repo compartido extra, sin repetidos",
                ["--sistema", "demo_mid", "otro_mid", os.path.join(u, "SIS/Backend/demo_mid")], env_u,
                ["SIS/Backend/demo_crud", "SIS/Backend/demo_crud_serverless", "SIS/Backend/demo_mid", "SIS/Frontend/demo_mf",
                 "SIS/Backend/otro_mid"])
        sistema("--sistema con repos en la raíz de udistrital", ["--sistema", os.path.join(u, "raiz_mid")], env_u,
                ["raiz_crud", "raiz_mid"])
        sistema("--sistema con un repo sin sufijo de tipo: sólo él", ["--sistema", os.path.join(u, "SIS/Backend/demo")], env_u,
                ["SIS/Backend/demo"])
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print(f"\n{ok}/{ok + fallos} OK")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
