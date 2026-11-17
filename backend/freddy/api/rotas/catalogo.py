"""O catálogo novo (o banco do Fredify): o pedido em português vira músicas prontas pra fila."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

rotas = APIRouter(prefix="/catalogo")


class Pedido(BaseModel):
    texto: str = Field(min_length=1, max_length=300)


@rotas.get("")
def situacao(request: Request):
    cat = request.app.state.catalogo
    return {"pronto": cat.pronto, "musicas": cat.quantas, "erro": cat.erro}


@rotas.post("/buscar")
async def buscar(pedido: Pedido, request: Request):
    cat = request.app.state.catalogo
    if not cat.pronto:
        raise HTTPException(503, "o catálogo ainda não está pronto")
    return await asyncio.to_thread(cat.buscar, pedido.texto)
