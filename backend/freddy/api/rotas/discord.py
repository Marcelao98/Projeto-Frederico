"""O bot do Discord: token, entrar/sair da call, assobio de teste, ouvir aqui."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from freddy.integracoes.discord.bot import ErroDoBot

rotas = APIRouter(prefix="/discord")


class TokenDoBot(BaseModel):
    token: str = Field(min_length=20, max_length=200)


class CanalDeVoz(BaseModel):
    canalId: str = Field(pattern=r"^\d{5,25}$")


class Ligado(BaseModel):
    ligado: bool


@rotas.get("")
def estado_do_discord(request: Request):
    return request.app.state.bot.estado()


@rotas.put("/token")
async def guardar_token(pedido: TokenDoBot, request: Request):
    estado = request.app.state
    if estado.segredos.do_ambiente:
        raise HTTPException(409, "o token vem da variável FREDDY_DISCORD_TOKEN; troque lá")
    estado.segredos.guardar(pedido.token)
    await estado.bot.conectar(pedido.token)
    return estado.bot.estado()


@rotas.post("/religar")
async def religar_bot(request: Request):
    estado = request.app.state
    if estado.segredos.token() is None:
        raise HTTPException(409, "não tem token guardado")
    await estado.bot.ligar()
    return estado.bot.estado()


@rotas.delete("/token")
async def esquecer_token(request: Request):
    estado = request.app.state
    await estado.bot.desconectar()
    if not estado.segredos.do_ambiente:
        estado.segredos.esquecer()
    return estado.bot.estado()


@rotas.post("/entrar")
async def entrar_na_call(pedido: CanalDeVoz, request: Request):
    try:
        await request.app.state.bot.entrar(int(pedido.canalId))
    except ErroDoBot as e:
        raise HTTPException(409, str(e)) from e
    return request.app.state.bot.estado()


@rotas.post("/sair")
async def sair_da_call(request: Request):
    await request.app.state.bot.sair()
    return request.app.state.bot.estado()


@rotas.post("/assobio")
async def assobio(request: Request):
    """O teste da call: o Frederico assobia só pelo Discord (o PC fica mudo)."""
    try:
        await request.app.state.bot.assobiar()
    except ErroDoBot as e:
        raise HTTPException(409, str(e)) from e
    return request.app.state.bot.estado()


@rotas.put("/ouvir-aqui")
def ouvir_aqui(pedido: Ligado, request: Request):
    request.app.state.bot.definir_ouvir_aqui(pedido.ligado)
    return request.app.state.bot.estado()
