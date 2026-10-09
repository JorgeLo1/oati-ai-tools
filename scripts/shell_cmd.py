#!/usr/bin/env python3
"""Análisis de comandos de shell para los hooks (git-guard, skill-guard).

Separa un comando en segmentos ejecutables (respetando comillas y heredocs), identifica el
programa de cada segmento, los subcomandos de git (con opciones globales y alias) y los archivos
que el comando escribe o lee. No ejecuta nada.
"""
import os
import re
import shlex
import subprocess

SEPARADORES = {";", "&&", "||", "|", "&", "|&", ";;", "(", ")", "\n", "{", "}"}
PREFIJOS = {"sudo", "command", "exec", "time", "nohup", "env", "nice", "timeout", "xargs", "builtin"}
SHELLS = {"bash", "sh", "zsh", "dash"}
INTERPRETES = {"python", "python3", "node", "perl", "ruby", "deno", "bun"}
RE_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][\w-]*)\1")
RE_ASIGNACION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Señales de escritura en código inline de intérpretes
RE_ESCRITURA_INLINE = re.compile(
    r"open\([^)]*,\s*['\"][wax+]|\.write_text\(|\.write_bytes\(|writeFile|appendFile|createWriteStream|"
    r"shutil\.|os\.(remove|rename|replace|unlink)|\.unlink\(|unlinkSync|renameSync|rmSync|File\.write|>\s*\S")
RE_RUTA_INLINE = re.compile(r"""['"]([^'"\s]+)['"]""")


class Segmento:
    def __init__(self, tokens, cwd, heredoc=""):
        self.tokens = tokens
        self.cwd = cwd
        self.heredoc = heredoc
        args = list(tokens)
        while args and (RE_ASIGNACION.match(args[0]) or args[0] in PREFIJOS):
            prefijo = args.pop(0)
            if prefijo in PREFIJOS:
                while args and args[0].startswith("-"):  # opciones de sudo/env/timeout/xargs
                    opcion = args.pop(0)
                    if opcion in ("-n", "-P", "-L", "-s", "-u", "-g", "-k", "-d") and args:  # opciones con valor
                        args.pop(0)
                if prefijo in ("timeout", "nice") and args and re.match(r"^[\d.]+[smhd]?$", args[0]):
                    args.pop(0)
        self.prog = os.path.basename(args[0]) if args else ""
        self.args = args[1:]


def _quitar_heredocs(cmd):
    """Devuelve (comando sin cuerpos de heredoc, lista de cuerpos en orden)."""
    lineas = cmd.split("\n")
    salida, cuerpos, i = [], [], 0
    while i < len(lineas):
        linea = lineas[i]
        salida.append(linea)
        marcas = RE_HEREDOC.findall(linea)
        i += 1
        for _, delim in marcas:
            cuerpo = []
            while i < len(lineas) and lineas[i].strip() != delim:
                cuerpo.append(lineas[i])
                i += 1
            i += 1  # salta el delimitador
            cuerpos.append("\n".join(cuerpo))
    return "\n".join(salida), cuerpos


def _tokens(texto):
    lex = shlex.shlex(texto, posix=True, punctuation_chars=";&|()<>\n")
    lex.whitespace = " \t\r"
    lex.whitespace_split = True
    lex.commenters = ""
    return list(lex)


def segmentos(cmd, cwd):
    """Lista de Segmento. Sigue los `cd` para resolver el directorio de cada segmento.
    Devuelve None si el comando no se puede analizar (comillas sin cerrar, etc.)."""
    sin_heredoc, cuerpos = _quitar_heredocs(cmd)
    try:
        toks = _tokens(sin_heredoc)
    except ValueError:
        return None
    resultado, actual, dir_actual = [], [], cwd
    heredocs = iter(cuerpos)

    def cerrar():
        nonlocal actual, dir_actual
        if not actual:
            return
        cuerpo = ""
        if "<<" in actual or "<<-" in actual:
            cuerpo = next(heredocs, "")
        seg = Segmento([t for t in actual], dir_actual, cuerpo)
        resultado.append(seg)
        if seg.prog == "cd":
            destino = next((a for a in seg.args if not a.startswith("-")), os.path.expanduser("~"))
            dir_actual = os.path.normpath(os.path.join(dir_actual, os.path.expanduser(destino)))
        if seg.prog in SHELLS or seg.prog == "eval":
            interno = None
            if seg.prog == "eval":
                interno = " ".join(seg.args)
            elif "-c" in seg.args:
                idx = seg.args.index("-c")
                interno = seg.args[idx + 1] if idx + 1 < len(seg.args) else None
            elif seg.heredoc:
                interno = seg.heredoc
            if interno:
                sub = segmentos(interno, dir_actual)
                if sub is None:
                    raise ValueError("subcomando no analizable")
                resultado.extend(sub)
        actual = []

    try:
        for t in toks:
            if t in SEPARADORES:
                cerrar()
            else:
                actual.append(t)
        cerrar()
    except ValueError:
        return None
    return resultado


