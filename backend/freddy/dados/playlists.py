"""Playlists salvas, num JSON na pasta do mestre (ver config.pasta_padrao).

Mesmo formato do PlaylistSalva do painel (frontend/src/dados/playlists.ts):
{id, nome, musicas, atualizadaEm}. A lista fica da mais recente pra mais velha.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

from freddy.dados.arquivos import gravar_json


class Playlists:
    def __init__(self, arquivo: Path):
        self.arquivo = arquivo

    def listar(self) -> list[dict]:
        if not self.arquivo.exists():
            return []
        return json.loads(self.arquivo.read_text(encoding="utf-8"))["playlists"]

    def salvar(self, playlist: dict) -> dict:
        """Cria ou substitui (pelo id) e põe no topo da lista."""
        lista = [p for p in self.listar() if p["id"] != playlist["id"]]
        gravar_json(self.arquivo, {"playlists": [playlist, *lista]})
        return playlist

    def excluir(self, id_: str) -> bool:
        lista = self.listar()
        restantes = [p for p in lista if p["id"] != id_]
        if len(restantes) == len(lista):
            return False
        gravar_json(self.arquivo, {"playlists": restantes})
        return True


def _limpo(texto: str) -> str:
    """minúsculas, sem acento e sem pontuação: "Sessão 12 — a cripta" → "sessao 12 a cripta"."""
    texto = unicodedata.normalize("NFD", texto.lower())
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^\w ]", " ", texto).split())


def mesmo_nome(a: str, b: str) -> bool:
    return _limpo(a) == _limpo(b)


def achar_playlist(texto: str, lista: list[dict]) -> list[dict]:
    """Porta de acharPlaylist (frontend/src/dados/playlists.ts): nome igual
    ganha; senão as que começam com o texto; senão as que têm todas as palavras."""
    alvo = _limpo(texto)
    if not alvo:
        return []
    iguais = [p for p in lista if _limpo(p["nome"]) == alvo]
    if iguais:
        return iguais
    comecam = [p for p in lista if _limpo(p["nome"]).startswith(alvo)]
    if comecam:
        return comecam
    palavras = alvo.split()
    return [p for p in lista if all(f" {w}" in f" {_limpo(p['nome'])} " for w in palavras)]
