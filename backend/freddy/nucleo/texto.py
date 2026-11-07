"""Texto: tirar acento, slug, links do YouTube."""

from __future__ import annotations

import re
import unicodedata

YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.|music\.)?(youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+)(\S*)?",
    re.IGNORECASE,
)


def normalizar(texto: str) -> str:
    """minúsculas, sem acento — pra 'É Pico' bater com 'epico'."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def extrair_link_youtube(texto: str) -> str | None:
    """Extrai a primeira URL de YouTube encontrada no texto, ou None."""
    m = YOUTUBE_URL_RE.search(texto)
    return m.group(0) if m else None


def slug(texto: str) -> str:
    """'Queen's Gardens' -> 'queens-gardens' (sem acento, só [a-z0-9-])."""
    texto = normalizar(texto)
    texto = re.sub(r"['’]", "", texto)
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


def video_id(link: str) -> str:
    """Id do vídeo de um link do YouTube (watch?v=, youtu.be/); o próprio texto se não achar."""
    m = re.search(r"(?:[?&]v=|youtu\.be/)([\w-]+)", link)
    return m.group(1) if m else link
