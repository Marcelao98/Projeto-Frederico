"""O YouTube: do link (ou da busca) ao áudio que o FFmpeg toca, e os erros em português.

A única peça que fala com o YouTube (via yt-dlp).
"""

from __future__ import annotations

from dataclasses import dataclass

import yt_dlp

# Opus primeiro: é o formato nativo do YouTube e o ffmpeg-free do Fedora toca
# sem precisar do RPM Fusion. Se não tiver, qualquer áudio serve.
FORMATO = "bestaudio[acodec=opus]/bestaudio/best"


@dataclass(frozen=True)
class Fonte:
    titulo: str
    url: str  # a URL de áudio de verdade (expira em horas: resolve na hora de tocar)
    duracao: float
    http_headers: dict[str, str]


def resolver_youtube(link: str) -> Fonte:
    info = resolver_stream(link, FORMATO)
    return Fonte(info["titulo"], info["stream_url"], float(info.get("duracao_segundos") or 0), info.get("http_headers") or {})


_MOTIVOS = (
    ("private video", "o vídeo é privado"),
    ("sign in to confirm your age", "o vídeo tem restrição de idade"),
    ("age-restricted", "o vídeo tem restrição de idade"),
    ("not available in your country", "o vídeo não está disponível no Brasil"),
    ("video unavailable", "o vídeo não existe mais (ou foi removido)"),
    ("this video has been removed", "o vídeo foi removido"),
    ("sign in to confirm you", "o YouTube pediu login (bloqueou o acesso por enquanto)"),
    ("http error 403", "o YouTube recusou o áudio"),
    ("unable to download webpage", "sem internet, ou o YouTube não respondeu"),
    ("name or service not known", "sem internet"),
)


def motivo_em_portugues(erro: BaseException | str) -> str:
    texto = str(erro).lower()
    for trecho, motivo in _MOTIVOS:
        if trecho in texto:
            return motivo
    return "não consegui abrir o vídeo"


_YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "skip_download": True,
}


def resolver_stream(url: str, formato: str | None = None) -> dict:
    """Resolve uma URL do YouTube na URL de áudio direto + metadados.

    Levanta a exceção do yt-dlp se o vídeo não existir, estiver bloqueado,
    etc. — quem chama decide como tratar. `formato` troca o "format" do
    yt-dlp (o Freddy prefere Opus, que o ffmpeg-free do Fedora toca).
    """
    info = _extrair(url, formato)
    return {
        "titulo": info.get("title") or "música desconhecida",
        "stream_url": info["url"],
        "duracao_segundos": info.get("duration"),
        # O FFmpeg precisa mandar os mesmos headers pra URL de áudio.
        "http_headers": info.get("http_headers") or {},
    }


def buscar_stream(texto: str, formato: str | None = None) -> dict:
    """Busca `texto` no YouTube e resolve o primeiro resultado.

    Mesmo retorno de resolver_stream(), mais "link": o link de watch do
    vídeo, que (ao contrário da stream_url) não expira. Levanta LookupError
    se a busca não trouxer nada.
    """
    # "ytsearch1:" é a pseudo-URL de busca do yt-dlp (primeiro resultado).
    info = _extrair(f"ytsearch1:{texto}", formato)
    return {
        "titulo": info.get("title") or "música desconhecida",
        "link": f"https://www.youtube.com/watch?v={info['id']}",
        "stream_url": info["url"],
        "duracao_segundos": info.get("duration"),
        "http_headers": info.get("http_headers") or {},
    }


def _extrair(url: str, formato: str | None = None) -> dict:
    opcoes = {**_YDL_OPTS, "format": formato} if formato else _YDL_OPTS
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        info = ydl.extract_info(url, download=False)
    if "entries" in info:  # playlist ou busca: pega o primeiro item
        entradas = [e for e in info["entries"] if e]
        if not entradas:
            raise LookupError(f"nada encontrado para {url!r}")
        info = entradas[0]
    return info


class YoutubeDados:
    """O que o painel e o chat perguntam ao YouTube (os testes trocam por um falso)."""

    def info(self, link: str) -> dict:
        f = resolver_youtube(link)
        return {"titulo": f.titulo, "link": link, "duracaoSegundos": f.duracao or None}

    def buscar(self, texto: str) -> dict:
        r = buscar_stream(texto, FORMATO)
        return {"titulo": r["titulo"], "link": r["link"], "duracaoSegundos": r.get("duracao_segundos")}
