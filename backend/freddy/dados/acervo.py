"""O acervo que o painel enxerga: o dataset do repositório + as faixas aprendidas.

O dataset (modules/bardo/dataset/musicas.json) é a curadoria, versionada no
git. O que a mesa ensina pelo "era essa?" vai pra `aprendidas.json`, na
pasta do mestre: quem baixou o app não tem o repositório. Pra levar as
aprendidas pro dataset oficial: scripts/freddy_promover_aprendidas.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from freddy.dados.playlists import gravar_json
from modules.bardo import service

_DATASET = Path(service.__file__).parent / "dataset"


class Acervo:
    def __init__(self, arquivo_aprendidas: Path, pasta_dataset: Path = _DATASET):
        self.arquivo_aprendidas = arquivo_aprendidas
        self.pasta_dataset = pasta_dataset

    def base(self) -> list[dict]:
        return json.loads((self.pasta_dataset / "musicas.json").read_text(encoding="utf-8"))["musicas"]

    def aprendidas(self) -> list[dict]:
        if not self.arquivo_aprendidas.exists():
            return []
        return json.loads(self.arquivo_aprendidas.read_text(encoding="utf-8"))["musicas"]

    def vocabulario(self) -> dict:
        return json.loads((self.pasta_dataset / "vocabulario.json").read_text(encoding="utf-8"))

    def faixas(self) -> list[dict]:
        return self.base() + self.aprendidas()

    def aprender(self, titulo: str, link: str, temas: list[str]) -> dict:
        """Grava a faixa nas aprendidas. MusicaJaNoDataset se o vídeo já está no acervo."""
        faixas = self.faixas()
        video = service.video_id(link)
        for f in faixas:
            if service.video_id(f["link"]) == video:
                raise service.MusicaJaNoDataset(f)

        ids = {f["id"] for f in faixas}
        base = f"{service.slug(service.ORIGEM_DESCOBERTA['nome'])}-{service.slug(titulo) or video.lower()}"
        id_, n = base, 2
        while id_ in ids:
            id_, n = f"{base}-{n}", n + 1

        temas = [t.strip() for t in temas if t.strip()][: service.MAX_TEMAS_DESCOBERTA] or [service.NAO_CLASSIFICADO]
        entrada = {
            "id": id_,
            "nome": titulo,
            "link": f"https://www.youtube.com/watch?v={video}",
            "escopo": "faixa_individual",
            "origem": dict(service.ORIGEM_DESCOBERTA),
            "temas": temas,
            "categorias": service.categorias_dos_temas(temas),
            "comentario_pessoal": "",
        }
        gravar_json(self.arquivo_aprendidas, {"musicas": [*self.aprendidas(), entrada]})
        return entrada
