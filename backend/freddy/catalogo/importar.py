"""Leva os blocos conferidos (acervo/catalogo/blocos/) pro catálogo (os CSV de música).

Pra cada música da lista de um bloco:
- sem link oficial do YouTube (ou ainda não conferida) → vai pro pendentes.csv;
- o MusicBrainz achou outro ano → fica o do MusicBrainz (menos na clássica,
  em que o ano da lista é o da composição);
- o resto entra no catálogo com lote "bloco-NN", as tags da lista
  (quem_marcou=claude) e a fonte oficial conferida hoje.

Roda de novo sem problema: apaga o que veio de blocos antes e escreve tudo de
novo (as faixas do rpg-legado não são tocadas).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from freddy.catalogo.bloco import chave_musica
from freddy.catalogo.compilar import PASTA_CATALOGO
from freddy.nucleo.texto import slug

PASTA_BLOCOS = PASTA_CATALOGO / "blocos"


@dataclass
class Relatorio:
    por_bloco: dict[str, dict[str, int]] = field(default_factory=dict)
    pendentes: list[list[str]] = field(default_factory=list)
    anos_corrigidos: list[str] = field(default_factory=list)
    sem_musicbrainz: int = 0

    def conta(self, bloco: str, chave: str) -> None:
        b = self.por_bloco.setdefault(bloco, {})
        b[chave] = b.get(chave, 0) + 1


def _ler(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _escrever(caminho: Path, cabecalho: list[str], linhas: list[dict]) -> None:
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cabecalho, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def listas_de_blocos(pasta: Path = PASTA_BLOCOS) -> list[Path]:
    return sorted(p for p in pasta.glob("bloco-[0-9][0-9].csv"))


def importar(pasta_cat: Path = PASTA_CATALOGO, pasta_blocos: Path | None = None) -> Relatorio:
    pasta_blocos = pasta_blocos or pasta_cat / "blocos"
    rel = Relatorio()
    tabelas = {n: _ler(pasta_cat / f"{n}.csv") for n in
               ("musicas", "artistas", "musica_artista", "musica_genero", "musica_tag", "fontes")}
    cabecalhos = {n: list(t[0].keys()) for n, t in tabelas.items()}
    # Tira o que veio de blocos numa importação anterior.
    de_bloco = {m["id"] for m in tabelas["musicas"] if m["lote"].startswith("bloco-")}
    for n in ("musica_artista", "musica_genero", "musica_tag", "fontes"):
        tabelas[n] = [l for l in tabelas[n] if l["musica"] not in de_bloco]
    tabelas["musicas"] = [m for m in tabelas["musicas"] if m["id"] not in de_bloco]
    ids = {m["id"] for m in tabelas["musicas"]}
    artistas = {a["id"]: a for a in tabelas["artistas"]}
    hoje = date.today().isoformat()

    for lista in listas_de_blocos(pasta_blocos):
        bloco = lista.stem
        base = lista.with_suffix("")
        mb = {chave_musica(l["artista"], l["titulo"]): l for l in _ler(Path(f"{base}.musicbrainz.csv"))}
        yt = {chave_musica(l["artista"], l["titulo"]): l for l in _ler(Path(f"{base}.youtube.csv"))}
        for l in _ler(lista):
            k = chave_musica(l["artista"], l["titulo"])
            rel.conta(bloco, "na lista")
            v = yt.get(k)
            if v is None:
                rel.pendentes.append([l["artista"], l["titulo"], bloco, "ainda não conferida no YouTube"])
                rel.conta(bloco, "pendente")
                continue
            if v["oficial"] != "1":
                rel.pendentes.append([l["artista"], l["titulo"], bloco, v["motivo"]])
                rel.conta(bloco, "pendente")
                continue
            ano = l["ano"]
            g = mb.get(k)
            if g is None or not g.get("ano_mb"):
                rel.sem_musicbrainz += 1
            elif g["confere"] == "NÃO" and "ano =" not in l["nota"]:
                rel.anos_corrigidos.append(f"{l['artista']} - {l['titulo']}: {ano} → {g['ano_mb']}")
                ano = g["ano_mb"]
            mid = base_id = slug(f"{l['artista']} {l['titulo']}")[:80]
            n = 2
            while mid in ids:
                mid, n = f"{base_id}-{n}", n + 1
            ids.add(mid)
            duracao = (g or {}).get("duracao") or v.get("duracao") or ""
            tabelas["musicas"].append({
                "id": mid, "titulo": l["titulo"], "ano": ano, "duracao": duracao, "idioma": l["idioma"],
                "obra": "", "energia": l["energia"], "animacao": l["animacao"], "tem_voz": l["tem_voz"],
                "canta_junto": l["canta_junto"], "ao_vivo": l["ao_vivo"], "explicita": l["explicita"],
                "popularidade": l["popularidade"], "essencial": l["essencial"],
                "mbid": (g or {}).get("mbid", ""), "isrc": "", "lote": bloco, "revisar": "0", "nome_original": ""})
            nomes = [l["artista"]] + [f.strip() for f in l["feat"].split(",") if f.strip()]
            vistos = set()
            for i, nome in enumerate(nomes):
                aid = slug(nome)
                if not aid or aid in vistos:
                    continue
                vistos.add(aid)
                artistas.setdefault(aid, {"id": aid, "nome": nome, "tipo": "", "pais": "", "regiao": "",
                                          "ano_inicio": "", "mbid": ""})
                tabelas["musica_artista"].append({"musica": mid, "artista": aid,
                                                  "papel": "principal" if i == 0 else "feat"})
            tabelas["musica_genero"].append({"musica": mid, "genero": l["genero"], "peso": "1.0"})
            if l["genero2"] and l["genero2"] != l["genero"]:
                tabelas["musica_genero"].append({"musica": mid, "genero": l["genero2"], "peso": "0.6"})
            marcas: dict[str, str] = {}
            for i, c in enumerate(x for x in l["climas"].split("|") if x):
                marcas.setdefault(c, "1.0" if i == 0 else "0.8")
            for col in ("ocasioes", "temas", "instrumentos"):
                for x in (x for x in l[col].split("|") if x):
                    marcas.setdefault(x, "0.9")
            for t, peso in marcas.items():
                tabelas["musica_tag"].append({"musica": mid, "tag": t, "peso": peso, "quem_marcou": "claude"})
            tabelas["fontes"].append({"musica": mid, "tipo": "youtube", "endereco": v["endereco"],
                                      "oficial": "1", "viva": "1", "conferida_em": hoje})
            rel.conta(bloco, "entrou")

    tabelas["artistas"] = sorted(artistas.values(), key=lambda a: a["id"])
    for n, linhas in tabelas.items():
        _escrever(pasta_cat / f"{n}.csv", cabecalhos[n], linhas)
    _escrever(pasta_blocos / "pendentes.csv", ["artista", "titulo", "bloco", "motivo"],
              [dict(zip(["artista", "titulo", "bloco", "motivo"], p)) for p in rel.pendentes])
    return rel
