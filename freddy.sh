#!/usr/bin/env bash
# Liga o Freddy a partir do código (o jeito de desenvolver): o backend
# primeiro, e o app só quando ele estiver respondendo. Fechar o app desliga
# o Freddy (Ctrl+C também, se rodou num terminal). Rodar de qualquer lugar:
#   ~/Projeto-Frederico/freddy.sh             toca na caixa de som
#   ~/Projeto-Frederico/freddy.sh --sem-som   finge que toca (testar o painel)
# Sem terminal (atalho com Terminal=false), as mensagens vão pro
# ~/.local/share/Freddy/freddy.log. O app instalado liga o backend sozinho:
# este script é pra rodar o backend do código, não o empacotado.
set -euo pipefail

raiz="$(cd "$(dirname "$0")" && pwd)"
cd "$raiz/backend"

if [ ! -t 1 ]; then
  pasta="${FREDDY_PASTA:-$HOME/.local/share/Freddy}"
  mkdir -p "$pasta"
  exec >"$pasta/freddy.log" 2>&1
fi

if [ ! -d .venv ]; then
  echo "🐦 Primeira vez: preparando o Python do Freddy..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# Só reinstala as dependências quando o requirements.txt muda.
marca=".venv/.requirements-instalados"
if ! cmp -s requirements.txt "$marca" 2>/dev/null; then
  echo "🐦 Instalando o que o Freddy precisa..."
  pip install -q -r requirements.txt
  cp requirements.txt "$marca"
fi

python -m freddy "$@" &
backend=$!
trap 'kill "$backend" 2>/dev/null || true' EXIT INT TERM

# Espera o Freddy responder (até 30 s) antes de abrir o app.
for _ in $(seq 1 60); do
  if curl -sf http://127.0.0.1:47824/saude >/dev/null 2>&1; then
    break
  fi
  if ! kill -0 "$backend" 2>/dev/null; then
    echo "O Freddy não ligou. Olhe as mensagens acima." >&2
    exit 1
  fi
  sleep 0.5
done

if command -v freddy >/dev/null 2>&1; then
  # O app em primeiro plano: fechou o app, desliga o Freddy (o trap acima).
  freddy >/dev/null 2>&1 || true
else
  echo "🐦 App não encontrado: abra o painel no navegador (cd frontend && npm run dev)."
  wait "$backend"
fi
