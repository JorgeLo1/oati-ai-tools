#!/usr/bin/env python3
"""Ejecuta spec/casos.json contra los guardianes de Claude Code (skill-guard.py y git-guard.py).

Uso:  python3 scripts/tests/run_casos.py [-v] [ID ...]
Crea una carpeta udistrital temporal con repos sintéticos (UDISTRITAL_DIR apunta a ella), traduce cada caso
al protocolo de hooks de Claude Code y compara la decisión. No toca repos reales. Sale con 1 si algún caso falla.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid

RAIZ_HERRAMIENTAS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(RAIZ_HERRAMIENTAS, "scripts")
CASOS = os.path.join(RAIZ_HERRAMIENTAS, "spec", "casos.json")
DECISION = {"deny": "bloquear", "block": "bloquear", "ask": "confirmar", None: "permitir"}


def preparar_entorno(base, entorno):
    u = os.path.join(base, "udistrital")
    os.makedirs(os.path.join(u, ".claude", "specs"))
    repos = {}
    for clave, r in entorno["repos"].items():
        ruta = os.path.join(u, r["nombre"])
        os.makedirs(ruta)
        subprocess.run(["git", "init", "-q", "-b", r["rama"], ruta], check=True)
        for rel, contenido in r.get("archivos", {}).items():
            os.makedirs(os.path.dirname(os.path.join(ruta, rel)), exist_ok=True)
            open(os.path.join(ruta, rel), "w").write(contenido)
        for alias, valor in r.get("alias", {}).items():
            subprocess.run(["git", "-C", ruta, "config", f"alias.{alias}", valor], check=True)
        repos[clave] = ruta
    return u, repos


def sustituir(texto, mapa):
    if not isinstance(texto, str):
        return texto
    for k, v in mapa.items():
        texto = texto.replace(k, v)
    return texto


def spec(estado, repos):
    return (f"---\nissue: x#9\ntitulo: t\nrama: feature/zz-prueba\nrepos: [{', '.join(repos)}]\n"
            f"estado: {estado}\nactualizado: 2026-10-08\n---\n# T\n")


def transcript(base, sesion):
    p = os.path.join(base, f"t-{uuid.uuid4().hex}.jsonl")
    lineas = []

    def skill(s):
        lineas.append({"message": {"content": [{"type": "tool_use", "name": "Skill", "input": {"skill": s}}]}})

    for s in sesion.get("skills", []):
        skill(s)
    for i, (preg, resp) in enumerate(sesion.get("respuestas", [])):
        tid = f"ask{i}-{uuid.uuid4().hex[:8]}" if "id" not in sesion else f"ask{i}-{sesion['id']}"
        lineas.append({"message": {"content": [{"type": "tool_use", "name": "AskUserQuestion", "id": tid, "input": {}}]}})
        lineas.append({"toolUseResult": {"questions": [], "answers": {preg: resp}},
                       "message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": "ok"}]}})
    for cmd, salida in sesion.get("comandos", []):
        tid = uuid.uuid4().hex
        lineas.append({"message": {"content": [{"type": "tool_use", "name": "Bash", "id": tid, "input": {"command": cmd}}]}})
        lineas.append({"message": {"content": [{"type": "tool_result", "tool_use_id": tid, "content": salida}]}})
    for s in sesion.get("skills_despues", []):
        skill(s)
    with open(p, "w") as f:
        f.write("\n".join(json.dumps(x, ensure_ascii=False) for x in lineas) + "\n")
    return p


def ejecutar(caso, mapa, base, nonce, env):
    sesion = caso.get("sesion", {})
    sid = f"casos-{nonce}-{sesion.get('id', caso['id'])}"
    datos = {"session_id": sid, "transcript_path": transcript(base, sesion), "cwd": sustituir(caso.get("cwd", "{MF}"), mapa)}
    ev = caso["evento"]
    if ev in ("edicion", "escritura"):
        datos["tool_name"] = "Edit" if ev == "edicion" else "Write"
        archivo = sustituir(caso["archivo"], mapa)
        nuevo = sustituir(caso.get("nuevo", ""), mapa)
        if nuevo.startswith("{SPEC:"):
            _, est, repos = nuevo.strip("{}").split(":")
            nuevo = spec(est, repos.split(","))
        datos["tool_input"] = {"file_path": archivo, "content": nuevo} if ev == "escritura" else \
            {"file_path": archivo, "old_string": sustituir(caso.get("viejo", ""), mapa), "new_string": nuevo}
        args = ["skill-guard.py", "pre-edit"]
    elif ev == "lectura":
        datos["tool_input"] = {"file_path": sustituir(caso["archivo"], mapa)}
        args = ["skill-guard.py", "pre-read"]
    elif ev == "comando":
        datos["tool_input"] = {"command": sustituir(caso["comando"], mapa)}
        args = ["git-guard.py"] if caso.get("componente") == "git" else ["skill-guard.py", "pre-bash"]
    elif ev == "fin_de_turno":
        args = ["skill-guard.py", "stop"]
    else:
        raise ValueError(f"evento desconocido: {ev}")
    r = subprocess.run(["python3", os.path.join(SCRIPTS, args[0]), *args[1:]], input=json.dumps(datos),
                       capture_output=True, text=True, env=env)
    salida = r.stdout.strip()
    if not salida:
        return "permitir", r.stderr.strip()
    j = json.loads(salida)
    d = (j.get("hookSpecificOutput") or {}).get("permissionDecision") or j.get("decision")
    razon = (j.get("hookSpecificOutput") or {}).get("permissionDecisionReason") or j.get("reason") or ""
    return DECISION.get(d, d), razon


def main():
    verbose = "-v" in sys.argv
    filtro = [a for a in sys.argv[1:] if not a.startswith("-")]
    data = json.load(open(CASOS))
    base = tempfile.mkdtemp(prefix="oas-casos-")
    nonce = uuid.uuid4().hex[:8]
    try:
        u, repos = preparar_entorno(base, data["entorno"])
        env = dict(os.environ, UDISTRITAL_DIR=u)
        env.pop("CLAUDE_PLUGIN_ROOT", None)
        mapa = {"{SPECS}": os.path.join(u, ".claude", "specs"), "{U}": u,
                "{CONFIG_IA}": os.path.expanduser("~/.claude"), "{HERRAMIENTAS}": RAIZ_HERRAMIENTAS}
        mapa.update({"{" + k + "}": v for k, v in repos.items()})
        ok, fallos = 0, []
        for caso in data["casos"]:
            if filtro and caso["id"] not in filtro:
                continue
            prep = caso.get("preparacion", {})
            spec_path = None
            if "spec" in prep:
                spec_path = os.path.join(mapa["{SPECS}"], prep["spec"]["archivo"])
                open(spec_path, "w").write(spec(prep["spec"]["estado"], prep["spec"]["repos"]))
            if "staged" in prep:
                rp = repos[prep["staged"]["repo"]]
                open(os.path.join(rp, prep["staged"]["archivo"]), "w").write("x")
                subprocess.run(["git", "-C", rp, "add", prep["staged"]["archivo"]], check=True)
            obtenido, razon = ejecutar(caso, mapa, base, nonce, env)
            if "staged" in prep:
                rp = repos[prep["staged"]["repo"]]
                subprocess.run(["git", "-C", rp, "rm", "-q", "--cached", prep["staged"]["archivo"]], check=True)
                os.remove(os.path.join(rp, prep["staged"]["archivo"]))
            for f in os.listdir(mapa["{SPECS}"]):  # cada caso parte sin especificaciones
                os.remove(os.path.join(mapa["{SPECS}"], f))
            bien = obtenido == caso["esperado"]
            ok += bien
            if not bien:
                fallos.append(caso["id"])
            print(f"{'✅' if bien else '❌'} {caso['id']} {caso['titulo']}: esperado={caso['esperado']} obtenido={obtenido}")
            if verbose or not bien:
                if razon:
                    print(f"     ↳ {razon[:220]}")
        total = ok + len(fallos)
        print(f"\n{ok}/{total} OK" + (f" — FALLOS: {', '.join(fallos)}" if fallos else ""))
        return 1 if fallos else 0
    finally:
        shutil.rmtree(base, ignore_errors=True)
        for zz in ("/tmp/zz-oas.txt", "/tmp/zz-oas.md"):
            if os.path.exists(zz):
                os.remove(zz)
        tmp = tempfile.gettempdir()
        for m in os.listdir(tmp):
            if m.startswith(f"claude-skill-guard-aprob-casos-{nonce}"):
                os.remove(os.path.join(tmp, m))


if __name__ == "__main__":
    sys.exit(main())