def git_subcomando(seg):
    """(subcomando, args, directorio) si el segmento es git; si no, None. Resuelve alias."""
    if seg.prog != "git":
        return None
    args, directorio = list(seg.args), seg.cwd
    while args and args[0].startswith("-"):
        op = args.pop(0)
        if op == "-C" and args:
            directorio = os.path.normpath(os.path.join(directorio, os.path.expanduser(args.pop(0))))
        elif op in ("-c", "--git-dir", "--work-tree", "--namespace", "--exec-path") and args and "=" not in op:
            args.pop(0)
    if not args:
        return None
    sub, resto = args[0], args[1:]
    try:
        alias = subprocess.run(["git", "config", "--get", f"alias.{sub}"], cwd=directorio if os.path.isdir(directorio) else None,
                               capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        alias = ""
    if alias and not alias.startswith("!"):
        partes = alias.split()
        sub, resto = partes[0], partes[1:] + resto
    return sub, resto, directorio


def _abs(cwd, ruta):
    return os.path.normpath(os.path.join(cwd, os.path.expanduser(ruta)))


def escrituras(seg):
    """Rutas (absolutas) que el segmento crea, modifica, mueve o borra."""
    out, t, a = [], seg.tokens, seg.args
    # redirecciones > y >> (no >&N ni /dev/null)
    for i, tok in enumerate(t):
        if tok in (">", ">>", ">|", "&>", "&>>") and i + 1 < len(t):
            dest = t[i + 1]
            if dest not in ("&", "/dev/null") and not dest.startswith("&") and not dest.isdigit():
                out.append(_abs(seg.cwd, dest))
    no_op = [x for x in a if not x.startswith("-")]
    if seg.prog == "tee":
        out += [_abs(seg.cwd, x) for x in no_op]
    elif seg.prog in ("sed", "perl") and any(x.startswith("-i") or x == "--in-place" or (x.startswith("-") and "i" in x[1:] and seg.prog == "perl") for x in a):
        archivos, i, con_script = [], 0, any(x in ("-e", "-f", "--expression") for x in a)
        while i < len(a):
            x = a[i]
            if x in ("-e", "-f", "--expression", "--file"):
                i += 2
                continue
            if not x.startswith("-"):
                if not con_script and seg.prog == "sed":
                    con_script = True  # primer posicional = script de sed
                else:
                    archivos.append(x)
            i += 1
        out += [_abs(seg.cwd, x) for x in archivos]
    elif seg.prog in ("cp", "mv", "install", "ln", "rsync") and len(no_op) >= 2:
        dest = _abs(seg.cwd, no_op[-1])
        for src in no_op[:-1]:
            out.append(os.path.join(dest, os.path.basename(src)) if os.path.isdir(dest) else dest)
            if seg.prog == "mv":
                out.append(_abs(seg.cwd, src))
    elif seg.prog in ("rm", "touch", "truncate", "unlink", "shred"):
        out += [_abs(seg.cwd, x) for x in no_op]
    elif seg.prog == "dd":
        out += [_abs(seg.cwd, x[3:]) for x in a if x.startswith("of=")]
    elif seg.prog in INTERPRETES:
        codigo = ""
        for flag in ("-c", "-e", "--eval", "-p"):
            if flag in a and a.index(flag) + 1 < len(a):
                codigo += "\n" + a[a.index(flag) + 1]
        codigo += "\n" + seg.heredoc
        if RE_ESCRITURA_INLINE.search(codigo):
            for ruta in RE_RUTA_INLINE.findall(codigo):
                if "/" in ruta or "." in os.path.basename(ruta):
                    out.append(_abs(seg.cwd, ruta))
    return out


def lecturas(seg):
    """Rutas (absolutas) que aparecen como argumentos del segmento (posibles lecturas)."""
    return [_abs(seg.cwd, x) for x in seg.args if not x.startswith("-") and ("/" in x or "." in x)]
