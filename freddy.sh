#!/usr/bin/env bash
# Liga o Freddy na ordem certa: o backend primeiro, e o app só quando ele
# estiver respondendo. Ctrl+C desliga tudo. Rodar de qualquer lugar:
#   ~/Projeto-Frederico/freddy.sh             toca na caixa de som
#   ~/Projeto-Frederico/freddy.sh --sem-som   finge que toca (testar o painel)
set -euo pipefail

raiz="$(cd "$(dirname "$0")" && pwd)"
cd "$raiz/backend"

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
  freddy >/dev/null 2>&1 &
else
  echo "🐦 App não encontrado: abra o painel no navegador (cd frontend && npm run dev)."
fi

wait "$backend"
