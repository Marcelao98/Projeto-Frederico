"""Acesso cru ao YouTube via yt-dlp.

Espelha o papel de `modules/core/sheets.py`: é a única peça do Bardo que
fala com um sistema externo (aqui, extrai a URL de áudio direto de um vídeo
do YouTube). Nenhuma lógica de negócio mora aqui, só a chamada crua.
"""

from __future__ import annotations

import yt_dlp

_YDL_OPTS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "skip_download": True,
}


def resolver_stream(url: str) -> dict:
    """Resolve uma URL do YouTube na URL de áudio direto + metadados.

    Levanta a exceção do yt-dlp se o vídeo não existir, estiver bloqueado,
    etc. — quem chama decide como tratar.
    """
    with yt_dlp.YoutubeDL(_YDL_OPTS) as ydl:
        info = ydl.extract_info(url, download=False)
        if "entries" in info:  # o link era de uma playlist; pega o primeiro item
            info = info["entries"][0]

        return {
            "titulo": info.get("title") or "música desconhecida",
            "stream_url": info["url"],
            "duracao_segundos": info.get("duration"),
        }
