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
