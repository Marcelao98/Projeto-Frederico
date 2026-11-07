"""O canal de tempo real (/ws): o motor da sala. Protocolo em api/protocolo.py."""

from __future__ import annotations

import asyncio
import json
from contextlib import suppress

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from freddy import PROTOCOLO, VERSAO
from freddy.api.paineis import Paineis
from freddy.api.protocolo import descrever_erro, validar_comando
from freddy.salas.motor import ComandoInvalido, Motor

rotas = APIRouter()

INTERVALO_DO_PROGRESSO = 0.5  # segundos


@rotas.websocket("/ws")
async def ws(socket: WebSocket):
    # Quem pode conectar (só o painel) o Porteiro já conferiu.
    await socket.accept()
    estado = socket.app.state
    paineis: Paineis = estado.paineis
    motor: Motor = estado.motor
    fila = paineis.entrar(socket)
    envio = asyncio.create_task(_enviar(socket, fila))
    try:
        som = "simulado" if estado.config.sem_som else "local"
        fila.put_nowait({"tipo": "ola", "protocolo": PROTOCOLO, "versao": VERSAO, "som": som})
        fila.put_nowait({"tipo": "estado", "estado": motor.estado()})
        fila.put_nowait({"tipo": "progresso", **motor.progresso()})
        fila.put_nowait({"tipo": "discord", "discord": estado.bot.estado()})
        while True:
            texto = await socket.receive_text()
            resposta = atender(texto, motor, paineis)
            if resposta is not None:
                fila.put_nowait(resposta)
    except WebSocketDisconnect:
        pass
    finally:
        paineis.sair(socket)
        envio.cancel()
        with suppress(asyncio.CancelledError):
            await envio


def atender(texto: str, motor: Motor, paineis: Paineis) -> dict | None:
    try:
        mensagem = json.loads(texto)
    except json.JSONDecodeError:
        return {"tipo": "resposta", "id": None, "ok": False, "erro": "mensagem não é JSON"}
    if not isinstance(mensagem, dict):
        return {"tipo": "resposta", "id": None, "ok": False, "erro": "mensagem não é um objeto"}
    if mensagem.get("tipo") == "ping":
        return {"tipo": "pong"}
    if mensagem.get("tipo") != "comando":
        return {"tipo": "resposta", "id": mensagem.get("id"), "ok": False, "erro": f"tipo desconhecido: {mensagem.get('tipo')!r}"}
    id_ = mensagem.get("id")
    try:
        resultado = motor.executar(validar_comando(mensagem.get("comando")))
    except (ValidationError, ComandoInvalido) as e:
        return {"tipo": "resposta", "id": id_, "ok": False, "erro": descrever_erro(e)}
    paineis.descarregar()  # o estado novo sai antes da resposta, pra todo mundo
    return {"tipo": "resposta", "id": id_, "ok": True, "resultado": resultado}


async def _enviar(socket: WebSocket, fila: asyncio.Queue) -> None:
    with suppress(WebSocketDisconnect, RuntimeError):
        while True:
            await socket.send_json(await fila.get())


async def relogio(motor: Motor, paineis: Paineis) -> None:
    """Manda o progresso da música pros painéis, 2x por segundo."""
    while True:
        await asyncio.sleep(INTERVALO_DO_PROGRESSO)
        if motor.atualizar_progresso():
            paineis.enviar_progresso()
