#!/usr/bin/env python3
"""Verifica la calidad mecánica del contexto local de un repo (<REPO>/.claude/).

Uso:  python3 verificar_contexto.py <REPO> [--json]

Comprueba:
  - CLAUDE.md existe y tiene ≤ 80 líneas
  - cada documento de docs/ tiene ≤ 300 líneas (salvo los que tienen bloques generados)
  - todos los enlaces relativos de .claude/ resuelven (incluidos los que apuntan a otros repos)
  - todo documento de docs/ (primer nivel) aparece en docs/README.md
  - bloques <!-- generado:inicio ... --> / <!-- generado:fin --> balanceados
  - no hay valores con forma de secreto
Sale con 1 si hay errores.
"""
import json
import os
import re
import sys
from urllib.parse import unquote

MAX_CLAUDE = 80
MAX_DOC = 300
RE_LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
RE_FENCE = re.compile(r"^\s*(```|~~~)")
RE_INICIO = re.compile(r"<!--\s*generado:inicio\b")
RE_FIN = re.compile(r"<!--\s*generado:fin\s*-->")
SECRETOS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"\b(mongodb(\+srv)?|postgres(ql)?|mysql)://[^\s:/@${}<]+:[^\s@${}<]+@"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
]


def lineas_sin_codigo(texto):
    """Líneas fuera de bloques de código (los ejemplos/plantillas no se validan como enlaces)."""
    dentro = False
    for n, linea in enumerate(texto.splitlines(), 1):
        if RE_FENCE.match(linea):
            dentro = not dentro
            continue
        if not dentro:
            yield n, linea


def verificar(repo):
    repo = os.path.abspath(repo)
    base = os.path.join(repo, ".claude")
    docs = os.path.join(base, "docs")
    errores, avisos, stats = [], [], {"documentos": 0, "lineas": 0, "enlaces": 0}

    claude_md = os.path.join(base, "CLAUDE.md")
    if not os.path.isfile(claude_md):
        errores.append("Falta .claude/CLAUDE.md")
    else:
        n = len(open(claude_md, encoding="utf-8", errors="ignore").read().splitlines())
        if n > MAX_CLAUDE:
            errores.append(f"CLAUDE.md tiene {n} líneas (máximo {MAX_CLAUDE}): mueve el detalle a docs/")
    if not os.path.isdir(docs):
        errores.append("Falta .claude/docs/")
        return errores, avisos, stats
    readme = os.path.join(docs, "README.md")
    texto_readme = open(readme, encoding="utf-8", errors="ignore").read() if os.path.isfile(readme) else ""
    if not texto_readme:
        errores.append("Falta docs/README.md (índice)")

    archivos = [claude_md] if os.path.isfile(claude_md) else []
    for raiz, dirs, nombres in os.walk(docs):
        dirs[:] = [d for d in dirs if not d.startswith("docs.bak")]
        archivos += [os.path.join(raiz, n) for n in sorted(nombres) if n.endswith(".md")]

    for ruta in archivos:
        rel = os.path.relpath(ruta, repo)
        texto = open(ruta, encoding="utf-8", errors="ignore").read()
        lineas = texto.splitlines()
        stats["documentos"] += 1
        stats["lineas"] += len(lineas)
        inicios, fines = len(RE_INICIO.findall(texto)), len(RE_FIN.findall(texto))
        if inicios != fines:
            errores.append(f"{rel}: bloques generados desbalanceados ({inicios} inicio / {fines} fin)")
        es_doc = os.path.dirname(ruta) == docs and os.path.basename(ruta) != "README.md"
        if es_doc and not inicios and len(lineas) > MAX_DOC:
            errores.append(f"{rel}: {len(lineas)} líneas (máximo {MAX_DOC}); divídelo en subdominios o genera las tablas")
        if es_doc and os.path.basename(ruta) not in texto_readme:
            errores.append(f"{rel}: no aparece en docs/README.md")
        for n, linea in lineas_sin_codigo(texto):
            for destino in RE_LINK.findall(linea):
                if re.match(r"^[a-z]+:", destino) or destino.startswith("#"):
                    continue
                stats["enlaces"] += 1
                destino_archivo = unquote(destino.split("#", 1)[0])  # %20 = espacio en rutas
                if not destino_archivo:
                    continue
                objetivo = os.path.normpath(os.path.join(os.path.dirname(ruta), destino_archivo))
                if not os.path.exists(objetivo):
                    errores.append(f"{rel}:{n}: enlace roto → {destino}")
            for patron in SECRETOS:
                if patron.search(linea):
                    errores.append(f"{rel}:{n}: posible secreto en la documentación")
    if stats["documentos"] and not os.path.isdir(os.path.join(docs, "cambios")):
        avisos.append("Aún no hay docs/cambios/ (se crea con /documentar-cambios)")
    return errores, avisos, stats


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    errores, avisos, stats = verificar(sys.argv[1])
    if "--json" in sys.argv:
        print(json.dumps({"errores": errores, "avisos": avisos, "stats": stats}, ensure_ascii=False, indent=2))
    else:
        print(f"Contexto: {stats['documentos']} documentos, {stats['lineas']} líneas, {stats['enlaces']} enlaces")
        for a in avisos:
            print(f"  ! {a}")
        for e in errores:
            print(f"  ✖ {e}")
        print("✔ Verificación superada" if not errores else f"✖ {len(errores)} problema(s)")
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
