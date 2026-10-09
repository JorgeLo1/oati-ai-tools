#!/usr/bin/env bash
# Pruebas de los hooks de git del equipo (pre-commit y commit-msg).
# Uso: bash git-hooks/tests/test_git_hooks.sh
# Crea repos temporales (una carpeta "udistrital" falsa vía UDISTRITAL_DIR y un repo ajeno) y los borra al final.
set -u
H="$(cd "$(dirname "$0")/.." && pwd)"
BASE="$(mktemp -d)"
export UDISTRITAL_DIR="$BASE/udistrital"
R="$UDISTRITAL_DIR/repo_prueba"
O="$BASE/ajeno"
SALIDA="$BASE/salida.txt"
OK=0; FALLOS=0

t() {
  local desc="$1" esperado="$2"; shift 2
  if "$@" >"$SALIDA" 2>&1; then r=pasa; else r=bloquea; fi
  if [ "$r" = "$esperado" ]; then OK=$((OK+1)); echo "✅ $desc → $r"
  else FALLOS=$((FALLOS+1)); echo "❌ $desc → $r (esperado: $esperado)"; head -5 "$SALIDA" | sed 's/^/   /'; fi
}
commit() { git commit -q "$@"; }

for d in "$R" "$O"; do
  mkdir -p "$d"; git -C "$d" init -q -b develop
  git -C "$d" config core.hooksPath "$H"; git -C "$d" config user.email t@t; git -C "$d" config user.name t
done

cd "$R"
echo base > base.txt; git add base.txt; OAS_HOOKS_OMITIR=1 git commit -q -m "base"   # commit inicial de develop
echo a > a.ts; git add a.ts
t "commit directo en develop" bloquea commit -m "feat: inicial"
git checkout -qb fix/algo;               t "rama fix/ (prefijo inválido)" bloquea commit -m "feat: x"
git checkout -qb feature/Mayus_X;        t "rama con mayúsculas" bloquea commit -m "feat: x"
git checkout -qb feature/claude-cambios; t "rama que menciona claude" bloquea commit -m "feat: x"
git checkout -qb feature/firma-electronica
t "rama y mensaje válidos" pasa commit -m "feat: Se agrega la firma electrónica udistrital/sisifo_documentacion#900"
echo b >> a.ts; git add a.ts
t "etiqueta chore" bloquea commit -m "chore: x"
t "sin etiqueta" bloquea commit -m "Se arregla el bug"
t "Co-Authored-By" bloquea commit -m "fix: x" -m "Co-Authored-By: Claude <noreply@anthropic.com>"
t "menciona IA" bloquea commit -m "fix: ajuste hecho con IA"
t "palabra 'diagrama' no es IA" pasa commit -m "fix: ajuste del diagrama"
printf 'X=1\n' > .env; git add -f .env
t ".env en el commit" bloquea commit -m "fix: x"; git rm -q --cached .env; rm .env
printf 'A=\n' > .env.example; git add .env.example
t ".env.example permitido" pasa commit -m "docs: ejemplo de variables"
printf 'const uri = "mongodb://admin:clave123@host:27017/db";\n' > b.ts; git add b.ts
t "cadena mongodb con credenciales" bloquea commit -m "fix: x"; git rm -q --cached b.ts; rm b.ts
printf -- '-----BEGIN RSA PRIVATE KEY-----\n' > k.txt; git add k.txt
t "llave privada" bloquea commit -m "fix: x"; git rm -q --cached k.txt; rm k.txt
printf 'const password = "superSecreta123";\n' > c.spec.ts; git add c.spec.ts
t "password literal en .spec (excluido)" pasa commit -m "test: caso de login"
printf 'const password = "superSecreta123";\n' > s.ts; git add s.ts
t "password literal en código" bloquea commit -m "fix: x"; git rm -q --cached s.ts; rm s.ts
printf 'const p = process.env.PASS;\n' > d.ts; git add d.ts
t "variable de entorno (sin secreto)" pasa commit -m "fix: lee la clave del entorno"
echo e > e.ts; git add e.ts
t "escape humano OAS_HOOKS_OMITIR" pasa env OAS_HOOKS_OMITIR=1 git commit -q -m "wip"
printf '#!/bin/sh\necho HOOK-PROPIO >&2; exit 1\n' > .git/hooks/pre-commit; chmod +x .git/hooks/pre-commit
echo f > f.ts; git add f.ts
t "encadena el hook propio del repo" bloquea commit -m "fix: x"
grep -q HOOK-PROPIO "$SALIDA" || { FALLOS=$((FALLOS+1)); echo "❌ el hook propio no se ejecutó"; }
rm .git/hooks/pre-commit; git rm -q --cached f.ts; rm f.ts
git checkout -q develop; git merge -q --no-ff feature/firma-electronica -m "Merge branch 'feature/firma-electronica' into develop" >"$SALIDA" 2>&1
[ $? -eq 0 ] && { OK=$((OK+1)); echo "✅ merge en develop (permitido)"; } || { FALLOS=$((FALLOS+1)); echo "❌ merge en develop bloqueado"; cat "$SALIDA"; }

cd "$O"; echo a > a; git add a
t "repo fuera de udistrital: no aplica reglas" pasa commit -m "lo que sea"

cd /; rm -rf "$BASE"
echo; echo "$OK/$((OK+FALLOS)) OK"; [ "$FALLOS" -eq 0 ]
