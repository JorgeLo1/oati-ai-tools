#!/usr/bin/env bash
# Instalador de oas-ai-tools (herramientas de IA del equipo para repos udistrital).
#
# Uso:
#   bash instalar.sh                      # instalación interactiva
#   bash instalar.sh --udistrital <ruta>  # carpeta de los repos udistrital (por defecto ~/go/src/github.com/udistrital)
#   bash instalar.sh -y                   # sin preguntas (acepta los valores por defecto)
#   bash instalar.sh --solo-verificar     # sólo revisa requisitos e instalación y corre las pruebas
#   bash instalar.sh --sin-git-hooks      # no instala los hooks de git globales
#   bash instalar.sh --sin-pruebas        # no corre las pruebas al final
#   bash instalar.sh --migrar-desde-manual  # quita una instalación manual previa en ~/.claude (skills/scripts/hooks)
#
# Qué hace (no toca ningún repositorio institucional ni hace commits):
#   1. Verifica requisitos (python3 >= 3.8, git, gh autenticado, identidad de git).
#   2. Guarda la carpeta udistrital en ~/.config/oas-ai-tools/config.json.
#   3. Copia las reglas del equipo a <udistrital>/AGENTS.md y <udistrital>/CLAUDE.md (con respaldo) y crea .claude/specs.
#   4. Instala los hooks de git del equipo en ~/.config/oas-ai-tools/git-hooks y los activa con core.hooksPath global.
#   5. Detecta las herramientas de IA instaladas y explica el siguiente paso para cada una.
#   6. Corre las pruebas (hooks de git y casos de los guardianes).
set -uo pipefail

RAIZ_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$HOME/.config/oas-ai-tools"
HOOKS_DIR="$CONFIG_DIR/git-hooks"
FECHA="$(date +%Y%m%d-%H%M%S)"
UDISTRITAL=""; SI=0; SOLO_VERIFICAR=0; SIN_HOOKS=0; SIN_PRUEBAS=0; MIGRAR=0
AVISOS=(); ERRORES=()

while [ $# -gt 0 ]; do
  case "$1" in
    --udistrital) UDISTRITAL="${2:-}"; shift ;;
    -y|--si) SI=1 ;;
    --solo-verificar) SOLO_VERIFICAR=1 ;;
    --sin-git-hooks) SIN_HOOKS=1 ;;
    --sin-pruebas) SIN_PRUEBAS=1 ;;
    --migrar-desde-manual) MIGRAR=1 ;;
    -h|--ayuda|--help) sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Opción desconocida: $1 (usa --ayuda)"; exit 2 ;;
  esac
  shift
done

c_ok() { printf '  \033[32m✔\033[0m %s\n' "$*"; }
c_av() { printf '  \033[33m!\033[0m %s\n' "$*"; AVISOS+=("$*"); }
c_er() { printf '  \033[31m✖\033[0m %s\n' "$*"; ERRORES+=("$*"); }
titulo() { printf '\n\033[1m%s\033[0m\n' "$*"; }
preguntar() { # preguntar "texto" "por_defecto" -> respuesta en $RESP
  if [ "$SI" = 1 ]; then RESP="$2"; return; fi
  read -r -p "  $1 [$2]: " RESP; RESP="${RESP:-$2}"
}
confirmar() { # confirmar "texto" -> 0 si sí
  if [ "$SI" = 1 ]; then return 0; fi
  read -r -p "  $1 [S/n]: " r; [[ -z "$r" || "$r" =~ ^[sSyY] ]]
}
respaldar() { [ -e "$1" ] && cp -a "$1" "$1.bak-oas-$FECHA" && c_av "Respaldo: $1.bak-oas-$FECHA"; }

# ------------------------------------------------------------------ 1. requisitos
titulo "1. Requisitos"
if command -v python3 >/dev/null && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
  c_ok "python3 $(python3 -c 'import platform; print(platform.python_version())')"
else
  c_er "Se necesita python3 >= 3.8 (los hooks y guardianes están en Python sin dependencias externas)."
fi
command -v git >/dev/null && c_ok "git $(git --version | awk '{print $3}')" || c_er "Falta git."
if command -v gh >/dev/null; then
  if gh auth status >/dev/null 2>&1; then c_ok "gh autenticado ($(gh api user --jq .login 2>/dev/null || echo '?'))"
  else c_av "gh instalado pero sin autenticar: ejecuta 'gh auth login' (las skills leen issues y descargan mockups)."; fi
else
  c_av "Falta gh (GitHub CLI): /planificar-issue y /doc-issue-oas lo usan para leer issues. https://cli.github.com"
