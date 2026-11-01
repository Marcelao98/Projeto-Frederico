"""O servidor local do Freddy: FastAPI com o motor no /ws e os dados em REST.

Rotas:
    GET    /saude                 o painel descobre se o Freddy está ligado
    WS     /ws                    o Motor (ver protocolo.py)
    GET    /acervo                {musicas, vocabulario}: o dataset + as aprendidas
    POST   /acervo/faixas         {titulo, link, temas}: ensina faixa nova ("era essa?")
    PATCH  /acervo/faixas/{id}    {nome?, temas?, comentario?}: corrige uma faixa
    GET    /discord               o bot: situação, servidores e canais, onde está tocando
    PUT    /discord/token         {token}: guarda o token e conecta
    DELETE /discord/token         desconecta e esquece o token
    POST   /discord/religar       conecta de novo com o token guardado
    POST   /discord/entrar        {canalId}: entra na call
    POST   /discord/sair          sai da call
    PUT    /discord/ouvir-aqui    {ligado}: a caixa de som toca a cópia do que vai pra call
    GET    /acervo/planilha       o acervo em CSV (pra baixar pelo navegador)
    POST   /acervo/planilha/salvar   salva o CSV na pasta Downloads (funciona no app)
    POST   /acervo/planilha?aplicar=  manda o CSV editado: resumo; com aplicar=true, grava
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
from csv import Error as csv_Error
from datetime import date

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError

from freddy import PROTOCOLO, VERSAO
from freddy.api.paineis import Paineis
from freddy.api.protocolo import Musica, descrever_erro, validar_comando
from freddy.config import Config
from freddy.dados import planilha
from freddy.dados.acervo import Acervo, FaixaNaoEncontrada
from freddy.dados.playlists import Playlists
from freddy.dados.segredos import Segredos
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


class EdicaoDeFaixa(BaseModel):
    nome: str | None = Field(default=None, max_length=300)
    temas: list[str] | None = Field(default=None, max_length=30)
    comentario: str | None = Field(default=None, max_length=2000)


class TokenDoBot(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class CanalDeVoz(BaseModel):
    canalId: str = Field(pattern=r"^\d{5,25}$")


class Ligado(BaseModel):
    ligado: bool


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


def criar_bot(motor, reprodutor, acervo, playlists, youtube, segredos):
    from freddy.bot.bot import BotDoFreddy
    from freddy.bot.conversa import Conversa

    return BotDoFreddy(motor, reprodutor, Conversa(motor, acervo, playlists, youtube), segredos)


def criar_app(
    config: Config | None = None,
    criar=criar_reprodutor,
    youtube: YoutubeDados | None = None,
    bot=criar_bot,
) -> FastAPI:
    config = config or Config()
    acervo = Acervo(config.arquivo_aprendidas)
    playlists = Playlists(config.arquivo_playlists)
    youtube = youtube or YoutubeDados()
    segredos = Segredos(config.arquivo_discord)

    @asynccontextmanager
    async def vida(app: FastAPI):
        loop = asyncio.get_running_loop()
        reprodutor = criar(config, loop)
        motor = Motor(reprodutor)
        app.state.reprodutor = reprodutor
        app.state.motor = motor
        paineis = app.state.paineis = Paineis(motor)
        app.state.bot = bot(motor, reprodutor, acervo, playlists, youtube, segredos)
        app.state.bot.ao_mudar = lambda: paineis.enviar({"tipo": "discord", "discord": app.state.bot.estado()})
        ligar_bot = asyncio.create_task(app.state.bot.ligar())
        relogio = asyncio.create_task(_relogio(motor, app.state.paineis))
        try:
            yield
        finally:
            ligar_bot.cancel()
            with suppress(Exception, asyncio.CancelledError):
                await app.state.bot.desconectar()
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

    @app.patch("/acervo/faixas/{id_}")
    def editar_faixa(id_: str, edicao: EdicaoDeFaixa):
        campos = {"nome": edicao.nome, "temas": edicao.temas, "comentario_pessoal": edicao.comentario}
        try:
            return acervo.editar(id_, campos)
        except FaixaNaoEncontrada as e:
            raise HTTPException(404, "essa faixa não está no acervo") from e

    @app.get("/acervo/planilha")
    def baixar_planilha():
        return Response(
            planilha.exportar(acervo),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{_nome_da_planilha()}"'},
        )

    @app.post("/acervo/planilha/salvar")
    def salvar_planilha():
        destino = config.pasta_downloads / _nome_da_planilha()
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(planilha.exportar(acervo), encoding="utf-8")
        return {"caminho": str(destino)}

    @app.post("/acervo/planilha")
    async def enviar_planilha(request: Request, aplicar: bool = False):
        corpo = await request.body()
        if len(corpo) > 5_000_000:
            raise HTTPException(413, "planilha grande demais")
        try:
            texto = corpo.decode("utf-8")
        except UnicodeDecodeError:
            texto = corpo.decode("latin-1")  # Excel antigo salva assim
        try:
            resumo = planilha.comparar(acervo, texto)
        except (ValueError, csv_Error) as e:
            raise HTTPException(400, f"não consegui ler a planilha: {e}") from e
        if aplicar:
            planilha.aplicar(acervo, resumo)
        return {**resumo.como_dict(), "aplicado": aplicar}

    # --- Discord -------------------------------------------------------------

    @app.get("/discord")
    def estado_do_discord():
        return app.state.bot.estado()

    @app.put("/discord/token")
    async def guardar_token(pedido: TokenDoBot):
        if segredos.do_ambiente:
            raise HTTPException(409, "o token vem da variável FREDDY_DISCORD_TOKEN; troque lá")
        segredos.guardar(pedido.token)
        await app.state.bot.conectar(pedido.token)
        return app.state.bot.estado()

    @app.post("/discord/religar")
    async def religar_bot():
        if segredos.token() is None:
            raise HTTPException(409, "não tem token guardado")
        await app.state.bot.ligar()
        return app.state.bot.estado()

    @app.delete("/discord/token")
    async def esquecer_token():
        await app.state.bot.desconectar()
        if not segredos.do_ambiente:
            segredos.esquecer()
        return app.state.bot.estado()

    @app.post("/discord/entrar")
    async def entrar_na_call(pedido: CanalDeVoz):
        from freddy.bot.bot import ErroDoBot

        try:
            await app.state.bot.entrar(int(pedido.canalId))
        except ErroDoBot as e:
            raise HTTPException(409, str(e)) from e
        return app.state.bot.estado()

    @app.post("/discord/sair")
    async def sair_da_call():
        await app.state.bot.sair()
        return app.state.bot.estado()

    @app.put("/discord/ouvir-aqui")
    def ouvir_aqui(pedido: Ligado):
        app.state.bot.definir_ouvir_aqui(pedido.ligado)
        return app.state.bot.estado()

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
        # um teste). Com ela, só o painel passa.
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
            fila.put_nowait({"tipo": "discord", "discord": app.state.bot.estado()})
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


def _nome_da_planilha() -> str:
    return f"freddy-acervo-{date.today().isoformat()}.csv"


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
