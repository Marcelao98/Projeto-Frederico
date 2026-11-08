"""Consulta no catálogo: entende o pedido em português e acha as músicas.

"toca um modão de 2024 pra um churrasco e depois um pagode" vira duas
partes; cada parte é uma lista de grupos (um por expressão reconhecida:
"modão" → sertanejo raiz/romântico/sofrido, "2024" → época, "churrasco" →
ocasião). Uma música entra se satisfaz todo grupo forte (AND); dentro do
grupo, qualquer alvo serve (OR). "sem"/"nada de"/"não" negam o grupo
seguinte; "ou" separa ramos alternativos. Palavra que não é gíria nem nome
de gênero/obra/artista vira texto livre, buscado no título/obra/artista.

Ocasião bate de dois jeitos: a música marcada com ela, ou o perfil da
ocasião (gênero que combina, energia na faixa, nenhum clima a evitar).

Protótipo da etapa 2 do banco (docs/etapas/banco-fredify.md): ainda não é
usado pelo app; a etapa 4 liga no Freddy. Lógica pura, sem rede nem som.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from freddy.catalogo.compilar import chave
from freddy.nucleo.texto import normalizar

MAX_PALAVRAS_NA_EXPRESSAO = 6
PESO_FORTE = 0.6  # grupo com algum alvo de peso >= isso filtra; abaixo, só pontua

_SEPARA_PARTES = re.compile(r"\b(?:e depois|depois disso|depois|e em seguida|em seguida|e entao|e ai)\b")
_NEGACAO = {"sem", "nao", "menos", "nada"}
_ENCHIMENTO = {
    "toca", "toque", "tocar", "coloca", "coloque", "colocar", "bota", "bote", "poe", "ponha", "manda",
    "solta", "quero", "queria", "ouvir", "escutar", "me", "ai", "por", "favor", "pf", "pfv", "agora",
    "musica", "musicas", "som", "sons", "faixa", "faixas", "cancao", "trilha", "algo", "alguma",
    "algum", "umas", "uns", "uma", "um", "de", "do", "da", "dos", "das", "a", "o", "as", "os", "e",
    "para", "pra", "pro", "pros", "pras", "com", "no", "na", "nos", "nas", "em", "tipo", "bem",
    "muito", "mais", "clima", "cena", "hora", "estilo", "vibe", "que", "seja", "so", "aquele",
    "aquela", "aqueles", "aquelas", "esse", "essa", "isso", "lista", "playlist", "seleção", "selecao",
}
# Gêneros (famílias) que contam como "brasileira" quando a música não diz o idioma.
_FAMILIAS_BR = {"mpb", "samba", "sertanejo", "forro", "axe", "brega", "regional-br", "funk-br",
                "rap-nacional", "trap-nacional", "rock-nacional", "pop-nacional", "reggae-nacional",
                "soul-brasileiro", "trilha-de-novela", "musica-catolica"}


@dataclass(frozen=True)
class Alvo:
    tipo: str
    alvo: str
    peso: float


@dataclass
class Grupo:
    texto: str
    alvos: list[Alvo]
    negado: bool = False

    @property
    def forte(self) -> bool:
        return self.negado or max(a.peso for a in self.alvos) >= PESO_FORTE


@dataclass
class Ramo:
    grupos: list[Grupo] = field(default_factory=list)
    livre: list[str] = field(default_factory=list)


@dataclass
class Parte:
    texto: str
    ramos: list[Ramo]

    def alvos(self) -> set[str]:
        """'tipo:alvo' (com '!' na frente se negado) de todos os ramos: pra teste e depuração."""
        return {("!" if g.negado else "") + f"{a.tipo}:{a.alvo}"
                for r in self.ramos for g in r.grupos for a in g.alvos}


@dataclass
class Achado:
    musica: str
    pontos: float


@dataclass
class Resposta:
    parte: Parte
    achados: list[Achado]
    aproximado: bool  # nenhuma música satisfez tudo: devolveu as que chegaram mais perto
    ignorado: list[str]  # palavras que não ajudaram em nada


class Catalogo:
    """O catalogo.db carregado na memória (5 mil músicas cabem folgado)."""

    def __init__(self, caminho: Path | str):
        con = sqlite3.connect(f"file:{caminho}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            self._carregar(con)
        finally:
            con.close()

    def _carregar(self, con: sqlite3.Connection) -> None:
        self.palavras: dict[str, list[Alvo]] = {}
        for r in con.execute("SELECT palavra, tipo, alvo, peso FROM palavra"):
            self.palavras.setdefault(r["palavra"], []).append(Alvo(r["tipo"], r["alvo"], r["peso"]))
        self.pai = {r["id"]: r["pai"] for r in con.execute("SELECT id, pai FROM genero")}
        self.perfis = {r["ocasiao"]: dict(r) for r in con.execute("SELECT * FROM ocasiao_perfil")}
        self.musicas = {r["id"]: dict(r) for r in con.execute("SELECT * FROM musica")}
        for m in self.musicas.values():
            m["generos"], m["tags"], m["artistas"] = {}, {}, set()
        for r in con.execute("SELECT * FROM musica_genero"):
            m = self.musicas[r["musica"]]
            for g in self.linhagem(r["genero"]):  # a música de 'piseiro' também é 'forro'
                m["generos"][g] = max(m["generos"].get(g, 0), r["peso"])
        for r in con.execute("SELECT * FROM musica_tag"):
            self.musicas[r["musica"]]["tags"][r["tag"]] = r["peso"]
        for r in con.execute("SELECT * FROM musica_artista"):
            self.musicas[r["musica"]]["artistas"].add(r["artista"])
        self.texto = {r["musica"]: normalizar(" ".join(r[c] for c in ("titulo", "artista", "obra")))
                      for r in con.execute("SELECT * FROM busca")}

    def linhagem(self, genero: str) -> list[str]:
        saida = []
        while genero:
            saida.append(genero)
            genero = self.pai.get(genero)
        return saida

    # ---------- entender ----------

    def interpretar(self, pedido: str) -> list[Parte]:
        partes = []
        for pedaco in _SEPARA_PARTES.split(normalizar(pedido)):
            ramos = [self._ramo(r) for r in re.split(r"\bou\b", pedaco)]
            ramos = [r for r in ramos if r.grupos or r.livre]
            if ramos:
                partes.append(Parte(pedaco.strip(), ramos))
        return partes

    def _ramo(self, texto: str) -> Ramo:
        tokens = chave(texto).split()
        ramo, negar, i = Ramo(), False, 0
        while i < len(tokens):
            achou = None
            for n in range(min(MAX_PALAVRAS_NA_EXPRESSAO, len(tokens) - i), 0, -1):
                expr = " ".join(tokens[i:i + n])
                if expr in self.palavras and expr not in _ENCHIMENTO:
                    achou = (expr, list(self.palavras[expr]), n)
                    break
            tok = tokens[i]
            if not achou and re.fullmatch(r"(19|20)\d{2}", tok):
                achou = (tok, [Alvo("epoca", f"{tok}-{tok}", 1.0)], 1)
            if achou:
                expr, alvos, n = achou
                ramo.grupos.append(Grupo(expr, alvos, negar))
                negar, i = False, i + n
                continue
            if tok in _NEGACAO:
                negar = True
            elif tok not in _ENCHIMENTO and len(tok) > 1:
                ramo.livre.append(tok)
            i += 1
        return ramo

    # ---------- casar ----------

    def forca(self, m: dict, a: Alvo) -> float:
        """Quanto a música m satisfaz o alvo (0 = nada)."""
        t, alvo = a.tipo, a.alvo
        if t == "genero":
            return a.peso * m["generos"].get(alvo, 0)
        if t in ("clima", "tema", "instrumento", "cenario"):
            return a.peso * m["tags"].get(alvo, 0)
        if t == "ocasiao":
            if alvo in m["tags"]:
                return a.peso * m["tags"][alvo]
            return a.peso * 0.7 * self._cabe_no_perfil(m, alvo)
        if t == "obra":
            return a.peso if m["obra"] == alvo else 0
        if t == "artista":
            return a.peso if alvo in m["artistas"] else 0
        if t == "epoca":
            return a.peso if self._na_epoca(m["ano"], alvo) else 0
        if t == "campo":
            return a.peso if self._campo(m, alvo) else 0
        return 0

    def _cabe_no_perfil(self, m: dict, ocasiao: str) -> float:
        p = self.perfis.get(ocasiao)
        if not p or m["energia"] is None:
            return 0
        if not set(p["generos"].split("|")) & set(m["generos"]):
            return 0
        if not p["energia_min"] <= m["energia"] <= p["energia_max"]:
            return 0
        if p["voz"] == "sim" and not m["tem_voz"] or p["voz"] == "nao" and m["tem_voz"]:
            return 0
        if any(m["tags"].get(c, 0) >= 0.8 for c in p["climas_evitar"].split("|")):
            return 0
        combina = sum(m["tags"].get(c, 0) for c in p["climas_combinam"].split("|"))
        if not combina:  # gênero e energia certos mas nenhum clima da ocasião: não basta
            return 0
        return min(1.0, 0.5 + 0.5 * combina)

    @staticmethod
    def _na_epoca(ano: int | None, epoca: str) -> bool:
        if ano is None:
            return False
        hoje = date.today().year
        if epoca.startswith("ate-"):
            return ano <= int(epoca[4:])
        if epoca.startswith("ultimos-"):
            n, unidade = epoca.split("-")[1:]
            return ano >= hoje - (int(n) - 1 if unidade == "anos" else 1)
        ini, fim = (int(x) for x in epoca.split("-"))
        return ini <= ano <= fim

    def _campo(self, m: dict, campo: str) -> bool:
        brasileira = m["idioma"] == "pt" or (m["idioma"] is None and bool(_FAMILIAS_BR & set(m["generos"])))
        return {
            "popularidade-alta": m["popularidade"] >= 70, "essencial": bool(m["essencial"]),
            "canta-junto": bool(m["canta_junto"]), "ao-vivo": bool(m["ao_vivo"]),
            "acustico": bool({"violao", "piano"} & set(m["tags"])),
            "sem-voz": not m["tem_voz"], "com-voz": bool(m["tem_voz"]),
            "nao-explicita": not m["explicita"], "brasileira": brasileira,
            "internacional": not brasileira,
        }.get(campo, False)

    # ---------- buscar ----------

    def buscar(self, pedido: str, limite: int = 15) -> list[Resposta]:
        return [self._buscar_parte(p, limite) for p in self.interpretar(pedido)]

    def _buscar_parte(self, parte: Parte, limite: int) -> Resposta:
        melhor: dict[str, float] = {}
        aproximado_em_todos, ignorado = True, []
        for ramo in parte.ramos:
            livre = ramo.livre
            if livre and not any(self._texto_bate(mid, livre) for mid in self.musicas):
                ignorado += livre
                livre = []
            pontos, exato = self._pontuar(ramo.grupos, livre)
            aproximado_em_todos &= not exato
            for mid, p in pontos.items():
                melhor[mid] = max(melhor.get(mid, 0), p)
        ordem = sorted(melhor.items(), key=lambda kv: (-kv[1], kv[0]))[:limite]
        return Resposta(parte, [Achado(mid, round(p, 3)) for mid, p in ordem],
                        aproximado_em_todos and bool(ordem), ignorado)

    def _texto_bate(self, mid: str, palavras: list[str]) -> bool:
        texto = self.texto.get(mid, "")
        return all(re.search(r"\b" + re.escape(p), texto) for p in palavras)

    def _pontuar(self, grupos: list[Grupo], livre: list[str]) -> tuple[dict[str, float], bool]:
        exigidos = [g for g in grupos if g.forte and not g.negado]
        negados = [g for g in grupos if g.negado]
        candidatos: list[tuple[int, float, str]] = []
        for mid, m in self.musicas.items():
            if livre and not self._texto_bate(mid, livre):
                continue
            if any(max(self.forca(m, a) for a in g.alvos) >= 0.4 for g in negados):
                continue
            pontos, cumpridos = 0.0, 0
            for g in grupos:
                if g.negado:
                    continue
                f = max(self.forca(m, a) for a in g.alvos)
                if f > 0:
                    pontos += f
                    cumpridos += g in exigidos
            if not grupos and not livre:
                continue
            pontos += 0.2 * m["popularidade"] / 100 + (1.0 if livre else 0)
            candidatos.append((cumpridos, pontos, mid))
        if not candidatos:
            return {}, False
        if not exigidos:
            sobra = [c for c in candidatos if c[1] > 0.2 * 1.0 or livre]
            return {mid: p for _, p, mid in sobra if p > 0.2 or livre}, True
        maximo = max(c[0] for c in candidatos)
        if maximo == 0:
            return {}, False
        return {mid: p for c, p, mid in candidatos if c == maximo}, maximo == len(exigidos)


def abrir(caminho: Path | str | None = None) -> Catalogo:
    from freddy.catalogo.compilar import SAIDA_PADRAO

    return Catalogo(caminho or SAIDA_PADRAO)
