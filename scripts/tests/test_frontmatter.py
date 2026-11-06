#!/usr/bin/env python3
"""Revisa el frontmatter de skills/*/SKILL.md y agents/*.md (sólo stdlib, sin PyYAML).

Falla si:
  - falta el bloque `---` inicial o los campos `name` y `description`;
  - una `description` en línea sin comillas contiene ` #` (YAML la corta ahí: lo que sigue es comentario)
    o `: ` (YAML inválido: el cargador puede leerla distinto);
  - una `description` en bloque (`>-`, `>`, `|`) no tiene líneas indentadas;
  - el `name` de una skill no coincide con su carpeta.
Uso: python3 scripts/tests/test_frontmatter.py   (sale con 1 si algo falla)
"""
import glob
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LIMITE = 1024  # caracteres de la descripción; más larga, pesa en el contexto de cada sesión


def campos(cab):
    """{campo: valor} del frontmatter, uniendo los bloques `>-`/`|` indentados."""
    out, actual = {}, None
    for linea in cab.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s?(.*)$", linea)
        if m:
            actual = m.group(1)
            out[actual] = {"crudo": m.group(2), "bloque": []}
        elif actual and linea.startswith((" ", "\t")):
            out[actual]["bloque"].append(linea.strip())
    return out


def revisar(ruta):
    errores = []
    texto = open(ruta, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", texto, re.S)
    if not m:
        return ["sin frontmatter `---`"]
    c = campos(m.group(1))
    for requerido in ("name", "description"):
        if requerido not in c:
            errores.append(f"falta `{requerido}`")
    if "description" in c:
        d = c["description"]
        crudo = d["crudo"].strip()
        if crudo in (">-", ">", "|", "|-", ">+", "|+"):
            if not d["bloque"]:
                errores.append("description en bloque sin líneas indentadas")
            valor = " ".join(d["bloque"])
        elif crudo[:1] in ("'", '"'):
            valor = crudo.strip("'\"")
        else:
            valor = crudo
            if " #" in crudo:
                errores.append(f"description sin comillas con ` #` (YAML la corta en «{crudo[max(0, crudo.index(' #') - 25):crudo.index(' #') + 3]}»): usa `description: >-`")
            if ": " in crudo:
                errores.append("description sin comillas con `: ` (YAML inválido): usa `description: >-`")
        if len(valor) > LIMITE:
            errores.append(f"description de {len(valor)} caracteres (máximo {LIMITE})")
    if "/skills/" in ruta and "name" in c:
        carpeta = os.path.basename(os.path.dirname(ruta))
        if c["name"]["crudo"].strip() != carpeta:
            errores.append(f"name `{c['name']['crudo'].strip()}` distinto de la carpeta `{carpeta}`")
    return errores


def main():
    archivos = sorted(glob.glob(os.path.join(RAIZ, "skills", "*", "SKILL.md")) + glob.glob(os.path.join(RAIZ, "agents", "*.md")))
    fallos = 0
    for ruta in archivos:
        errores = revisar(ruta)
        rel = os.path.relpath(ruta, RAIZ)
        if errores:
            fallos += 1
            for e in errores:
                print(f"❌ {rel}: {e}")
        else:
            print(f"✅ {rel}")
    print(f"\n{len(archivos) - fallos}/{len(archivos)} OK")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
