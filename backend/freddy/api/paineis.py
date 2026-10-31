"""Os painéis conectados (o app e quantas abas do navegador houver).

Todos veem a mesma fila. Cada painel tem sua fila de mensagens e uma tarefa
que envia em ordem: o estado sempre chega antes da resposta do comando que o
mudou, então quem fez `await motor.executar(...)` já lê o estado novo.
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import WebSocket

from freddy.motor.motor import Motor

log = logging.getLogger("freddy.api")


class Paineis:
    def __init__(self, motor: Motor):
        self.motor = motor
        self._filas: dict[WebSocket, asyncio.Queue] = {}
        self._estado_enviado: dict | None = None
        self._progresso_enviado: dict | None = None
        self._agendado = False
        motor.inscrever(self._estado_mudou)
        motor.ao_evento(self._evento)

    @property
    def quantos(self) -> int:
        return len(self._filas)

    def entrar(self, ws: WebSocket) -> asyncio.Queue:
        fila: asyncio.Queue = asyncio.Queue()
        self._filas[ws] = fila
        return fila

    def sair(self, ws: WebSocket) -> None:
        self._filas.pop(ws, None)

    def enviar(self, mensagem: dict, so_para: WebSocket | None = None) -> None:
        if so_para is not None:
            fila = self._filas.get(so_para)
            if fila:
                fila.put_nowait(mensagem)
            return
        for fila in self._filas.values():
            fila.put_nowait(mensagem)

    def descarregar(self) -> None:
        """Manda o estado (e o progresso) se mudaram desde o último envio."""
        self._agendado = False
        estado = self.motor.estado()
        if estado is not self._estado_enviado:
            self._estado_enviado = estado
            self.enviar({"tipo": "estado", "estado": estado})
        self.enviar_progresso()

    def enviar_progresso(self) -> None:
        progresso = self.motor.progresso()
        if progresso != self._progresso_enviado:
            self._progresso_enviado = progresso
            self.enviar({"tipo": "progresso", **progresso})

    def _estado_mudou(self) -> None:
        # Um comando pode mudar o estado várias vezes: junta tudo num envio só.
        if not self._agendado:
            self._agendado = True
            asyncio.get_running_loop().call_soon(self.descarregar)

    def _evento(self, evento: dict) -> None:
        self.descarregar()
        self.enviar({"tipo": "evento", "evento": evento})
