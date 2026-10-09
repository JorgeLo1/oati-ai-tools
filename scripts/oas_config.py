#!/usr/bin/env python3
"""Configuración compartida de oas-ai-tools.

Carpeta raíz de los repos udistrital (<UDISTRITAL>), en orden de prioridad:
  1. variable de entorno UDISTRITAL_DIR
  2. ~/.config/oas-ai-tools/config.json -> {"udistrital_dir": "..."}   (lo escribe instalar.sh)
  3. ~/go/src/github.com/udistrital

Uso por consola:
  python3 oas_config.py udistrital     # imprime <UDISTRITAL>
  python3 oas_config.py specs          # imprime <UDISTRITAL>/.claude/specs
  python3 oas_config.py raiz-plugin    # imprime la carpeta de oas-ai-tools
"""
import json
import os
import re
import sys

CONFIG_DIR = os.path.expanduser("~/.config/oas-ai-tools")
CONFIG = os.path.join(CONFIG_DIR, "config.json")
DEFAULT = "~/go/src/github.com/udistrital"
PLUGIN = "oas"  # nombre del plugin de Claude Code (prefijo de skills y agentes)


def udistrital_dir():
    valor = os.environ.get("UDISTRITAL_DIR")
    if not valor and os.path.exists(CONFIG):
        try:
            valor = json.load(open(CONFIG)).get("udistrital_dir")
        except Exception:
            valor = None
    return os.path.realpath(os.path.expanduser(valor or DEFAULT))


def specs_dir():
    return os.path.join(udistrital_dir(), ".claude", "specs")


def raiz_plugin():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def como_plugin():
    """True si el proceso corre como hook del plugin de Claude Code."""
    return bool(os.environ.get("CLAUDE_PLUGIN_ROOT"))


def skill(nombre):
    """Nombre con el que Claude debe invocar una skill o agente (con prefijo si es plugin)."""
    return f"{PLUGIN}:{nombre}" if como_plugin() else nombre


NOMBRES = ("commit-oas", "planificar-issue", "endpoint-oas", "crud-oas", "mid-oas", "seguridad-oas",
           "documentar-cambios", "doc-issue-oas", "contexto-proyecto")
_RE_SLASH = re.compile(r"(^|[\s(])/(" + "|".join(NOMBRES) + r")\b")
_RE_TICK = re.compile(r"`(" + "|".join(NOMBRES) + r")`")
_RE_SUB = re.compile(r"subagent_type: (" + "|".join(NOMBRES) + r")\b")


def adaptar(texto):
    """En modo plugin, agrega el prefijo `oas:` a las skills/agentes mencionados en un mensaje para Claude."""
    if not como_plugin() or not texto:
        return texto
    texto = _RE_SLASH.sub(lambda m: f"{m.group(1)}/{PLUGIN}:{m.group(2)}", texto)
    texto = _RE_TICK.sub(lambda m: f"`{PLUGIN}:{m.group(1)}`", texto)
    return _RE_SUB.sub(lambda m: f"subagent_type: {PLUGIN}:{m.group(1)}", texto)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "udistrital"
    print({"udistrital": udistrital_dir, "specs": specs_dir, "raiz-plugin": raiz_plugin}.get(cmd, udistrital_dir)())
