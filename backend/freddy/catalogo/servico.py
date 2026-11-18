"""O catálogo dentro do app: compila sozinho ao ligar e responde pedidos com músicas prontas pra fila.

Os CSV vêm com o app (acervo/catalogo/); o catalogo.db fica na pasta do
mestre e é refeito quando os CSV ou a versão mudam. Se algo der errado, o
Freddy continua funcionando com o acervo antigo: `pronto` fica False.

A música e o link são coisas separadas no catálogo (musica × fonte). Aqui é
onde o link é escolhido: a melhor fonte viva da música (oficial primeiro).
A fila recebe {titulo, link, faixaId}: o `faixaId` é o id da música no
catálogo, pra um dia trocar o link sem perder a música.
"""

from __future__ import annotations

import logging
import random
import sqlite3
import threading
from pathlib import Path

from freddy import VERSAO
from freddy.catalogo.compilar import compilar
from freddy.catalogo.consulta import Catalogo

log = logging.getLogger("freddy.catalogo")

MAX_POR_PEDIDO = 15  # igual ao acervo antigo (nucleo/busca.MAX_RESULTADOS_DA_BUSCA)
FOLGA_DE_PONTOS = 0.35  # quem fica até isso abaixo da melhor entra no sorteio
TAMANHO_DO_SORTEIO = 60

# Catálogo já carregado neste processo (mesmos CSV, mesma versão): não recompila.
_JA_CARREGADO: dict[tuple[str, str], tuple] = {}


class CatalogoDoApp:
    def __init__(self, pasta_csv: Path, arquivo_db: Path):
        self.pasta_csv = pasta_csv
        self.arquivo_db = arquivo_db
        self.cat: Catalogo | None = None
        self.erro: str | None = None
        self._nomes: dict[str, str] = {}
        self._fontes: dict[str, str] = {}
        self._obras: dict[str, str] = {}
        self._trava = threading.Lock()

    @property
    def pronto(self) -> bool:
        return self.cat is not None

    @property
    def quantas(self) -> int:
        return len(self._fontes) if self.cat else 0

    def _carimbo(self) -> str:
        partes = [VERSAO]
        for p in sorted(self.pasta_csv.glob("*.csv")):
            s = p.stat()
            partes.append(f"{p.name}:{s.st_size}:{int(s.st_mtime)}")
        return "|".join(partes)

    def preparar(self) -> None:
        """Compila (se precisar) e carrega. Nunca levanta erro: guarda em `erro`."""
        with self._trava:
            try:
                if not self.pasta_csv.is_dir():
                    raise FileNotFoundError(f"não achei {self.pasta_csv}")
                carimbo, marca = self._carimbo(), self.arquivo_db.with_suffix(".carimbo")
                memo = _JA_CARREGADO.get((str(self.pasta_csv), carimbo))
                if memo:
                    self.cat, self._nomes, self._fontes, self._obras = memo
                    self.erro = None
                    return
                velho = marca.read_text("utf-8") if marca.exists() else ""
                if velho != carimbo or not self.arquivo_db.exists():
                    r = compilar(self.pasta_csv, self.arquivo_db)
                    if r.erros:
                        raise ValueError(f"{len(r.erros)} erros nos CSV, o primeiro: {r.erros[0]}")
                    marca.write_text(carimbo, "utf-8")
                self._carregar()
                _JA_CARREGADO[(str(self.pasta_csv), carimbo)] = (self.cat, self._nomes, self._fontes, self._obras)
                self.erro = None
                log.info("catálogo pronto: %d músicas", self.quantas)
            except Exception as e:  # noqa: BLE001 - sem catálogo o Freddy segue com o acervo antigo
                self.cat, self.erro = None, str(e)
                log.warning("catálogo fora do ar (%s); sigo com o acervo antigo", e)

    def _carregar(self) -> None:
        cat = Catalogo(self.arquivo_db)
        con = sqlite3.connect(f"file:{self.arquivo_db}?mode=ro", uri=True)
        try:
            artista = dict(con.execute("SELECT id, nome FROM artista"))
            obra = dict(con.execute("SELECT id, nome FROM obra"))
            principal: dict[str, str] = {}
            for musica, aid in con.execute(
                    "SELECT musica, artista FROM musica_artista ORDER BY papel = 'principal' DESC"):
                principal.setdefault(musica, artista.get(aid, ""))
            fontes: dict[str, str] = {}
            for musica, endereco in con.execute(
                    "SELECT musica, endereco FROM fonte WHERE viva = 1 AND tipo LIKE 'youtube%' "
                    "ORDER BY oficial DESC"):
                fontes.setdefault(musica, endereco)
        finally:
            con.close()
        self._nomes = {mid: principal.get(mid) or obra.get(m.get("obra") or "", "") for mid, m in cat.musicas.items()}
        self._obras = obra
        self._fontes = fontes
        self.cat = cat

    def musica(self, mid: str) -> dict | None:
        """A música no formato da fila ({titulo, link, faixaId, origem}); None se não tem como tocar."""
        if not self.cat or mid not in self.cat.musicas or mid not in self._fontes:
            return None
        m = self.cat.musicas[mid]
        obra = self._obras.get(m.get("obra") or "")
        if obra:  # trilha: "Greenpath (Hollow Knight)"; a origem é a obra
            titulo, de = f"{m['titulo']} ({obra})", obra
        else:  # música de artista: "Artista - Título"
            de = self._nomes.get(mid, "")
            titulo = f"{de} - {m['titulo']}" if de else m["titulo"]
        saida = {"titulo": titulo, "link": self._fontes[mid], "faixaId": mid}
        if de:
            saida["origem"] = de
        if m.get("duracao"):
            saida["duracaoSegundos"] = m["duracao"]
        return saida

    def buscar(self, pedido: str, quantas: int = MAX_POR_PEDIDO) -> dict:
        """{'musicas': [...], 'total': n, 'entendeu': bool}. Vazio = não é com o catálogo.

        'entendeu' False quando sobrou palavra que o catálogo não reconheceu
        ("toca aquela do shrek"): melhor deixar pro acervo antigo e pro YouTube
        do que tocar outra coisa.
        """
        vazio = {"musicas": [], "total": 0, "entendeu": False}
        if not self.cat:
            return vazio
        respostas = [r for r in self.cat.buscar(pedido, TAMANHO_DO_SORTEIO) if r.achados]
        if not respostas or any(r.ignorado for r in respostas):
            return vazio
        por_parte = max(1, quantas // len(respostas))
        musicas, total = [], 0
        for r in respostas:
            tocaveis = [a for a in r.achados if a.musica in self._fontes]
            total += len(tocaveis)
            pelo_nome = any(ramo.livre for ramo in r.parte.ramos)
            if pelo_nome:  # pediu pelo nome: a ordem importa, a mais certa primeiro
                escolhidas = tocaveis[:por_parte]
            else:  # pediu um clima/gênero: sorteia entre as melhores, pra não tocar sempre as mesmas
                topo = tocaveis[0].pontos if tocaveis else 0
                boas = [a for a in tocaveis if a.pontos >= topo - FOLGA_DE_PONTOS]
                escolhidas = random.sample(boas, min(por_parte, len(boas)))
            musicas += [self.musica(a.musica) for a in escolhidas]
        musicas = [m for m in musicas if m]
        return {"musicas": musicas, "total": total, "entendeu": bool(musicas)}