fi
GIT_EMAIL="$(git config --global user.email || true)"; GIT_NAME="$(git config --global user.name || true)"
if [ -n "$GIT_EMAIL" ] && [ -n "$GIT_NAME" ]; then c_ok "identidad de git: $GIT_NAME <$GIT_EMAIL>"
else c_av "Configura git user.name y user.email: se usan para distinguir tus commits de los traídos (contexto) y como autor."; fi
command -v node >/dev/null && c_ok "node $(node --version)" || c_av "node no encontrado (necesario para trabajar en los MF/APIs Nest, no para estas herramientas)."
[ ${#ERRORES[@]} -gt 0 ] && { echo; echo "Corrige los errores y vuelve a ejecutar."; exit 1; }

# ------------------------------------------------------------------ 2. carpeta udistrital
titulo "2. Carpeta de los repos udistrital"
if [ -z "$UDISTRITAL" ]; then
  ACTUAL="$(python3 "$RAIZ_REPO/scripts/oas_config.py" udistrital 2>/dev/null)"
  preguntar "Ruta de la carpeta que contiene los repos udistrital" "${ACTUAL:-$HOME/go/src/github.com/udistrital}"
  UDISTRITAL="$RESP"
fi
UDISTRITAL="$(python3 -c 'import os,sys; print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$UDISTRITAL")"
if [ ! -d "$UDISTRITAL" ]; then
  if [ "$SOLO_VERIFICAR" = 1 ]; then c_er "No existe $UDISTRITAL"
  elif confirmar "No existe $UDISTRITAL. ¿Crearla?"; then mkdir -p "$UDISTRITAL" && c_ok "Creada $UDISTRITAL"
  else c_er "Sin carpeta udistrital no se puede continuar."; exit 1; fi
fi
if [ "$SOLO_VERIFICAR" = 0 ]; then
  mkdir -p "$CONFIG_DIR"
  python3 - "$CONFIG_DIR/config.json" "$UDISTRITAL" "$RAIZ_REPO" <<'PY'
import json, os, sys
ruta, u, repo = sys.argv[1:4]
datos = json.load(open(ruta)) if os.path.exists(ruta) else {}
datos.update({"udistrital_dir": u, "repo_herramientas": repo})
json.dump(datos, open(ruta, "w"), indent=2, ensure_ascii=False)
PY
  c_ok "Configuración: $CONFIG_DIR/config.json (udistrital_dir = $UDISTRITAL)"
fi
N_REPOS=$(find "$UDISTRITAL" -maxdepth 4 -name .git -type d 2>/dev/null | wc -l)
c_ok "$N_REPOS repos git encontrados bajo la carpeta"

# ------------------------------------------------------------------ 3. reglas del equipo
titulo "3. Reglas del equipo en $UDISTRITAL"
AGENTS_TMP="$(mktemp)"; grep -v '^> \*\*Si eres una IA distinta de Claude Code' "$RAIZ_REPO/AGENTS.md" | sed '/^$/N;/^\n$/D' > "$AGENTS_TMP"
instalar_archivo() { # origen destino
  if [ -f "$2" ] && cmp -s "$1" "$2"; then c_ok "$(basename "$2") al día"; return; fi
  if [ "$SOLO_VERIFICAR" = 1 ]; then c_av "$(basename "$2") ausente o distinto de la versión del repo"; return; fi
  respaldar "$2"; cp "$1" "$2" && c_ok "Instalado $2"
}
instalar_archivo "$AGENTS_TMP" "$UDISTRITAL/AGENTS.md"
instalar_archivo "$RAIZ_REPO/plantillas/udistrital/CLAUDE.md" "$UDISTRITAL/CLAUDE.md"
rm -f "$AGENTS_TMP"
[ "$SOLO_VERIFICAR" = 0 ] && mkdir -p "$UDISTRITAL/.claude/specs" && c_ok "Carpeta de especificaciones: $UDISTRITAL/.claude/specs"
if git -C "$UDISTRITAL" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  c_av "$UDISTRITAL está dentro de un repo git: AGENTS.md, CLAUDE.md y .claude/ podrían commitearse ahí. Revísalo."
fi

# ------------------------------------------------------------------ 4. hooks de git
titulo "4. Hooks de git del equipo (cualquier IA y personas)"
if [ "$SIN_HOOKS" = 1 ]; then
  c_av "Omitidos por --sin-git-hooks: ramas, etiquetas, atribución y secretos NO se validarán al commitear."
else
  GLOBAL="$(git config --global --get core.hooksPath || true)"
  if [ -n "$GLOBAL" ] && [ "$(python3 -c 'import os,sys;print(os.path.realpath(os.path.expanduser(sys.argv[1])))' "$GLOBAL")" != "$HOOKS_DIR" ]; then
    c_er "Ya tienes core.hooksPath global = $GLOBAL. No lo reemplazo: integra $RAIZ_REPO/git-hooks a mano o quítalo y reintenta."
  elif [ "$SOLO_VERIFICAR" = 1 ]; then
    [ "$GLOBAL" ] && c_ok "core.hooksPath global → $HOOKS_DIR" || c_av "Hooks de git no instalados"
    for f in pre-commit commit-msg oas_git_hooks.py oas_config.py; do
      [ -f "$HOOKS_DIR/$f" ] || c_av "Falta $HOOKS_DIR/$f"
    done
  else
    mkdir -p "$HOOKS_DIR"
    cp "$RAIZ_REPO/git-hooks/pre-commit" "$RAIZ_REPO/git-hooks/commit-msg" "$RAIZ_REPO/git-hooks/oas_git_hooks.py" "$RAIZ_REPO/scripts/oas_config.py" "$HOOKS_DIR/"
    chmod +x "$HOOKS_DIR/pre-commit" "$HOOKS_DIR/commit-msg" "$HOOKS_DIR/oas_git_hooks.py"
    git config --global core.hooksPath "$HOOKS_DIR" && c_ok "core.hooksPath global → $HOOKS_DIR"
  fi
  # repos con su propio hooksPath local (husky, etc.): el local tiene prioridad y nuestros hooks no corren ahí
  while IFS= read -r g; do
    r="$(dirname "$g")"; local_hp="$(git -C "$r" config --local --get core.hooksPath || true)"
    [ -n "$local_hp" ] && c_av "$(basename "$r") define core.hooksPath local ($local_hp): ahí no corren los hooks del equipo."
  done < <(find "$UDISTRITAL" -maxdepth 4 -name .git -type d 2>/dev/null)
fi

# ------------------------------------------------------------------ 5. herramientas de IA
titulo "5. Herramientas de IA detectadas"
CLAUDE_BIN="$(command -v claude || ls -d "$HOME"/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude "$HOME"/.vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | sort -V | tail -1 || true)"
HAY_OTRA=0
if [ -n "$CLAUDE_BIN" ]; then
  c_ok "Claude Code ($("$CLAUDE_BIN" --version 2>/dev/null | head -1))"
  if "$CLAUDE_BIN" plugin list 2>/dev/null | grep -q "oas@oas-udistrital"; then c_ok "Plugin oas instalado"
  else
    REMOTO="$(git -C "$RAIZ_REPO" remote get-url origin 2>/dev/null | sed -E 's#(git@github.com:|https://github.com/)##; s#\.git$##')"
    echo "     Instálalo (en la terminal o dentro de Claude Code con /plugin):"
    echo "       claude plugin marketplace add ${REMOTO:-$RAIZ_REPO}"
    echo "       claude plugin install oas@oas-udistrital"
  fi
fi
for herramienta in cursor codex gemini windsurf; do
  if command -v "$herramienta" >/dev/null || [ -d "$HOME/.$herramienta" ]; then c_ok "$herramienta"; HAY_OTRA=1; fi
done
if ls -d "$HOME"/.vscode-server/extensions/github.copilot* "$HOME"/.vscode/extensions/github.copilot* >/dev/null 2>&1; then c_ok "GitHub Copilot (VS Code)"; HAY_OTRA=1; fi
if [ "$HAY_OTRA" = 1 ]; then
  echo "     Para otras IAs: abre la herramienta en $RAIZ_REPO y pídele:"
  echo "       \"Lee PORTAR.md y síguelo para instalar estas herramientas en ti\""
fi
[ -z "$CLAUDE_BIN" ] && [ "$HAY_OTRA" = 0 ] && c_av "No detecté herramientas de IA. Las reglas y los hooks de git ya quedan activos."

# ------------------------------------------------------------------ instalación manual previa
MANUAL=()
for s in commit-oas planificar-issue endpoint-oas crud-oas mid-oas seguridad-oas documentar-cambios doc-issue-oas; do
  [ -d "$HOME/.claude/skills/$s" ] && MANUAL+=("$HOME/.claude/skills/$s")
done
[ -f "$HOME/.claude/agents/contexto-proyecto.md" ] && MANUAL+=("$HOME/.claude/agents/contexto-proyecto.md")
for f in contexto-proyecto.py reglas-udistrital.py skill-guard.py git-guard.py shell_cmd.py tests; do
  # los sustitutos (oas-shim) que deja una migración previa no cuentan como instalación manual
  [ -e "$HOME/.claude/scripts/$f" ] && ! grep -qs "oas-shim" "$HOME/.claude/scripts/$f" && MANUAL+=("$HOME/.claude/scripts/$f")
done
if [ ${#MANUAL[@]} -gt 0 ]; then
  titulo "Instalación manual previa en ~/.claude"
  if [ "$MIGRAR" = 1 ] && [ "$SOLO_VERIFICAR" = 0 ]; then
    DEST="$CONFIG_DIR/respaldo-manual-$FECHA"; mkdir -p "$DEST"
    for m in "${MANUAL[@]}"; do mv "$m" "$DEST/" && c_ok "Movido a respaldo: $m"; done
    # Las sesiones de Claude Code abiertas cargaron sus hooks al iniciar y siguen llamando a estos scripts:
    # si no existen, el hook falla y puede bloquear la sesión. Se dejan sustitutos que no hacen nada.
    for f in contexto-proyecto.py reglas-udistrital.py skill-guard.py git-guard.py; do
      if [ -e "$DEST/$f" ] && [ ! -e "$HOME/.claude/scripts/$f" ]; then
        printf '#!/usr/bin/env python3\n# oas-shim: sustituto temporal tras migrar al plugin oas. Las sesiones abiertas antes de la\n# migración aún llaman a este hook; las nuevas ya no. Se puede borrar después de reiniciar Claude Code.\nimport sys\nsys.stdin.read()\n' > "$HOME/.claude/scripts/$f"
      fi
    done
    c_av "Quedan sustitutos vacíos (oas-shim) en ~/.claude/scripts para las sesiones abiertas: cierra y abre Claude Code; luego puedes borrarlos."
    if [ -f "$HOME/.claude/settings.json" ]; then
      respaldar "$HOME/.claude/settings.json"
      python3 - "$HOME/.claude/settings.json" <<'PY'
import json, re, sys
p = sys.argv[1]; s = json.load(open(p))
patron = re.compile(r"\.claude/scripts/(contexto-proyecto|reglas-udistrital|skill-guard|git-guard)\.py")
for ev, grupos in list((s.get("hooks") or {}).items()):
    nuevos = []
    for g in grupos:
        g["hooks"] = [h for h in g.get("hooks", []) if not patron.search(h.get("command", ""))]
        if g["hooks"]:
            nuevos.append(g)
    if nuevos: s["hooks"][ev] = nuevos
    else: del s["hooks"][ev]
json.dump(s, open(p, "w"), indent=2, ensure_ascii=False)
PY
      c_ok "Quitados de ~/.claude/settings.json los hooks de la instalación manual (el plugin los reemplaza)"
    fi
  else
    c_av "Hay ${#MANUAL[@]} piezas de una instalación manual en ~/.claude (skills/agente/scripts). Con el plugin quedarían duplicadas y los hooks correrían dos veces."
    echo "     Para retirarlas (con respaldo): bash instalar.sh --migrar-desde-manual"
  fi
fi

# ------------------------------------------------------------------ 6. pruebas
if [ "$SIN_PRUEBAS" = 0 ]; then
  titulo "6. Pruebas"
  if bash "$RAIZ_REPO/git-hooks/tests/test_git_hooks.sh" > /tmp/oas-test-hooks.log 2>&1; then c_ok "Hooks de git: $(tail -1 /tmp/oas-test-hooks.log)"
  else c_er "Hooks de git: fallaron pruebas (ver /tmp/oas-test-hooks.log)"; fi
  if python3 "$RAIZ_REPO/scripts/tests/run_casos.py" > /tmp/oas-test-casos.log 2>&1; then c_ok "Guardianes (spec/casos.json): $(tail -1 /tmp/oas-test-casos.log)"
  else c_er "Guardianes: fallaron casos (ver /tmp/oas-test-casos.log)"; fi
  if python3 "$RAIZ_REPO/scripts/tests/test_verificar_contexto.py" > /tmp/oas-test-verif.log 2>&1; then c_ok "Verificador de contexto: $(tail -1 /tmp/oas-test-verif.log)"
  else c_er "Verificador de contexto: fallaron pruebas (ver /tmp/oas-test-verif.log)"; fi
fi

# ------------------------------------------------------------------ resumen
titulo "Resumen"
[ ${#ERRORES[@]} -eq 0 ] && c_ok "Sin errores." || { for e in "${ERRORES[@]}"; do echo "  ✖ $e"; done; }
[ ${#AVISOS[@]} -gt 0 ] && echo "  Avisos: ${#AVISOS[@]} (revisa los '!' de arriba)."
echo "  Guía de uso: $RAIZ_REPO/README.md"
[ ${#ERRORES[@]} -eq 0 ]
