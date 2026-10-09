#!/usr/bin/env python3
"""Pruebas de verificar_contexto.py con contextos sintéticos. Uso: python3 scripts/tests/test_verificar_contexto.py"""
import os, shutil, subprocess, sys, tempfile

V = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verificar_contexto.py")
ok = fallos = 0


def contexto(base, archivos):
    for rel, texto in archivos.items():
        p = os.path.join(base, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(texto)


def caso(nombre, archivos, pasa, contiene=""):
    global ok, fallos
    d = tempfile.mkdtemp()
    try:
        contexto(d, archivos)
        r = subprocess.run(["python3", V, d], capture_output=True, text=True)
        bien = (r.returncode == 0) == pasa and contiene in r.stdout
        ok += bien; fallos += not bien
        print(f"{'✅' if bien else '❌'} {nombre}")
        if not bien:
            print("   " + r.stdout.replace("\n", "\n   "))
    finally:
        shutil.rmtree(d)


BASE = {".claude/CLAUDE.md": "# R\n[índice](docs/README.md)\n", ".claude/docs/README.md": "- [00](00-arquitectura.md)\n",
        ".claude/docs/00-arquitectura.md": "# A\n[main](../../src/main.ts)\n", "src/main.ts": "x"}
caso("contexto válido", BASE, True)
caso("CLAUDE.md demasiado largo", {**BASE, ".claude/CLAUDE.md": "x\n" * 81}, False, "CLAUDE.md tiene 81")
caso("documento de más de 300 líneas", {**BASE, ".claude/docs/00-arquitectura.md": "x\n" * 301}, False, "301 líneas")
caso("documento largo con bloque generado (exento)", {**BASE, ".claude/docs/00-arquitectura.md":
     "<!-- generado:inicio python3 x.py -->\n" + "x\n" * 400 + "<!-- generado:fin -->\n"}, True)
caso("bloque generado sin cierre", {**BASE, ".claude/docs/00-arquitectura.md": "<!-- generado:inicio x -->\n"}, False, "desbalanceados")
caso("enlace roto", {**BASE, ".claude/docs/00-arquitectura.md": "[x](../../src/no-existe.ts)\n"}, False, "enlace roto")
caso("enlace con %20 a carpeta con espacio", {**BASE, ".claude/docs/00-arquitectura.md": "[x](../../src/%20carpeta/a.ts)\n",
     "src/ carpeta/a.ts": "x"}, True)
caso("enlace dentro de bloque de código no se valida", {**BASE, ".claude/docs/00-arquitectura.md": "```\n[x](no-existe.md)\n```\n"}, True)
caso("documento fuera del índice", {**BASE, ".claude/docs/02-dominio.md": "# D\n"}, False, "no aparece en docs/README.md")
caso("secreto en la documentación", {**BASE, ".claude/docs/00-arquitectura.md": "mongodb://admin:clave@host/db\n"}, False, "posible secreto")
caso("falta CLAUDE.md", {k: v for k, v in BASE.items() if k != ".claude/CLAUDE.md"}, False, "Falta .claude/CLAUDE.md")
print(f"\n{ok}/{ok + fallos} OK")
sys.exit(1 if fallos else 0)
