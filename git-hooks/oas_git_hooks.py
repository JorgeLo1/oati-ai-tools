#!/usr/bin/env python3
"""Hooks de git del equipo (lineamientos OAS). Funcionan con cualquier IA y con las personas,
porque los ejecuta git, no la herramienta.

Se instalan con instalar.sh en ~/.config/oas-ai-tools/git-hooks y `git config --global core.hooksPath`.
Sólo actúan en repos udistrital (dentro de <UDISTRITAL> o con remoto github.com/udistrital); en el resto
de repos sólo encadenan el hook local del repo, si existe.

  pre-commit   rama GitFlow válida (feature/<nombre>, hotfix/<nombre>, release/X.Y.Z), sin commits directos en
               develop/master/main (salvo resolución de merge), sin archivos de secretos ni secretos en las líneas agregadas
  commit-msg   primera línea `<etiqueta>: <descripción>` con etiqueta OAS (feat, fix, docs, test, refactor, devops,
               management) y sin atribución a IA (Co-Authored-By, Claude, Anthropic, "Generated with", 🤖, IA, AI, LLM)

Al terminar, ejecuta el hook propio del repo (.git/hooks/<hook>) si existe, para no romper flujos existentes.
Escape para personas (no para IA, git-guard lo bloquea): OAS_HOOKS_OMITIR=1 git commit ...
"""
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import oas_config
    RAIZ = oas_config.udistrital_dir()
except Exception:  # instalado sin oas_config
    RAIZ = os.path.realpath(os.path.expanduser(os.environ.get("UDISTRITAL_DIR", "~/go/src/github.com/udistrital")))

