"""O Freddy: o som da mesa rodando sozinho, sem a Natty.

`python -m freddy` sobe o servidor local (FastAPI + WebSocket) que o painel
usa pelo MotorRemoto. Ver backend/README.md.
"""

VERSAO = "0.5.2"
PROTOCOLO = 1  # versão do protocolo do WebSocket (sobe quando quebrar o contrato)
