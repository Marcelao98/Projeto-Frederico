"""Perguntar ao YouTube: título de um link colado e a busca livre."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from freddy.audio.fontes.youtube import motivo_em_portugues
from freddy.nucleo.texto import extrair_link_youtube

rotas = APIRouter(prefix="/youtube")


class PedidoDeBusca(BaseModel):
    texto: str = Field(min_length=1, max_length=300)


@rotas.get("/info")
async def info_do_link(link: str, request: Request):
    if not extrair_link_youtube(link):
        raise HTTPException(400, "isso não é um link do YouTube")
    try:
        return await asyncio.to_thread(request.app.state.youtube.info, link)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, motivo_em_portugues(e)) from e


@rotas.post("/buscar")
async def busca_livre(pedido: PedidoDeBusca, request: Request):
    try:
        return await asyncio.to_thread(request.app.state.youtube.buscar, pedido.texto)
    except LookupError as e:
        raise HTTPException(404, "não achei nada no YouTube") from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, motivo_em_portugues(e)) from e
