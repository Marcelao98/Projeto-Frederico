"""Escolhas da etapa 3 (encher o catálogo em blocos), sem rede.

O script backend/scripts/catalogo_bloco.py busca no MusicBrainz e no YouTube
(roda no computador do Marcelo: a nuvem não alcança os dois) e usa estas
funções pra decidir: qual gravação do MusicBrainz é a música da lista e qual
vídeo é o upload oficial. Separadas aqui pra terem teste.
"""

from __future__ import annotations

import re

from freddy.nucleo.texto import normalizar

# Vídeo com isto no título quase nunca é o oficial da música.
_NAO_OFICIAL = re.compile(
    r"\b(cover|karaoke|karaokê|playback|lyrics?|letra|legendad[oa]|tradu[cç][aã]o|"
    r"remix|sped up|slowed|nightcore|8d|instrumental|reaction|react|aula|tutorial|"
    r"how to play|piano version|guitar lesson|1 hour|10 hours)\b",
    re.IGNORECASE,
)
_AO_VIVO = re.compile(r"\b(ao vivo|live|acustico|acústico|unplugged|mtv)\b", re.IGNORECASE)


def _simples(texto: str) -> str:
    """Só letras e números, sem acento: 'Zé Neto & Cristiano' -> 'zenetocristiano'."""
    return re.sub(r"[^a-z0-9]", "", normalizar(texto))


def _artistas(artista: str) -> list[str]:
    """'Zé Neto & Cristiano' é um artista; 'Elis Regina & Tom Jobim' são dois: guarda os três jeitos."""
    partes = [artista] + re.split(r"\s+(?:&|e|and|x|feat\.?|part\.?)\s+", artista)
    return [p for p in {_simples(p) for p in partes} if len(p) >= 3]


def _titulo_bate(titulo_lista: str, titulo_achado: str) -> bool:
    base = _simples(re.sub(r"\(.*?\)", "", titulo_lista)) or _simples(titulo_lista)
    return base in _simples(titulo_achado)


def escolher_video(artista: str, titulo: str, videos: list[dict], ao_vivo: bool = False) -> tuple[dict | None, str]:
    """Escolhe o upload oficial entre os resultados de busca do YouTube.

    videos: dicionários do yt-dlp (title, channel/uploader, id, duration).
    Devolve (vídeo, motivo). Ordem de preferência: canal "<artista> - Topic"
    (o áudio oficial que as gravadoras sobem), canal VEVO do artista, canal do
    próprio artista com "oficial/official" no título, canal do artista. Sem
    nenhum desses, (None, motivo): melhor deixar sem link que pôr um pirata.
    """
    artistas = _artistas(artista)
    candidatos = []
    for v in videos:
        nome = v.get("title") or ""
        canal = v.get("channel") or v.get("uploader") or ""
        if not _titulo_bate(titulo, nome):
            continue
        if _NAO_OFICIAL.search(nome) and not _NAO_OFICIAL.search(titulo):
            continue
        if not ao_vivo and _AO_VIVO.search(nome) and not _AO_VIVO.search(titulo):
            continue
        canal_s = _simples(canal)
        do_artista = any(a in canal_s for a in artistas)
        if canal.endswith(" - Topic") and do_artista:
            candidatos.append((0, "canal Topic (áudio oficial)", v))
        elif "vevo" in canal_s and do_artista:
            candidatos.append((1, "canal VEVO", v))
        elif do_artista and re.search(r"\b(oficial|official)\b", nome, re.IGNORECASE):
            candidatos.append((2, "canal do artista, vídeo oficial", v))
        elif do_artista:
            candidatos.append((3, "canal do artista", v))
    if not candidatos:
        return None, "nenhum upload oficial nos resultados"
    candidatos.sort(key=lambda c: c[0])
    return candidatos[0][2], candidatos[0][1]


