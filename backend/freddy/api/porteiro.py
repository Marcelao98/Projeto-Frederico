"""O porteiro: só o painel (e programas deste computador) falam com o Freddy.

Vale pra todas as rotas, HTTP e WebSocket, antes de qualquer coisa:

- **Endereço (Host):** só `127.0.0.1:<porta>` e `localhost:<porta>`. Um site
  que troca o próprio DNS pra apontar pro 127.0.0.1 ("DNS rebinding") chega
  com o nome dele no Host e é recusado.
- **Origem (Origin):** o navegador diz de que site veio o pedido. Se veio de
  um site que não é o painel, recusa. Sem isso, qualquer página aberta
  conseguia mandar um POST "simples" (sem preflight de CORS) e, por exemplo,
  reescrever o acervo pela planilha ou tirar o bot da call.
- **Sem Origin** passa: navegador sempre manda Origin nesses pedidos, então
  quem não manda é um programa local (curl, script, os testes).
"""

from __future__ import annotations

import json
import logging

log = logging.getLogger("freddy.porteiro")


class Porteiro:
    def __init__(self, app, origens: tuple[str, ...], hosts: tuple[str, ...]):
        self.app = app
        self.origens = set(origens)
        self.hosts = {h.lower() for h in hosts}

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        cabecalhos = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        host = cabecalhos.get("host", "").lower()
        origem = cabecalhos.get("origin")
        motivo = None
        if host not in self.hosts:
            motivo = f"endereço não permitido ({host or 'sem Host'})"
        elif origem is not None and origem not in self.origens:
            motivo = f"origem não permitida ({origem})"
        if motivo is None:
            return await self.app(scope, receive, send)

        log.warning("Recusado: %s %s — %s", scope["type"], scope.get("path"), motivo)
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 4403})
            return
        corpo = json.dumps({"detail": f"recusado: {motivo}"}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(corpo)).encode())],
            }
        )
        await send({"type": "http.response.body", "body": corpo})
