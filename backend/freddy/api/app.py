"""O servidor local do Freddy: FastAPI com o motor no /ws e os dados em REST.

Rotas:
    GET    /saude                 o painel descobre se o Freddy está ligado
    WS     /ws                    o Motor (ver protocolo.py)
    GET    /acervo                {musicas, vocabulario}: o dataset + as aprendidas
    POST   /acervo/faixas         {titulo, link, temas}: ensina faixa nova ("era essa?")
    GET    /playlists             playlists salvas
    PUT    /playlists/{id}        cria ou substitui
    DELETE /playlists/{id}
    GET    /youtube/info?link=    título e duração de um link colado
    POST   /youtube/buscar        {texto}: busca livre, o melhor resultado
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from freddy import PROTOCOLO, VERSAO
from freddy.api.paineis import Paineis
from freddy.api.protocolo import Musica, descrever_erro, validar_comando
from freddy.config import Config
from freddy.dados.acervo import Acervo
from freddy.dados.playlists import Playlists
from freddy.motor.motor import ComandoInvalido, Motor
from modules.bardo import service

log = logging.getLogger("freddy.api")

INTERVALO_DO_PROGRESSO = 0.5  # segundos


class YoutubeDados:
    """O que o painel pergunta ao YouTube (os testes trocam por um falso)."""

    def info(self, link: str) -> dict:
        from freddy.audio.youtube import resolver_youtube

        f = resolver_youtube(link)
        return {"titulo": f.titulo, "link": link, "duracaoSegundos": f.duracao or None}

    def buscar(self, texto: str) -> dict:
        from freddy.audio.youtube import FORMATO
        from modules.bardo import youtube

        r = youtube.buscar_stream(texto, FORMATO)
        return {"titulo": r["titulo"], "link": r["link"], "duracaoSegundos": r.get("duracao_segundos")}


class PlaylistSalva(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    nome: str = Field(min_length=1, max_length=200)
    musicas: list[Musica] = Field(max_length=1000)
    atualizadaEm: float


class PedidoDeBusca(BaseModel):
    texto: str = Field(min_length=1, max_length=300)


class FaixaNova(BaseModel):
    titulo: str = Field(min_length=1, max_length=300)
    link: str = Field(min_length=1, max_length=2000)
    temas: list[str] = Field(default_factory=list, max_length=20)


def criar_reprodutor(config: Config, loop: asyncio.AbstractEventLoop):
    if config.sem_som:
        from freddy.audio.reprodutor_falso import ReprodutorFalso

        return ReprodutorFalso(simular=True, agendar=loop.call_soon_threadsafe)
    from freddy.audio.reprodutor_mesa import ReprodutorMesa
    from freddy.audio.saidas import abrir_saida_local

    return ReprodutorMesa(abrir_saida_local, agendar=loop.call_soon_threadsafe)


def criar_app(config: Config | None = None, criar=criar_reprodutor, youtube: YoutubeDados | None = None) -> FastAPI:
    config = config or Config()
    acervo = Acervo(config.arquivo_aprendidas)
    playlists = Playlists(config.arquivo_playlists)
    youtube = youtube or YoutubeDados()

    @asynccontextmanager
    async def vida(app: FastAPI):
        loop = asyncio.get_running_loop()
        reprodutor = criar(config, loop)
        motor = Motor(reprodutor)
        app.state.reprodutor = reprodutor
        app.state.motor = motor
        app.state.paineis = Paineis(motor)
        relogio = asyncio.create_task(_relogio(motor, app.state.paineis))
        try:
            yield
        finally:
            relogio.cancel()
            with suppress(asyncio.CancelledError):
                await relogio
            fechar = getattr(reprodutor, "fechar", None)
            if fechar:
                fechar()

    app = FastAPI(title="Freddy", version=VERSAO, lifespan=vida)
    app.add_middleware(
        CORSMiddleware, allow_origins=list(config.origens), allow_methods=["*"], allow_headers=["*"]
    )

    @app.get("/saude")
    def saude():
        return {
            "ok": True,
            "nome": "freddy",
            "versao": VERSAO,
            "protocolo": PROTOCOLO,
            "som": "simulado" if config.sem_som else "local",
            "paineis": app.state.paineis.quantos,
        }

    # --- acervo e playlists ------------------------------------------------

    @app.get("/acervo")
    def ler_acervo():
        return {"musicas": acervo.faixas(), "vocabulario": acervo.vocabulario()}

    @app.post("/acervo/faixas", status_code=201)
    def aprender(faixa: FaixaNova):
        try:
            return acervo.aprender(faixa.titulo, faixa.link, faixa.temas)
        except service.MusicaJaNoDataset as e:
            raise HTTPException(409, {"erro": "essa música já está no acervo", "faixa": e.musica}) from e

    @app.get("/playlists")
    def listar_playlists():
        return playlists.listar()

    @app.put("/playlists/{id_}")
    def salvar_playlist(id_: str, playlist: PlaylistSalva):
        if playlist.id != id_:
            raise HTTPException(400, "o id da rota e o da playlist não batem")
        return playlists.salvar(playlist.model_dump(exclude_none=True))

    @app.delete("/playlists/{id_}", status_code=204)
    def excluir_playlist(id_: str):
        if not playlists.excluir(id_):
            raise HTTPException(404, "playlist não encontrada")

    # --- YouTube -----------------------------------------------------------

    @app.get("/youtube/info")
    async def info_do_link(link: str):
        from freddy.audio.youtube import motivo_em_portugues

        if not service.extrair_link_youtube(link):
            raise HTTPException(400, "isso não é um link do YouTube")
        try:
            return await asyncio.to_thread(youtube.info, link)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, motivo_em_portugues(e)) from e

    @app.post("/youtube/buscar")
    async def busca_livre(pedido: PedidoDeBusca):
        from freddy.audio.youtube import motivo_em_portugues

        try:
            return await asyncio.to_thread(youtube.buscar, pedido.texto)
        except LookupError as e:
            raise HTTPException(404, "não achei nada no YouTube") from e
        except Exception as e:  # noqa: BLE001
            raise HTTPException(502, motivo_em_portugues(e)) from e

    # --- o motor -----------------------------------------------------------

    @app.websocket("/ws")
    async def ws(socket: WebSocket):
        origem = socket.headers.get("origin")
        # Navegador sempre manda Origin: sem ela é um programa local (script,
        # a Natty no futuro). Com ela, só o painel passa.
        if origem is not None and origem not in config.origens:
            log.warning("Conexão recusada de %s", origem)
            await socket.close(code=4403)
            return
        await socket.accept()
        paineis: Paineis = app.state.paineis
        motor: Motor = app.state.motor
        fila = paineis.entrar(socket)
        envio = asyncio.create_task(_enviar(socket, fila))
        try:
            fila.put_nowait({"tipo": "ola", "protocolo": PROTOCOLO, "versao": VERSAO, "som": "simulado" if config.sem_som else "local"})
            fila.put_nowait({"tipo": "estado", "estado": motor.estado()})
            fila.put_nowait({"tipo": "progresso", **motor.progresso()})
            while True:
                texto = await socket.receive_text()
                resposta = _atender(texto, motor, paineis)
                if resposta is not None:
                    fila.put_nowait(resposta)
        except WebSocketDisconnect:
            pass
        finally:
            paineis.sair(socket)
            envio.cancel()
            with suppress(asyncio.CancelledError):
                await envio

    return app


def _atender(texto: str, motor: Motor, paineis: Paineis) -> dict | None:
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


async def _relogio(motor: Motor, paineis: Paineis) -> None:
    while True:
        await asyncio.sleep(INTERVALO_DO_PROGRESSO)
        if motor.atualizar_progresso():
            paineis.enviar_progresso()
