#!/usr/bin/env bash
# Desinstala oas-ai-tools de esta máquina (no toca los repositorios ni las especificaciones).
#   bash desinstalar.sh        # interactivo
#   bash desinstalar.sh -y     # sin preguntas
set -uo pipefail
CONFIG_DIR="$HOME/.config/oas-ai-tools"
SI=0; [ "${1:-}" = "-y" ] && SI=1
confirmar() { [ "$SI" = 1 ] && return 0; read -r -p "$1 [s/N]: " r; [[ "$r" =~ ^[sSyY] ]]; }

UDISTRITAL="$(python3 -c 'import json,os;print(json.load(open(os.path.expanduser("~/.config/oas-ai-tools/config.json"))).get("udistrital_dir",""))' 2>/dev/null || true)"

GLOBAL="$(git config --global --get core.hooksPath || true)"
if [ "$GLOBAL" = "$CONFIG_DIR/git-hooks" ] && confirmar "¿Quitar los hooks de git del equipo (core.hooksPath global)?"; then
  git config --global --unset core.hooksPath && echo "✔ core.hooksPath global eliminado"
fi

CLAUDE_BIN="$(command -v claude || ls -d "$HOME"/.vscode-server/extensions/anthropic.claude-code-*/resources/native-binary/claude 2>/dev/null | sort -V | tail -1 || true)"
if [ -n "$CLAUDE_BIN" ] && "$CLAUDE_BIN" plugin list 2>/dev/null | grep -q "oas@oas-udistrital"; then
  if confirmar "¿Desinstalar el plugin de Claude Code (oas@oas-udistrital) y su marketplace?"; then
    "$CLAUDE_BIN" plugin uninstall oas@oas-udistrital && "$CLAUDE_BIN" plugin marketplace remove oas-udistrital
  fi
fi

if [ -n "$UDISTRITAL" ]; then
  for f in AGENTS.md CLAUDE.md; do
    [ -f "$UDISTRITAL/$f" ] && confirmar "¿Borrar $UDISTRITAL/$f (reglas del equipo)?" && rm "$UDISTRITAL/$f" && echo "✔ Borrado $UDISTRITAL/$f"
  done
  echo "  Las especificaciones en $UDISTRITAL/.claude/specs y el contexto .claude/ de cada repo se conservan."
fi

if [ -d "$CONFIG_DIR" ] && confirmar "¿Borrar $CONFIG_DIR (configuración, hooks copiados, informes de porte y respaldos)?"; then
  rm -rf "$CONFIG_DIR" && echo "✔ Borrado $CONFIG_DIR"
fi
echo "Si portaste las herramientas a otra IA, revierte su configuración con los respaldos *.bak-oas-* listados en su INFORME-PORTE.md."
