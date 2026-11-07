"""O servidor local do Freddy: monta as peças e liga as rotas.

As rotas moram em api/rotas/ (um arquivo por assunto) e o canal de tempo
real em api/ws.py. Tudo que elas usam fica em `app.state`:

    config, acervo, playlists, youtube, segredos   (montados aqui)
    reprodutor, motor, paineis, bot               (montados ao ligar, em `vida`)

O Porteiro (api/porteiro.py) confere todo pedido antes de qualquer rota.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from freddy import VERSAO
from freddy.api import ws
from freddy.api.rotas import acervo as rotas_acervo
from freddy.api.rotas import discord as rotas_discord
from freddy.api.rotas import playlists as rotas_playlists
from freddy.api.rotas import sistema as rotas_sistema
from freddy.api.rotas import youtube as rotas_youtube
from freddy.api.paineis import Paineis
from freddy.api.porteiro import Porteiro
from freddy.audio.fontes.youtube import YoutubeDados
from freddy.config import Config
from freddy.dados.acervo import Acervo
from freddy.dados.playlists import Playlists
from freddy.dados.segredos import Segredos
from freddy.salas.motor import Motor

log = logging.getLogger("freddy.api")


def criar_reprodutor(config: Config, loop: asyncio.AbstractEventLoop):
    if config.sem_som:
        from freddy.audio.reprodutor_falso import ReprodutorFalso

        return ReprodutorFalso(simular=True, agendar=loop.call_soon_threadsafe)
    from freddy.audio.reprodutor_mesa import ReprodutorMesa
    from freddy.audio.saidas.caixa import abrir_saida_local

    return ReprodutorMesa(abrir_saida_local, agendar=loop.call_soon_threadsafe)


def criar_bot(motor, reprodutor, acervo, playlists, youtube, segredos):
    from freddy.conversa.cerebro import Conversa
    from freddy.integracoes.discord.bot import BotDoFreddy

    return BotDoFreddy(motor, reprodutor, Conversa(motor, acervo, playlists, youtube), segredos)


def criar_app(
    config: Config | None = None,
    criar=criar_reprodutor,
    youtube: YoutubeDados | None = None,
    bot=criar_bot,
) -> FastAPI:
    config = config or Config()

    @asynccontextmanager
    async def vida(app: FastAPI):
        estado = app.state
        loop = asyncio.get_running_loop()
        estado.reprodutor = criar(config, loop)
        estado.motor = Motor(estado.reprodutor)
        estado.paineis = Paineis(estado.motor)
        estado.bot = bot(estado.motor, estado.reprodutor, estado.acervo, estado.playlists, estado.youtube, estado.segredos)
        estado.bot.ao_mudar = lambda: estado.paineis.enviar({"tipo": "discord", "discord": estado.bot.estado()})
        ligar_bot = asyncio.create_task(estado.bot.ligar())
        relogio = asyncio.create_task(ws.relogio(estado.motor, estado.paineis))
        try:
            yield
        finally:
            ligar_bot.cancel()
            with suppress(Exception, asyncio.CancelledError):
                await estado.bot.desconectar()
            relogio.cancel()
            with suppress(asyncio.CancelledError):
                await relogio
            fechar = getattr(estado.reprodutor, "fechar", None)
            if fechar:
                fechar()

    app = FastAPI(title="Freddy", version=VERSAO, lifespan=vida)
    app.state.config = config
    app.state.acervo = Acervo(config.arquivo_aprendidas)
    app.state.playlists = Playlists(config.arquivo_playlists)
    app.state.youtube = youtube or YoutubeDados()
    app.state.segredos = Segredos(config.arquivo_discord)

    app.add_middleware(CORSMiddleware, allow_origins=list(config.origens), allow_methods=["*"], allow_headers=["*"])
    # Por último = o primeiro a ver o pedido: recusa site estranho antes de tudo.
    app.add_middleware(Porteiro, origens=config.origens, hosts=config.hosts)

    for modulo in (rotas_sistema, rotas_acervo, rotas_playlists, rotas_youtube, rotas_discord, ws):
        app.include_router(modulo.rotas)
    return app
