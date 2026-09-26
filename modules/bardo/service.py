"""Módulo Bardo — camada de serviço.

MVP: reconhecer "toca <link do YouTube>" em linguagem natural e resolver o
link num stream de áudio tocável. Segue o mesmo padrão do NAT-CORE: lógica
pura aqui, sem nenhuma dependência de discord.py, pra qualquer outro módulo
(inclusive um futuro módulo de LLM) poder chamar direto.

A busca por tags, dataset local e playlist dinâmica ficam para depois —
isso aqui é só "reconhecer o pedido e tocar o link".
"""

from __future__ import annotations

import re

from modules.bardo import youtube

_GATILHO_RE = re.compile(r"\b(toca|toque|tocar|bota|play)\b", re.IGNORECASE)

_YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.|music\.)?(youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+)(\S*)?",
    re.IGNORECASE,
)

# Flags de reconexão recomendadas pelo próprio discord.py para streaming via
# FFmpeg: sem elas, uma soluço de rede na fonte derruba o playback de vez.
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


def eh_pedido_de_musica(texto: str) -> bool:
    """True se o texto contém um gatilho tipo 'toca'/'play'."""
    return bool(_GATILHO_RE.search(texto))


def extrair_link_youtube(texto: str) -> str | None:
    """Extrai a primeira URL de YouTube encontrada no texto, ou None."""
    m = _YOUTUBE_URL_RE.search(texto)
    return m.group(0) if m else None


def resolver_musica(url: str) -> dict:
    """Resolve um link de YouTube em algo tocável.

    Retorna {"titulo": str, "stream_url": str, "duracao_segundos": int|None}.
    """
    return youtube.resolver_stream(url)
