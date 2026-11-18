"""Trilhas instrumentais (jogo, anime, filme, Ghibli) no catálogo: o formato e a importação.

Lógica pura (sem rede): quem fala com o YouTube é backend/scripts/catalogo_ost.py.
O guia completo é docs/etapas/catalogo-ost.md.

    acervo/catalogo/ost/obras.csv        as obras (o Marcelo corta e acrescenta)
    acervo/catalogo/ost/faixas/<id>.csv  as faixas REAIS da playlist (o script
                                         extrai) + as colunas de classificação
                                         (a IA preenche, uma obra por vez)

O nome e o link de cada faixa vêm da playlist do YouTube, nunca da IA: assim
não tem faixa inventada. A IA só classifica.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from freddy.nucleo.texto import normalizar, slug

RAIZ = Path(__file__).resolve().parents[3]
PASTA_OST = RAIZ / "acervo" / "catalogo" / "ost"
PASTA_FAIXAS = PASTA_OST / "faixas"
LOTE = "ost"

COLUNAS_OBRA = ["id", "nome", "tipo", "ano", "compositor", "apelidos", "grupo", "meta", "playlist", "nota"]
# As 6 primeiras o script preenche; o resto é a classificação.
COLUNAS_FAIXA = ["ordem", "titulo", "link", "duracao", "canal", "oficial",
                 "fora", "uso", "cenarios", "climas", "energia", "animacao", "tem_voz", "estavel",
                 "instrumentos", "ocasioes", "popularidade", "essencial", "nota"]
GENERO_DO_TIPO = {"jogo": "trilha-de-jogo", "anime": "trilha-de-anime", "filme": "trilha-de-filme",
                  "série": "trilha-de-serie", "novela": "trilha-de-novela", "álbum": "epic-music",
                  "visual novel": "trilha-de-jogo"}
DURACAO_MIN, DURACAO_MAX = 40, 900  # menos é vinheta; mais é compilação ("1 hour")

_LIXO_NO_NOME = re.compile(
    r"\b(cover|covers|remix|piano version|piano cover|piano solo|for piano|piano arrangement|electone|orchestral cover|guitar cover|lyrics?|letra|"
    r"1 hour|one hour|10 hours|extended|slowed|sped up|nightcore|8d audio|reaction|tutorial|"
    r"music box|lofi|lo-fi|ringtone|trailer|teaser|gameplay|walkthrough|full album|full soundtrack|"
    r"full ost|complete soundtrack|ost compilation)\b", re.IGNORECASE)

_ROTULO = re.compile(r"\b(music|song|songs|ambien\w*|soundtrack|ost|epic|medieval|fantasy|celtic|relaxing|"
                    r"rpg|d&d|dnd|tabletop|instrumental|official|video|audio)\b", re.IGNORECASE)
# Playlist que é arranjo, não a trilha: piano, lofi, cover, remix, compilação de 1 hora...
_PLAYLIST_RUIM = re.compile(r"cover|remix|piano|lofi|lo-fi|\b1 hour|\b10 hours|music box|reaction|"
                            r"orchestral version|8.?bit version|acapella|a cappella", re.IGNORECASE)


# ---------- ler e gravar ----------

def ler(caminho: Path) -> list[dict]:
    if not caminho.exists():
        return []
    with open(caminho, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def gravar(caminho: Path, colunas: list[str], linhas: list[dict]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, colunas, delimiter=";", lineterminator="\n", restval="", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


def obras(pasta: Path = PASTA_OST) -> list[dict]:
    return ler(pasta / "obras.csv")


def faixas_de(obra_id: str, pasta: Path = PASTA_FAIXAS) -> list[dict]:
    return ler(pasta / f"{obra_id}.csv")


# ---------- extrair (o que o script decide com o que o YouTube devolveu) ----------

def limpar_titulo(titulo: str, obra_nome: str = "") -> str:
    """'Hollow Knight OST - Greenpath' → 'Greenpath'; '01. Dirtmouth' → 'Dirtmouth'."""
    t = re.sub(r"「[^」]*」|【[^】]*】|\[[^\]]*(?:OST|Soundtrack|HD|HQ|Audio|Official)[^\]]*\]", "", titulo, flags=re.IGNORECASE)
    t = re.sub(r"\([^()]*(?:Original|Soundtrack|OST|Official|Audio|HD|HQ|From [\"“'])[^()]*(?:\)|$)", "", t,
               flags=re.IGNORECASE)
    t = re.sub(r"^.*?\b(?:OST|O\.S\.T\.|Soundtrack)\s*[-–:|]\s*", "", t, flags=re.IGNORECASE)
    if obra_nome:  # "Elden Ring - Godrick the Grafted" / "Godrick the Grafted | Elden Ring"
        nome = re.escape(obra_nome)
        t = re.sub(rf"^\s*{nome}\s*[-–:|]\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(rf"\s*[-–|]\s*{nome}\s*$", "", t, flags=re.IGNORECASE)
    # "Souls of Fire - Dark Souls Soundtrack 01" / "Greenpath | Hollow Knight OST" / "… | Epic Medieval Music"
    t = re.sub(r"\s*[-–|]\s*[^-–|]*\b(?:Soundtrack|OST|O\.S\.T\.)\b[^-–|]*$", "", t, flags=re.IGNORECASE)
    partes = [x.strip() for x in t.split("|") if x.strip()]
    if len(partes) > 1:  # "🎵 RPG Combat Music | Paladin's Resolve": fica a parte que é nome, não rótulo
        nomes = [x for x in partes if not _ROTULO.search(x)]
        t = nomes[0] if nomes else partes[0]
    t = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", t)
    t = re.sub(r"^\s*(?:track\s*)?\d{1,3}\s*[.\-–)]?\s+", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*[-–|]\s*(?:OST|Soundtrack)\s*$", "", t, flags=re.IGNORECASE)
    return re.sub(r"\s{2,}", " ", t).strip(" -–|:")


def _bate(a: str, b: str) -> bool:
    a, b = re.sub(r"[^a-z0-9]", "", normalizar(a)), re.sub(r"[^a-z0-9]", "", normalizar(b))
    return bool(a) and a in b


def nomes_proprios(obra: dict, todas: list[dict]) -> list[str]:
    """O nome e os apelidos SÓ dessa obra ('ghibli', 'zelda', 'souls' são de várias: não servem pra achar a playlist)."""
    contagem: dict[str, int] = {}
    for o in todas:
        for a in {x for x in o.get("apelidos", "").split("|") if x}:
            contagem[a] = contagem.get(a, 0) + 1
    return [obra["nome"]] + [a for a in obra.get("apelidos", "").split("|") if a and contagem.get(a, 0) == 1]


def nota_da_playlist(obra: dict, titulo: str, n_validas: int, canal: str = "") -> float:
    """Quanto uma playlist parece a trilha dessa obra (maior = melhor). 0 = não serve."""
    if not n_validas or _PLAYLIST_RUIM.search(titulo):
        return 0
    nomes = obra.get("_proprios") or [obra["nome"]]
    if not any(_bate(n, titulo) for n in nomes) and not (
            obra.get("tipo") == "álbum" and any(_bate(c, canal) for c in obra.get("compositor", "").split("|") if c)):
        return 0
    nota = min(n_validas, 120)
    if obra.get("tipo") != "álbum" and re.search(r"\b(original|soundtrack|ost)\b", titulo, re.IGNORECASE):
        nota += 15
    return nota


def faixas_validas(obra: dict, videos: list[dict]) -> list[dict]:
    """Das entradas de uma playlist: as que são faixa da trilha, limpas e sem repetir."""
    saida, vistas = [], set()
    compositores = [c for c in obra.get("compositor", "").split("|") if c]
    for v in videos:
        bruto = v.get("title") or ""
        if not v.get("id") or bruto.lower() in ("[deleted video]", "[private video]"):
            continue
        d = v.get("duration")
        if d is not None and not DURACAO_MIN <= d <= DURACAO_MAX:
            continue
        if _LIXO_NO_NOME.search(bruto):
            continue
        titulo = limpar_titulo(bruto, obra["nome"]) or bruto
        k = slug(titulo)
        if not k or k in vistas:
            continue
        vistas.add(k)
        canal = v.get("channel") or v.get("uploader") or ""
        oficial = canal.endswith(" - Topic") or any(_bate(c, canal) for c in compositores)
        if obra.get("tipo") == "álbum" and not oficial:
            continue  # artista/estilo: só o que o próprio artista subiu (fora: música feita por IA, cópia)
        saida.append({"titulo": titulo, "link": f"https://www.youtube.com/watch?v={v['id']}",
                      "duracao": int(d) if d else "", "canal": canal, "oficial": "1" if oficial else "0"})
    for i, f in enumerate(saida, 1):
        f["ordem"] = str(i)
    return saida


# ---------- classificar (formato compacto de uma linha por faixa) ----------

MARCA = "ordem|uso|cenarios|climas|energia|animacao|flags|instrumentos|ocasioes|popularidade|nota"
# flags: V = tem voz (coral com letra conta), S = estável (sem susto/pico: serve de fundo),
#        E = essencial (a faixa mais famosa da obra), X = fora (não é faixa boa: vinheta, jingle, repetida)


def aplicar_marcas(faixas: list[dict], linhas: list[str]) -> tuple[int, list[str]]:
    """Grava as marcas compactas nas faixas (pela ordem). Devolve (quantas, erros)."""
    por_ordem = {f["ordem"]: f for f in faixas}
    erros, n = [], 0
    for bruta in linhas:
        bruta = bruta.strip()
        if not bruta or bruta.startswith("#"):
            continue
        c = [x.strip() for x in bruta.split("|")] + [""] * 11
        f = por_ordem.get(c[0])
        if f is None:
            erros.append(f"faixa {c[0]!r} não existe")
            continue
        flags = c[6].upper()
        lista = lambda s: "|".join(x.strip() for x in s.split(",") if x.strip())  # noqa: E731
        f.update({"fora": "1" if "X" in flags else "0", "uso": lista(c[1]), "cenarios": lista(c[2]),
                  "climas": lista(c[3]), "energia": c[4], "animacao": c[5],
                  "tem_voz": "1" if "V" in flags else "0", "estavel": "1" if "S" in flags else "0",
                  "essencial": "1" if "E" in flags else "0", "instrumentos": lista(c[7]),
                  "ocasioes": lista(c[8]), "popularidade": c[9], "nota": c[10]})
        n += 1
    return n, erros


def conferir_faixas(faixas: list[dict], tags: dict[str, str]) -> list[str]:
    """Erros da classificação de uma obra (tags: id -> gaveta)."""
    erros = []
    for f in faixas:
        if f.get("fora") == "1" or not f.get("climas"):
            continue
        onde = f"faixa {f['ordem']} ({f['titulo']})"
        for col, gaveta, minimo, maximo in (("climas", "clima", 2, 4), ("cenarios", "cenario", 0, 3),
                                             ("instrumentos", "instrumento", 0, 3)):
            ids = [x for x in f.get(col, "").split("|") if x]
            if not minimo <= len(ids) <= maximo:
                erros.append(f"{onde}: {col} precisa de {minimo} a {maximo}")
            erros += [f"{onde}: {gaveta} {x!r} não existe" for x in ids if tags.get(x) != gaveta]
        for col in ("uso", "ocasioes"):
            ids = [x for x in f.get(col, "").split("|") if x]
            erros += [f"{onde}: ocasião {x!r} não existe" for x in ids if tags.get(x) != "ocasiao"]
            if col == "uso":
                erros += [f"{onde}: uso {x!r} tem que ser rpg-*" for x in ids if not x.startswith("rpg-")]
            if col == "ocasioes":
                erros += [f"{onde}: {x!r} é de RPG: vai em uso" for x in ids if x.startswith("rpg-")]
        for col, lo, hi in (("energia", 1, 5), ("animacao", 1, 5), ("popularidade", 0, 100)):
            v = f.get(col, "")
            if not v.isdigit() or not lo <= int(v) <= hi:
                erros.append(f"{onde}: {col} {v!r} (de {lo} a {hi})")
    return erros


def situacao(obra: dict, faixas: list[dict]) -> str:
    if not faixas:
        return "falta extrair"
    marcadas = [f for f in faixas if f.get("climas") or f.get("fora") == "1"]
    if len(marcadas) < len(faixas):
        return f"falta classificar {len(faixas) - len(marcadas)}"
    return "PRONTA"


# ---------- importar pro catálogo ----------

@dataclass
class Importacao:
    obras: int = 0
    entraram: int = 0
    fora: int = 0
    repetidas_do_legado: int = 0
    sem_classificar: int = 0
    erros: list[str] = field(default_factory=list)


def importar(pasta_cat: Path, pasta_ost: Path = PASTA_OST) -> Importacao:
    """Põe as faixas classificadas no catálogo (lote 'ost'). Idempotente: refaz o lote inteiro."""
    rel = Importacao()
    nomes = ("musicas", "obras", "artistas", "musica_artista", "musica_genero", "musica_tag", "fontes")
    t = {n: ler(pasta_cat / f"{n}.csv") for n in nomes}
    cab = {n: list(t[n][0].keys()) for n in nomes}
    velhas = {m["id"] for m in t["musicas"] if m["lote"] == LOTE}
    for n in ("musica_artista", "musica_genero", "musica_tag", "fontes"):
        t[n] = [l for l in t[n] if l["musica"] not in velhas]
    t["musicas"] = [m for m in t["musicas"] if m["lote"] != LOTE]
    ids = {m["id"] for m in t["musicas"]}
    # A mesma faixa que já veio do acervo antigo (rpg-legado) não entra de novo.
    legado = {(m["obra"], slug(m["titulo"])) for m in t["musicas"] if m["obra"]}
    obras_cat = {o["id"]: o for o in t["obras"]}
    artistas = {a["id"]: a for a in t["artistas"]}
    tags = {x["id"]: x["gaveta"] for x in ler(pasta_cat / "tags.csv")}

    for o in obras(pasta_ost):
        faixas = faixas_de(o["id"], pasta_ost / "faixas")
        if not faixas:
            continue
        rel.erros += [f"{o['id']}: {e}" for e in conferir_faixas(faixas, tags)]
        prontas = [f for f in faixas if f.get("climas") and f.get("fora") != "1"]
        rel.fora += sum(1 for f in faixas if f.get("fora") == "1")
        rel.sem_classificar += sum(1 for f in faixas if not f.get("climas") and f.get("fora") != "1")
        if not prontas:
            continue
        rel.obras += 1
        if o["id"] not in obras_cat:
            obras_cat[o["id"]] = {"id": o["id"], "nome": o["nome"], "tipo": o["tipo"], "ano": o["ano"],
                                  "apelidos": o.get("apelidos", "")}
        elif o.get("apelidos"):  # junta os apelidos novos (ex.: 'ghibli') aos que já tinha
            ja = [a for a in obras_cat[o["id"]].get("apelidos", "").split("|") if a]
            obras_cat[o["id"]]["apelidos"] = "|".join(dict.fromkeys(ja + o["apelidos"].split("|")))
        compositores = [c.strip() for c in o.get("compositor", "").split("|") if c.strip()]
        genero = GENERO_DO_TIPO.get(o["tipo"], "trilha-sonora")
        for f in prontas:
            if (o["id"], slug(f["titulo"])) in legado:
                rel.repetidas_do_legado += 1
                continue
            mid = base = f"{o['id']}-{slug(f['titulo'])}"[:90].strip("-")
            n = 2
            while mid in ids:
                mid, n = f"{base}-{n}", n + 1
            ids.add(mid)
            t["musicas"].append({
                "id": mid, "titulo": f["titulo"], "ano": o["ano"], "duracao": f["duracao"],
                "idioma": "", "obra": o["id"], "energia": f["energia"], "animacao": f["animacao"],
                "tem_voz": f["tem_voz"] or "0", "canta_junto": "0", "ao_vivo": "0", "explicita": "0",
                "popularidade": f["popularidade"], "essencial": f["essencial"] or "0", "mbid": "",
                "isrc": "", "lote": LOTE, "revisar": "0", "nome_original": "", "estavel": f["estavel"]})
            for i, nome in enumerate(compositores):
                aid = slug(nome)
                artistas.setdefault(aid, {"id": aid, "nome": nome, "tipo": "", "pais": "", "regiao": "",
                                          "ano_inicio": "", "mbid": ""})
                t["musica_artista"].append({"musica": mid, "artista": aid,
                                            "papel": "principal" if i == 0 else "feat"})
            t["musica_genero"].append({"musica": mid, "genero": genero, "peso": "1.0"})
            if "chiptune" in f.get("nota", "").lower():
                t["musica_genero"].append({"musica": mid, "genero": "chiptune", "peso": "0.6"})
            marcas: dict[str, str] = {}
            for i, c in enumerate(x for x in f["climas"].split("|") if x):
                marcas.setdefault(c, "1.0" if i == 0 else "0.8")
            for col in ("uso", "cenarios", "ocasioes", "instrumentos"):
                for x in (x for x in f.get(col, "").split("|") if x):
                    marcas.setdefault(x, "0.9")
            t["musica_tag"] += [{"musica": mid, "tag": tg, "peso": p, "quem_marcou": "claude"}
                                for tg, p in marcas.items()]
            t["fontes"].append({"musica": mid, "tipo": "youtube", "endereco": f["link"],
                                "oficial": f["oficial"] or "0", "viva": "1", "conferida_em": ""})
            rel.entraram += 1
    t["obras"] = sorted(obras_cat.values(), key=lambda x: x["id"])
    t["artistas"] = sorted(artistas.values(), key=lambda x: x["id"])
    for n in nomes:
        gravar(pasta_cat / f"{n}.csv", cab[n], t[n])
    return rel