def escolher_gravacao(artista: str, titulo: str, gravacoes: list[dict]) -> tuple[dict | None, str]:
    """Escolhe a gravação do MusicBrainz (resultado de /ws/2/recording?query=...).

    Fica com as de nota >= 85 cujo título e artista batem e, entre elas, a de
    lançamento mais antigo (o ano da música é o do primeiro lançamento, não
    o da coletânea). Devolve (gravação, motivo).
    """
    artistas = _artistas(artista)
    boas = []
    for g in gravacoes:
        if int(g.get("score", 0)) < 85 or not _titulo_bate(titulo, g.get("title", "")):
            continue
        creditos = _simples(" ".join(c.get("name", "") + c.get("artist", {}).get("name", "")
                                     for c in g.get("artist-credit", [])))
        if not any(a in creditos for a in artistas):
            continue
        data = g.get("first-release-date") or ""
        boas.append((data[:4] if re.match(r"\d{4}", data) else "9999", g))
    if not boas:
        return None, "não achei no MusicBrainz"
    boas.sort(key=lambda b: b[0])
    return boas[0][1], f"{len(boas)} gravações batem, a mais antiga"


# ---------- a lista de um bloco (o que o Claude gera) ----------

COLUNAS = ["artista", "titulo", "ano", "genero", "genero2", "feat", "idioma", "tem_voz", "energia",
           "animacao", "climas", "ocasioes", "temas", "instrumentos", "popularidade", "essencial",
           "canta_junto", "explicita", "ao_vivo", "nota"]
IDIOMAS = {"pt", "en", "es", "it", "fr", "de", "ja", "ko", "la", "outro", ""}


def chave_musica(artista: str, titulo: str) -> str:
    """Pra achar repetida entre blocos: 'Chitãozinho & Xororó' + 'Evidências' -> 'chitaozinhoxororo|evidencias'."""
    return _simples(artista) + "|" + _simples(re.sub(r"\(.*?\)", "", titulo) or titulo)


def conferir_lista(linhas: list[dict], generos: set[str], tags: dict[str, str]) -> list[str]:
    """Erros de uma lista de bloco (vazio = boa). tags: id -> gaveta."""
    erros = []

    def gaveta(lista: str, nome: str, onde: str, minimo: int = 0) -> None:
        ids = [x for x in lista.split("|") if x]
        if len(ids) < minimo:
            erros.append(f"{onde}: precisa de pelo menos {minimo} em {nome}")
        for x in ids:
            if tags.get(x) != nome:
                erros.append(f"{onde}: {nome} {x!r} não existe")

    vistas: set[str] = set()
    for i, l in enumerate(linhas, 2):
        onde = f"linha {i} ({l.get('artista')} - {l.get('titulo')})"
        if set(l) != set(COLUNAS) or None in l.values():
            erros.append(f"{onde}: colunas erradas (tem ';' sobrando ou faltando?)")
            continue
        if not l["artista"].strip() or not l["titulo"].strip():
            erros.append(f"{onde}: sem artista ou título")
        k = chave_musica(l["artista"], l["titulo"])
        if k in vistas:
            erros.append(f"{onde}: repetida")
        vistas.add(k)
        if not re.fullmatch(r"\d{4}", l["ano"]) or not 1600 <= int(l["ano"]) <= 2026:
            erros.append(f"{onde}: ano {l['ano']!r}")
        for col in ("genero", "genero2"):
            if (l[col] or col == "genero") and l[col] not in generos:
                erros.append(f"{onde}: {col} {l[col]!r} não existe")
        if l["idioma"] not in IDIOMAS:
            erros.append(f"{onde}: idioma {l['idioma']!r}")
        for col, lo, hi in (("energia", 1, 5), ("animacao", 1, 5), ("popularidade", 0, 100)):
            if not re.fullmatch(r"\d{1,3}", l[col]) or not lo <= int(l[col]) <= hi:
                erros.append(f"{onde}: {col} {l[col]!r} (de {lo} a {hi})")
        for col in ("tem_voz", "essencial", "canta_junto", "explicita", "ao_vivo"):
            if l[col] not in ("0", "1"):
                erros.append(f"{onde}: {col} tem que ser 0 ou 1")
        gaveta(l["climas"], "clima", onde, 2)
        gaveta(l["ocasioes"], "ocasiao", onde)
        gaveta(l["temas"], "tema", onde)
        gaveta(l["instrumentos"], "instrumento", onde)
    return erros


