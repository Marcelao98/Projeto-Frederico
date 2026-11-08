"""Compila o catálogo (acervo/catalogo/*.csv) no catalogo.db e confere as regras.

    python -m freddy.catalogo.compilar            # gera acervo/catalogo.db
    python -m freddy.catalogo.compilar --conferir # só confere, não grava

Regras (docs/etapas/banco-fredify.md): toda música com gênero, energia,
animação, ≥ 2 climas e popularidade; ano e fonte oficial viva. As faixas do
lote "rpg-legado" (vindas do musicas.json) e as marcadas "revisar" têm parte
disso cobrado só como aviso. Erro barra a compilação; aviso só é contado.
"""

from __future__ import annotations

import argparse
import csv
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from freddy.nucleo.texto import normalizar


def chave(texto: str) -> str:
    """Como uma expressão é guardada e procurada: minúscula, sem acento nem pontuação."""
    return " ".join(re.findall(r"[a-z0-9&+-]+", normalizar(texto).replace("'", "")))

RAIZ = Path(__file__).resolve().parents[3]
PASTA_CATALOGO = RAIZ / "acervo" / "catalogo"
SAIDA_PADRAO = RAIZ / "acervo" / "catalogo.db"
ESQUEMA = Path(__file__).with_name("esquema.sql")

LOTES_LEGADO = {"rpg-legado"}
GAVETAS = ("clima", "ocasiao", "tema", "instrumento", "cenario")
CAMPOS = {"popularidade-alta", "essencial", "canta-junto", "ao-vivo", "acustico", "sem-voz",
          "com-voz", "nao-explicita", "internacional", "brasileira"}
EPOCA_RE = re.compile(r"^(\d{4}-\d{4}|ate-\d{4}|ultimos-\d+-(anos|meses))$")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


@dataclass
class Resultado:
    erros: list[str] = field(default_factory=list)
    avisos: dict[str, int] = field(default_factory=dict)

    def aviso(self, tipo: str) -> None:
        self.avisos[tipo] = self.avisos.get(tipo, 0) + 1


