"""Do link do YouTube ao que o FFmpeg toca, e os erros em português."""

from __future__ import annotations

from dataclasses import dataclass

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
    from modules.bardo import youtube

    info = youtube.resolver_stream(link, FORMATO)
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