ETIQUETAS = ("feat", "fix", "docs", "test", "refactor", "devops", "management")
RE_PRIMERA = re.compile(r"^(" + "|".join(ETIQUETAS) + r"): \S.*$")
RE_ATRIBUCION = re.compile(r"claude|anthropic|co-authored-by|generated with|noreply@anthropic|🤖|\bIA\b|\bAI\b|\bLLM\b", re.I)
RE_RAMA = re.compile(r"^(feature|hotfix)/[a-z0-9][a-z0-9._-]*$|^release/[0-9]+\.[0-9]+\.[0-9]+$")
RE_RAMA_IA = re.compile(r"claude|anthropic|(^|[/_.-])(ai|ia|bot|llm|gpt|copilot)([/_.-]|$)", re.I)
BASES = ("develop", "master", "main")
OMITIR_MSG = re.compile(r"^(Merge |Revert \"|fixup! |squash! |amend! )")
ARCHIVOS_SECRETOS = re.compile(r"(^|/)(\.env(\.[^/]*)?|id_rsa[^/]*|id_ed25519[^/]*|credentials[^/]*\.json|[^/]*\.(pem|key|p12|pfx|keystore|jks))$", re.I)
PERMITIDOS = re.compile(r"\.(example|sample|template|dist)$|\.pub$", re.I)
PATRONES_SECRETO = [
    ("llave privada", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("token JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("cadena de conexión con credenciales", re.compile(r"\b(mongodb(\+srv)?|postgres(ql)?|mysql)://[^\s:/@${}]+:[^\s@${}]+@")),
    ("token de GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b")),
    ("credencial en texto plano", re.compile(
        r"(password|passwd|pass|secret|token|api[_-]?key|client[_-]?secret)\s*[:=]\s*[\"'][^\"'$\{\s]{8,}[\"']", re.I)),
]
EXCLUIR_PATRON_GENERICO = re.compile(r"(\.spec\.|\.test\.|/tests?/|__tests__|\.md$|\.lock$|lock\.yaml$)", re.I)


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def es_repo_udistrital():
    top = os.path.realpath(git("rev-parse", "--show-toplevel") or os.getcwd())
    if top == RAIZ or top.startswith(RAIZ + os.sep):
        return True
    remotos = git("remote", "-v")
    return bool(re.search(r"github\.com[:/]udistrital/", remotos))


def fallar(titulo, detalles):
    print(f"\n✖ [oas-git-hooks] {titulo}", file=sys.stderr)
    for d in detalles:
        print(f"   - {d}", file=sys.stderr)
    print("   Lineamientos: https://github.com/udistrital/lineamientos_oas/tree/master/repositorios_institucionales\n",
          file=sys.stderr)
    sys.exit(1)


def pre_commit():
    errores = []
    rama = git("symbolic-ref", "--short", "-q", "HEAD")
    en_merge = os.path.exists(git("rev-parse", "--git-path", "MERGE_HEAD") or "MERGE_HEAD")
    if rama:
        if rama in BASES:
            if not en_merge:
                errores.append(f"No se commitea directamente en `{rama}`: crea una rama feature/<nombre> desde develop "
                               "(o hotfix/<nombre> desde master).")
        elif not RE_RAMA.match(rama):
            errores.append(f"Rama `{rama}` inválida: debe ser feature/<nombre>, hotfix/<nombre> (minúsculas, sin tildes, "
                           "palabras con guiones) o release/X.Y.Z. Prefijos como fix/, bugfix/, feat/, chore/ no se permiten.")
        if RE_RAMA_IA.search(rama):
            errores.append(f"El nombre de la rama `{rama}` no puede referirse a Claude/IA/bots.")

    staged = [f for f in git("diff", "--cached", "--name-only", "--diff-filter=ACMR").splitlines() if f]
    for f in staged:
        if ARCHIVOS_SECRETOS.search(f) and not PERMITIDOS.search(f):
            errores.append(f"`{f}` parece un archivo de secretos/configuración local: no se versiona (agrégalo a .gitignore).")

    diff = git("diff", "--cached", "-U0", "--no-color", "--diff-filter=ACMR")
    archivo = ""
    for linea in diff.splitlines():
        if linea.startswith("+++ "):
            archivo = linea[6:] if linea.startswith("+++ b/") else linea[4:]
            continue
        if not linea.startswith("+") or linea.startswith("+++"):
            continue
        for nombre, patron in PATRONES_SECRETO:
            if nombre == "credencial en texto plano" and EXCLUIR_PATRON_GENERICO.search(archivo):
                continue
            if patron.search(linea):
                errores.append(f"{nombre} en `{archivo}`: {linea[1:].strip()[:80]}…")
                break
    if errores:
        fallar("Commit bloqueado por los lineamientos del equipo:", errores)


def commit_msg(ruta):
    texto = open(ruta, encoding="utf-8", errors="ignore").read()
    lineas = [l for l in texto.splitlines() if not l.startswith("#")]
    while lineas and not lineas[0].strip():
        lineas.pop(0)
    if not lineas:
        return
    primera = lineas[0].strip()
    if OMITIR_MSG.match(primera):
        return
    errores = []
    if not RE_PRIMERA.match(primera):
        errores.append(f"Primera línea `{primera[:70]}` inválida. Formato: `<etiqueta>: <descripción en español>` con "
                       f"etiqueta {', '.join(ETIQUETAS)} (no chore, style, perf, build, ci, feature, hotfix, wip…).")
    m = RE_ATRIBUCION.search("\n".join(lineas))
    if m:
        errores.append(f"El mensaje contiene una referencia a Claude/IA (`{m.group(0)}`): quítala "
                       "(Co-Authored-By, \"Generated with\", 🤖, IA/AI/LLM).")
    if errores:
        fallar("Mensaje de commit inválido:", errores)


def encadenar(hook, args):
    """Ejecuta el hook propio del repo (.git/hooks/<hook>) si existe."""
    comun = git("rev-parse", "--git-common-dir")  # .git/hooks del repo (no core.hooksPath, que apunta aquí)
    propio = os.path.join(os.path.abspath(comun), "hooks", hook) if comun else ""
    if propio and os.path.isfile(propio) and os.access(propio, os.X_OK) \
            and os.path.realpath(propio) != os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), hook)):
        r = subprocess.run([propio, *args])
        sys.exit(r.returncode)


def main():
    hook = sys.argv[1] if len(sys.argv) > 1 else ""
    args = sys.argv[2:]
    if es_repo_udistrital() and os.environ.get("OAS_HOOKS_OMITIR") != "1":
        if hook == "pre-commit":
            pre_commit()
        elif hook == "commit-msg" and args:
            commit_msg(args[0])
    encadenar(hook, args)


if __name__ == "__main__":
    main()
