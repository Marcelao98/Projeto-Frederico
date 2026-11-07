"""O acervo oficial (acervo/musicas.json, versionado no git): ler, formatar e
acrescentar faixas. É o que os scripts de manutenção (backend/scripts/acervo_*)
e o freddy_promover usam. O que o mestre muda no app fica por cima, na pasta
dele (dados/acervo.py).
"""

from __future__ import annotations

import json
from pathlib import Path

from freddy.config import PASTA_ACERVO
from freddy.nucleo.texto import slug, video_id
from freddy.nucleo.vocabulario import NAO_CLASSIFICADO, categorias_dos_temas

CAMINHO = PASTA_ACERVO / "musicas.json"
MAX_TEMAS_DESCOBERTA = 5
ORIGEM_DESCOBERTA = {"nome": "Descoberta em mesa", "tipo": "outro"}


class MusicaJaNoAcervo(Exception):
    """A faixa já está no acervo (mesmo vídeo); .musica é a entrada que existe."""

    def __init__(self, musica: dict):
        super().__init__(musica["nome"])
        self.musica = musica


def carregar(caminho: Path | None = None) -> list[dict]:
    with open(caminho or CAMINHO, encoding="utf-8") as f:
        return json.load(f)["musicas"]


def adicionar_descoberta(titulo: str, link: str, temas: list[str], caminho: Path | None = None) -> dict:
    """Grava uma faixa descoberta em mesa no musicas.json e devolve a entrada.

    Sem temas, entra como "não classificado". MusicaJaNoAcervo se o vídeo já
    estiver lá.
    """
    arquivo = caminho or CAMINHO
    dataset = json.loads(arquivo.read_text(encoding="utf-8"))
    musicas = dataset["musicas"]

    video = video_id(link)
    for m in musicas:
        if video_id(m["link"]) == video:
            raise MusicaJaNoAcervo(m)

    ids = {m["id"] for m in musicas}
    base = f"{slug(ORIGEM_DESCOBERTA['nome'])}-{slug(titulo) or video.lower()}"
    id_, n = base, 2
    while id_ in ids:
        id_, n = f"{base}-{n}", n + 1

    temas = temas or [NAO_CLASSIFICADO]
    entrada = {
        "id": id_,
        "nome": titulo,
        "link": f"https://www.youtube.com/watch?v={video}",
        "escopo": "faixa_individual",
        "origem": dict(ORIGEM_DESCOBERTA),
        "temas": temas,
        "categorias": categorias_dos_temas(temas),
        "comentario_pessoal": "",
    }
    musicas.append(entrada)
    arquivo.write_text(formatar(dataset), encoding="utf-8")
    return entrada


# Ordem dos campos de cada faixa no arquivo, pra ficar legível no diff.
_ORDEM_DOS_CAMPOS = ["id", "nome", "link", "escopo", "origem", "temas", "categorias", "comentario_pessoal"]


def formatar(dataset: dict) -> str:
    """musicas.json no formato do arquivo à mão: uma faixa por bloco, um campo por linha."""
    faixas = []
    for m in dataset["musicas"]:
        chaves = [k for k in _ORDEM_DOS_CAMPOS if k in m] + [k for k in m if k not in _ORDEM_DOS_CAMPOS]
        campos = ",\n".join(f"      {json.dumps(k)}: {json.dumps(m[k], ensure_ascii=False)}" for k in chaves)
        faixas.append("    {\n" + campos + "\n    }")
    comentario = json.dumps(dataset["_comentario"], ensure_ascii=False)
    return "{\n" f'  "_comentario": {comentario},\n' '  "musicas": [\n' + ",\n".join(faixas) + "\n  ]\n}\n"
