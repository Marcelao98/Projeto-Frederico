"""O acervo que o painel enxerga: o dataset do repositório + o que o mestre mudou.

Três camadas, nesta ordem:
- o dataset (modules/bardo/dataset/musicas.json): a curadoria, versionada no git;
- `ajustes.json` (pasta do mestre): correções nas faixas do dataset (nome,
  temas, comentário), feitas pelo chat, pelo modo Acervo ou pela planilha;
- `aprendidas.json` (pasta do mestre): faixas novas que a mesa ensinou.

Quem baixou o app não tem o repositório, por isso o que o mestre muda fica
na pasta dele. Pra levar pro dataset oficial: scripts/freddy_promover.py.
As categorias sempre saem dos temas (vocabulario.json), nunca à mão.
"""

from __future__ import annotations

import json
from pathlib import Path

from freddy.dados.playlists import gravar_json
from modules.bardo import service

_DATASET = Path(service.__file__).parent / "dataset"

CAMPOS_EDITAVEIS = ("nome", "temas", "comentario_pessoal")
MAX_TEMAS = 12


class FaixaNaoEncontrada(KeyError):
    pass


def limpar_temas(temas: list[str]) -> list[str]:
    """Tira espaço, vazio e repetido (sem diferenciar maiúscula); mantém a ordem."""
    vistos: set[str] = set()
    limpos: list[str] = []
    for t in temas:
        t = " ".join(str(t).split()).lower()
        if t and t not in vistos:
            vistos.add(t)
            limpos.append(t)
    return limpos[:MAX_TEMAS]


def com_categorias(faixa: dict) -> dict:
    temas = faixa.get("temas") or [service.NAO_CLASSIFICADO]
    return {**faixa, "temas": temas, "categorias": service.categorias_dos_temas(temas)}


class Acervo:
    def __init__(self, arquivo_aprendidas: Path, pasta_dataset: Path = _DATASET, arquivo_ajustes: Path | None = None):
        self.arquivo_aprendidas = arquivo_aprendidas
        self.arquivo_ajustes = arquivo_ajustes or arquivo_aprendidas.with_name("ajustes.json")
        self.pasta_dataset = pasta_dataset

    # --- leitura -----------------------------------------------------------

    def base(self) -> list[dict]:
        return json.loads((self.pasta_dataset / "musicas.json").read_text(encoding="utf-8"))["musicas"]

    def aprendidas(self) -> list[dict]:
        if not self.arquivo_aprendidas.exists():
            return []
        return json.loads(self.arquivo_aprendidas.read_text(encoding="utf-8"))["musicas"]

    def ajustes(self) -> dict[str, dict]:
        if not self.arquivo_ajustes.exists():
            return {}
        return json.loads(self.arquivo_ajustes.read_text(encoding="utf-8"))["faixas"]

    def vocabulario(self) -> dict:
        return json.loads((self.pasta_dataset / "vocabulario.json").read_text(encoding="utf-8"))

    def faixas(self) -> list[dict]:
        ajustes = self.ajustes()
        faixas = [com_categorias({**f, **ajustes[f["id"]]}) if f["id"] in ajustes else f for f in self.base()]
        return faixas + self.aprendidas()

    def faixa(self, id_: str) -> dict:
        for f in self.faixas():
            if f["id"] == id_:
                return f
        raise FaixaNaoEncontrada(id_)

    # --- escrita -----------------------------------------------------------

    def editar(self, id_: str, campos: dict) -> dict:
        """Muda nome/temas/comentário de uma faixa. Devolve a faixa como ficou."""
        return self.editar_varias({id_: campos})[0]

    def editar_varias(self, mudancas: dict[str, dict]) -> list[dict]:
        """Várias edições numa gravação só (a planilha manda centenas)."""
        base = {f["id"]: f for f in self.base()}
        aprendidas = self.aprendidas()
        por_id_aprendida = {f["id"]: f for f in aprendidas}
        ajustes = self.ajustes()
        mexeu_ajustes = mexeu_aprendidas = False
        resultado: list[dict] = []

        for id_, campos in mudancas.items():
            campos = {k: v for k, v in campos.items() if k in CAMPOS_EDITAVEIS and v is not None}
            if "temas" in campos:
                campos["temas"] = limpar_temas(campos["temas"]) or [service.NAO_CLASSIFICADO]
            if "nome" in campos:
                campos["nome"] = str(campos["nome"]).strip() or None
                if campos["nome"] is None:
                    del campos["nome"]

            if id_ in por_id_aprendida:
                faixa = com_categorias({**por_id_aprendida[id_], **campos})
                por_id_aprendida[id_].update(faixa)
                mexeu_aprendidas = True
                resultado.append(faixa)
            elif id_ in base:
                original = base[id_]
                ajuste = {**ajustes.get(id_, {}), **campos}
                # Só guarda o que difere do dataset: voltar ao original apaga o ajuste.
                ajuste = {k: v for k, v in ajuste.items() if original.get(k) != v}
                if ajuste:
                    ajustes[id_] = ajuste
                else:
                    ajustes.pop(id_, None)
                mexeu_ajustes = True
                resultado.append(com_categorias({**original, **ajuste}) if ajuste else original)
            else:
                raise FaixaNaoEncontrada(id_)

        if mexeu_ajustes:
            gravar_json(self.arquivo_ajustes, {"faixas": ajustes})
        if mexeu_aprendidas:
            gravar_json(self.arquivo_aprendidas, {"musicas": aprendidas})
        return resultado

    def aprender(self, titulo: str, link: str, temas: list[str]) -> dict:
        """Grava a faixa nas aprendidas. MusicaJaNoDataset se o vídeo já está no acervo."""
        return self.aprender_varias([(titulo, link, temas)])[0]

    def aprender_varias(self, novas: list[tuple[str, str, list[str]]]) -> list[dict]:
        faixas = self.faixas()
        videos = {service.video_id(f["link"]): f for f in faixas}
        ids = {f["id"] for f in faixas}
        aprendidas = self.aprendidas()
        entradas: list[dict] = []
        for titulo, link, temas in novas:
            video = service.video_id(link)
            if video in videos:
                raise service.MusicaJaNoDataset(videos[video])
            base = f"{service.slug(service.ORIGEM_DESCOBERTA['nome'])}-{service.slug(titulo) or video.lower()}"
            id_, n = base, 2
            while id_ in ids:
                id_, n = f"{base}-{n}", n + 1
            temas = limpar_temas(temas)[: service.MAX_TEMAS_DESCOBERTA] or [service.NAO_CLASSIFICADO]
            entrada = com_categorias(
                {
                    "id": id_,
                    "nome": titulo,
                    "link": f"https://www.youtube.com/watch?v={video}",
                    "escopo": "faixa_individual",
                    "origem": dict(service.ORIGEM_DESCOBERTA),
                    "temas": temas,
                    "comentario_pessoal": "",
                }
            )
            ids.add(id_)
            videos[video] = entrada
            entradas.append(entrada)
        gravar_json(self.arquivo_aprendidas, {"musicas": [*aprendidas, *entradas]})
        return entradas