def _ler(pasta: Path, nome: str) -> list[dict]:
    with open(pasta / nome, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _int(v: str) -> int | None:
    return int(v) if v.strip() else None


def carregar(pasta: Path = PASTA_CATALOGO) -> dict[str, list[dict]]:
    nomes = ["generos", "tags", "ocasioes_perfil", "palavras", "obras", "artistas", "musicas",
             "musica_artista", "musica_genero", "musica_tag", "fontes"]
    return {n: _ler(pasta, n + ".csv") for n in nomes}


def conferir(d: dict[str, list[dict]]) -> Resultado:
    r = Resultado()
    err = r.erros.append

    generos = {g["id"]: g for g in d["generos"]}
    tags = {t["id"]: t for t in d["tags"]}
    obras = {o["id"] for o in d["obras"]}
    artistas = {a["id"] for a in d["artistas"]}
    for nome, linhas in (("gênero", d["generos"]), ("tag", d["tags"]), ("obra", d["obras"]),
                         ("artista", d["artistas"]), ("música", d["musicas"])):
        vistos: set[str] = set()
        for l in linhas:
            if l["id"] in vistos:
                err(f"{nome} repetido: {l['id']}")
            vistos.add(l["id"])
            if nome != "música" and not ID_RE.match(l["id"]):
                err(f"{nome} com id fora do padrão (minúsculas, sem acento, hífen): {l['id']!r}")

    for g in generos.values():
        visto, atual = set(), g["id"]
        while atual:
            if atual in visto:
                err(f"gênero em ciclo: {g['id']}")
                break
            visto.add(atual)
            pai = generos[atual]["pai"] if atual in generos else ""
            if pai and pai not in generos:
                err(f"gênero {atual}: pai {pai} não existe")
                break
            atual = pai
    for t in tags.values():
        if t["gaveta"] not in GAVETAS:
            err(f"tag {t['id']}: gaveta {t['gaveta']!r} não existe")

    def tag_de(gaveta: str, alvo: str) -> bool:
        return alvo in tags and tags[alvo]["gaveta"] == gaveta

    def alvo_ok(tipo: str, alvo: str) -> bool:
        if tipo == "genero":
            return alvo in generos
        if tipo in GAVETAS:
            return tag_de(tipo, alvo)
        if tipo == "epoca":
            return bool(EPOCA_RE.match(alvo))
        if tipo == "campo":
            return alvo in CAMPOS
        return False

    perfis = set()
    for p in d["ocasioes_perfil"]:
        oc = p["ocasiao"]
        perfis.add(oc)
        if not tag_de("ocasiao", oc):
            err(f"perfil de ocasião que não existe: {oc}")
        for g in p["generos_combinam"].split("|"):
            if g not in generos:
                err(f"perfil {oc}: gênero {g} não existe")
        combinam, evitar = p["climas_combinam"].split("|"), p["climas_evitar"].split("|")
        for c in combinam + evitar:
            if not tag_de("clima", c):
                err(f"perfil {oc}: clima {c} não existe")
        if set(combinam) & set(evitar):
            err(f"perfil {oc}: clima ao mesmo tempo em combinam e evitar")
        if not 1 <= int(p["energia_min"]) <= int(p["energia_max"]) <= 5:
            err(f"perfil {oc}: energia fora de 1–5")
        if p["voz"] not in ("sim", "nao", "qualquer"):
            err(f"perfil {oc}: voz {p['voz']!r}")
    for oc in (t for t in tags.values() if t["gaveta"] == "ocasiao"):
        if oc["id"] not in perfis:
            err(f"ocasião sem perfil: {oc['id']}")

    vistas = set()
    for p in d["palavras"]:
        chave_ = (chave(p["palavra"]), p["tipo"], p["alvo"])
        if chave_ in vistas:
            err(f"gíria repetida: {p['palavra']} → {p['tipo']}:{p['alvo']}")
        vistas.add(chave_)
        if not alvo_ok(p["tipo"], p["alvo"]):
            err(f"gíria {p['palavra']!r} aponta pra {p['tipo']}:{p['alvo']}, que não existe")
        if not 0 < float(p["peso"]) <= 1:
            err(f"gíria {p['palavra']!r}: peso fora de 0–1")

    musicas = {m["id"]: m for m in d["musicas"]}
    gen_de: dict[str, list[str]] = {}
    climas_de: dict[str, list[str]] = {}
    fontes_de: dict[str, list[dict]] = {}
    for l in d["musica_genero"]:
        if l["musica"] not in musicas or l["genero"] not in generos:
            err(f"musica_genero inválido: {l['musica']} → {l['genero']}")
        gen_de.setdefault(l["musica"], []).append(l["genero"])
    for l in d["musica_tag"]:
        if l["musica"] not in musicas or l["tag"] not in tags:
            err(f"musica_tag inválido: {l['musica']} → {l['tag']}")
        elif tags[l["tag"]]["gaveta"] == "clima":
            climas_de.setdefault(l["musica"], []).append(l["tag"])
    for l in d["musica_artista"]:
        if l["musica"] not in musicas or l["artista"] not in artistas:
            err(f"musica_artista inválido: {l['musica']} → {l['artista']}")
    for l in d["fontes"]:
        if l["musica"] not in musicas:
            err(f"fonte de música que não existe: {l['musica']}")
        fontes_de.setdefault(l["musica"], []).append(l)

    ano_max = date.today().year + 1
    for m in musicas.values():
        mid = m["id"]
        legado, revisar = m["lote"] in LOTES_LEGADO, m["revisar"] == "1"
        if m["obra"] and m["obra"] not in obras:
            err(f"{mid}: obra {m['obra']} não existe")
        if not gen_de.get(mid):
            err(f"{mid}: sem gênero")
        if not m["popularidade"].strip():
            err(f"{mid}: sem popularidade")
        if revisar:
            r.aviso("música marcada pra revisar (sem clima/energia)")
        else:
            if not m["energia"].strip() or not m["animacao"].strip():
                err(f"{mid}: sem energia ou animação")
            if len(climas_de.get(mid, [])) < 2:
                err(f"{mid}: menos de 2 climas")
        ano = _int(m["ano"])
        if ano is not None and not 1600 <= ano <= ano_max:
            err(f"{mid}: ano {ano} estranho")
        boas = [f for f in fontes_de.get(mid, []) if f["oficial"] == "1" and f["viva"] == "1"]
        if not fontes_de.get(mid):
            err(f"{mid}: sem fonte")
        for falta, ok in (("sem ano", ano is not None), ("sem fonte oficial viva", bool(boas))):
            if not ok:
                if legado:
                    r.aviso(f"legado {falta}")
                else:
                    err(f"{mid}: {falta}")
    return r


def _palavras_automaticas(d: dict[str, list[dict]]) -> list[tuple[str, str, str, float]]:
    """Todo gênero, tag, obra e artista também é palavra (pelo nome e pelo id)."""
    saida = []
    for g in d["generos"]:
        saida += [(g["nome"], "genero", g["id"], 1.0),
                  (g["id"].replace("-", " "), "genero", g["id"], 1.0)]
    for t in d["tags"]:
        nome = re.sub(r"^rpg: ", "", normalizar(t["nome"]))  # "RPG: taverna" também é "taverna"
        saida += [(nome, t["gaveta"], t["id"], 0.9), (t["id"].replace("-", " "), t["gaveta"], t["id"], 0.9)]
    for o in d["obras"]:
        saida += [(o["nome"], "obra", o["id"], 1.0)]
        saida += [(apelido, "obra", o["id"], 1.0) for apelido in o.get("apelidos", "").split("|") if apelido]
    for a in d["artistas"]:
        saida.append((a["nome"], "artista", a["id"], 1.0))
    return [(chave(p), t, a, w) for p, t, a, w in saida if chave(p)]


def gravar(d: dict[str, list[dict]], saida: Path) -> None:
    saida.parent.mkdir(parents=True, exist_ok=True)
    tmp = saida.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        con.executescript(ESQUEMA.read_text(encoding="utf-8"))
        n = lambda v: v if v != "" else None  # noqa: E731
        con.executemany("INSERT INTO genero VALUES (?,?,?,?)",
                        [(g["id"], g["nome"], n(g["pai"]), n(g["nota"])) for g in d["generos"]])
        con.executemany("INSERT INTO tag VALUES (?,?,?,?)",
                        [(t["id"], t["gaveta"], t["nome"], n(t["nota"])) for t in d["tags"]])
        con.executemany("INSERT INTO obra VALUES (?,?,?,?)",
                        [(o["id"], o["nome"], o["tipo"], _int(o["ano"])) for o in d["obras"]])
        con.executemany("INSERT INTO artista VALUES (?,?,?,?,?,?,?)",
                        [(a["id"], a["nome"], n(a["tipo"]), n(a["pais"]), n(a["regiao"]),
                          _int(a["ano_inicio"]), n(a["mbid"])) for a in d["artistas"]])
        cols = ["id", "titulo", "ano", "duracao", "idioma", "obra", "energia", "animacao", "tem_voz",
                "canta_junto", "ao_vivo", "explicita", "popularidade", "essencial", "mbid", "isrc",
                "lote", "revisar", "nome_original"]
        inteiros = {"ano", "duracao", "energia", "animacao", "tem_voz", "canta_junto", "ao_vivo",
                    "explicita", "popularidade", "essencial", "revisar"}
        con.executemany(f"INSERT INTO musica VALUES ({','.join('?' * len(cols))})",
                        [tuple(_int(m[c]) if c in inteiros else n(m[c]) for c in cols) for m in d["musicas"]])
        con.executemany("INSERT INTO musica_artista VALUES (?,?,?)",
                        [(l["musica"], l["artista"], l["papel"]) for l in d["musica_artista"]])
        con.executemany("INSERT INTO musica_genero VALUES (?,?,?)",
                        [(l["musica"], l["genero"], float(l["peso"])) for l in d["musica_genero"]])
        con.executemany("INSERT INTO musica_tag VALUES (?,?,?,?)",
                        [(l["musica"], l["tag"], float(l["peso"]), l["quem_marcou"]) for l in d["musica_tag"]])
        con.executemany("INSERT INTO fonte VALUES (?,?,?,?,?,?)",
                        [(l["musica"], l["tipo"], l["endereco"], int(l["oficial"]), int(l["viva"]),
                          n(l["conferida_em"])) for l in d["fontes"]])
        palavras = [(chave(p["palavra"]), p["tipo"], p["alvo"], float(p["peso"])) for p in d["palavras"]]
        con.executemany("INSERT INTO palavra VALUES (?,?,?,?)", palavras)
        # As automáticas não passam por cima de uma gíria escrita à mão.
        con.executemany("INSERT OR IGNORE INTO palavra VALUES (?,?,?,?)", _palavras_automaticas(d))
        con.executemany("INSERT INTO ocasiao_perfil VALUES (?,?,?,?,?,?,?)",
                        [(p["ocasiao"], p["generos_combinam"], int(p["energia_min"]), int(p["energia_max"]),
                          p["voz"], p["climas_combinam"], p["climas_evitar"]) for p in d["ocasioes_perfil"]])
        con.execute("""
            INSERT INTO busca (musica, titulo, artista, obra, generos, tags)
            SELECT m.id, m.titulo || ' ' || COALESCE(m.nome_original, ''),
                   COALESCE((SELECT group_concat(a.nome, ' ') FROM musica_artista ma
                             JOIN artista a ON a.id = ma.artista WHERE ma.musica = m.id), ''),
                   COALESCE((SELECT o.nome FROM obra o WHERE o.id = m.obra), ''),
                   COALESCE((SELECT group_concat(g.nome, ' ') FROM musica_genero mg
                             JOIN genero g ON g.id = mg.genero WHERE mg.musica = m.id), ''),
                   COALESCE((SELECT group_concat(t.nome, ' ') FROM musica_tag mt
                             JOIN tag t ON t.id = mt.tag WHERE mt.musica = m.id), '')
            FROM musica m""")
        con.executemany("INSERT INTO info VALUES (?,?)",
                        [("musicas", str(len(d["musicas"]))), ("compilado_em", date.today().isoformat())])
        problemas = con.execute("PRAGMA foreign_key_check").fetchall()
        if problemas:
            raise RuntimeError(f"chave estrangeira quebrada no catálogo: {problemas[:5]}")
        con.commit()
    finally:
        con.close()
    tmp.replace(saida)


def compilar(pasta: Path = PASTA_CATALOGO, saida: Path | None = SAIDA_PADRAO) -> Resultado:
    d = carregar(pasta)
    r = conferir(d)
    if not r.erros and saida is not None:
        gravar(d, saida)
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compila acervo/catalogo/*.csv no catalogo.db")
    ap.add_argument("--conferir", action="store_true", help="só confere as regras, não grava")
    ap.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = ap.parse_args(argv)
    r = compilar(saida=None if args.conferir else args.saida)
    for e in r.erros[:50]:
        print("ERRO:", e)
    if len(r.erros) > 50:
        print(f"... e mais {len(r.erros) - 50} erros")
    for tipo, qtd in sorted(r.avisos.items()):
        print(f"aviso: {tipo}: {qtd}")
    if r.erros:
        print(f"{len(r.erros)} erros: catálogo NÃO compilado.")
        return 1
    print("Catálogo conferido." if args.conferir else f"Catálogo compilado em {args.saida}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
