"""Playlists salvas (playlists.json na pasta do mestre)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from freddy.api.protocolo import Musica

rotas = APIRouter(prefix="/playlists")


class PlaylistSalva(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    nome: str = Field(min_length=1, max_length=200)
    musicas: list[Musica] = Field(max_length=1000)
    atualizadaEm: float


@rotas.get("")
def listar_playlists(request: Request):
    return request.app.state.playlists.listar()


@rotas.put("/{id_}")
def salvar_playlist(id_: str, playlist: PlaylistSalva, request: Request):
    if playlist.id != id_:
        raise HTTPException(400, "o id da rota e o da playlist não batem")
    return request.app.state.playlists.salvar(playlist.model_dump(exclude_none=True))


@rotas.delete("/{id_}", status_code=204)
def excluir_playlist(id_: str, request: Request):
    if not request.app.state.playlists.excluir(id_):
        raise HTTPException(404, "playlist não encontrada")
