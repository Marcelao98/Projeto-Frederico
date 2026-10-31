"""Playlists salvas, num JSON na pasta do mestre (ver config.pasta_padrao).

Mesmo formato do PlaylistSalva do painel (frontend/src/dados/playlists.ts):
{id, nome, musicas, atualizadaEm}. A lista fica da mais recente pra mais velha.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def gravar_json(arquivo: Path, dados) -> None:
    """Grava inteiro ou nada: escreve num temporário e troca (falta de luz não corrompe)."""
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(dir=arquivo.parent, prefix=f".{arquivo.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(temporario, arquivo)
    except BaseException:
        Path(temporario).unlink(missing_ok=True)
        raise


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
