"""O Freddy em si: está ligado? (/saude), abrir link no navegador, diagnóstico."""

from __future__ import annotations

import webbrowser

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from freddy import PROTOCOLO, VERSAO

rotas = APIRouter()

# O que o painel pode mandar abrir no navegador do sistema (o app não abre
# link sozinho). Lista fechada: a rota não vira "abre qualquer coisa".
SITES_QUE_ABRE = ("https://discord.com/", "https://github.com/Marcelao98/Projeto-Frederico")


class LinkExterno(BaseModel):
    url: str = Field(max_length=2000)


@rotas.get("/saude")
def saude(request: Request):
    estado = request.app.state
    return {
        "ok": True,
        "nome": "freddy",
        "versao": VERSAO,
        "protocolo": PROTOCOLO,
        "som": "simulado" if estado.config.sem_som else "local",
        "paineis": estado.paineis.quantos,
        "ytdlp": _versao_do_ytdlp(),
    }


def _versao_do_ytdlp() -> str | None:
    try:
        import yt_dlp.version

        return yt_dlp.version.__version__
    except Exception:  # noqa: BLE001
        return None


@rotas.post("/abrir")
def abrir_no_navegador(link: LinkExterno):
    if not link.url.startswith(SITES_QUE_ABRE):
        raise HTTPException(400, "só abro links do Discord e do GitHub do Freddy")
    if not webbrowser.open(link.url):
        raise HTTPException(500, "não achei um navegador pra abrir")
    return {"ok": True}


@rotas.get("/diagnostico")
def diagnostico(request: Request):
    return request.app.state.bot.diagnostico()