# Meta de cada bloco e o tema (docs/etapas/banco-fredify-etapa3.md).
METAS = {
    "bloco-01": (562, "essenciais de tudo (converter o formato antigo, manter as músicas)"),
    "bloco-02": (400, "MPB, bossa, tropicália, nova MPB, choro, soul BR"),
    "bloco-03": (400, "samba e pagode"),
    "bloco-04": (450, "sertanejo (caipira → agronejo, muito 2020–2025)"),
    "bloco-05": (450, "forró, piseiro, axé, brega, arrocha, regionais, marchinhas, São João"),
    "bloco-06": (450, "rock nacional, metal BR, reggae nacional, pop e teen BR"),
    "bloco-07": (500, "funk e rap/trap BR (300), gospel (130), infantil BR (70)"),
    "bloco-08": (500, "pop internacional, latina, k-pop, anime"),
    "bloco-09": (450, "rock internacional"),
    "bloco-10": (450, "soul, disco, R&B, jazz, reggae, hip hop internacional"),
    "bloco-11": (400, "eletrônica, baladas, trilhas, clássica, mundo, Natal"),
}


def _status() -> int:
    """python -m freddy.catalogo.bloco status: o que falta em cada bloco (pra dividir entre agentes)."""
    import csv
    from datetime import datetime
    from pathlib import Path

    from freddy.catalogo.compilar import PASTA_CATALOGO, carregar

    d = carregar(PASTA_CATALOGO)
    generos = {g["id"] for g in d["generos"]}
    tags = {t["id"]: t["gaveta"] for t in d["tags"]}
    pasta = PASTA_CATALOGO / "blocos"
    total, pronto = 0, 0
    print(f"{'bloco':9} {'tem':>4} {'meta':>4} {'erros':>5}  situação")
    for bloco, (meta, tema) in METAS.items():
        arq = pasta / f"{bloco}.csv"
        vez = pasta / "vez" / f"{bloco}.txt"
        linhas, erros, situacao = [], 0, ""
        if arq.exists():
            with open(arq, encoding="utf-8") as f:
                linhas = list(csv.DictReader(f, delimiter=";"))
            if linhas and set(linhas[0]) != set(COLUNAS):
                situacao = "FORMATO ANTIGO (converter)"
            else:
                erros = len(conferir_lista(linhas, generos, tags))
        if not situacao:
            if len(linhas) >= meta and not erros:
                situacao, pronto = "PRONTO", pronto + 1
            else:
                situacao = f"falta {max(0, meta - len(linhas))}" + (" e corrigir erros" if erros else "")
        if vez.exists():
            idade = (datetime.now().timestamp() - vez.stat().st_mtime) / 3600
            situacao += f"  [vez: {vez.read_text(encoding='utf-8').strip()[:40]}, há {idade:.0f} h]"
        total += len(linhas) if not situacao.startswith("FORMATO") else 0
        print(f"{bloco:9} {len(linhas):>4} {meta:>4} {erros:>5}  {situacao}  — {tema}")
    print(f"\n{pronto}/{len(METAS)} blocos prontos; {total} músicas no formato novo "
          f"(meta {sum(m for m, _ in METAS.values())}).")
    return 0


def _main() -> int:
    """python -m freddy.catalogo.bloco conferir <lista.csv> [outras listas.csv ...]"""
    import csv
    import sys
    from pathlib import Path

    from freddy.catalogo.compilar import PASTA_CATALOGO, carregar

    d = carregar(PASTA_CATALOGO)
    generos = {g["id"] for g in d["generos"]}
    tags = {t["id"]: t["gaveta"] for t in d["tags"]}
    arquivos = [Path(a) for a in sys.argv[2:]]
    todas: dict[str, str] = {}
    total_erros = 0
    for arq in arquivos:
        with open(arq, encoding="utf-8") as f:
            linhas = list(csv.DictReader(f, delimiter=";"))
        erros = conferir_lista(linhas, generos, tags)
        for l in linhas:  # repetida entre listas diferentes
            k = chave_musica(l.get("artista") or "", l.get("titulo") or "")
            if k in todas and todas[k] != arq.name:
                erros.append(f"{l['artista']} - {l['titulo']}: já está em {todas[k]}")
            todas.setdefault(k, arq.name)
        for e in erros[:80]:
            print(f"{arq.name}: {e}")
        print(f"{arq.name}: {len(linhas)} músicas, {len(erros)} erros")
        total_erros += len(erros)
    return 1 if total_erros else 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3 and sys.argv[1] == "conferir":
        sys.exit(_main())
    if len(sys.argv) == 2 and sys.argv[1] == "status":
        sys.exit(_status())
    print(_main.__doc__)
    print(_status.__doc__)
