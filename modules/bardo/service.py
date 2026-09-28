"""Módulo Bardo — camada de serviço.

Reconhece "toca <link do YouTube>" ou "toca <busca por tema/origem>" em
linguagem natural, resolve link em stream tocável, e mantém a fila de
reprodução por servidor. Segue o mesmo padrão do NAT-CORE: lógica pura
aqui, sem nenhuma dependência de discord.py, pra qualquer outro módulo
(inclusive um futuro módulo de LLM) poder chamar direto.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import deque
from pathlib import Path

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


def extrair_texto_de_busca(texto: str) -> str:
    """Remove o gatilho ('toca'/'play'/etc) do texto, sobrando o resto —
    o que, se não for um link, é tratado como busca por tag/origem.

    O cog.py é responsável por remover a menção ao bot antes de chamar
    isso (menção é formato específico de Discord, não é problema do
    reconhecimento de gatilho).
    """
    return _GATILHO_RE.sub("", texto, count=1).strip()


# ---------------------------------------------------------------------------
# Dataset e busca booleana em linguagem natural
#
# Query como "triste e bloodborne" ou "boss fight e elden ring ou hollow
# knight" ou "calmo e fire emblem sem batalha" (sem = exclui o termo).
# "e" combina (AND), "ou" separa grupos alternativos (OR), "sem"/"não" na
# frente de um termo nega ele. Cada termo é comparado (substring, sem
# acento) contra nome da faixa + nome/tipo da origem + temas da faixa.
# ---------------------------------------------------------------------------

_DATASET_PATH = Path(__file__).parent / "dataset" / "musicas.json"

_FILLER_WORDS = {
    "musica", "música", "som", "sons", "faixa", "algo", "alguma", "algum",
    "uma", "um", "de", "do", "da", "dos", "das", "a", "o",
}

_dataset_cache: list[dict] | None = None


def carregar_dataset(caminho: Path | None = None) -> list[dict]:
    """Carrega (com cache em memória) o dataset de músicas taggeadas."""
    global _dataset_cache
    if caminho is not None:
        # Uso principalmente em teste: não usa o cache global.
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)["musicas"]
    if _dataset_cache is None:
        with open(_DATASET_PATH, encoding="utf-8") as f:
            _dataset_cache = json.load(f)["musicas"]
    return _dataset_cache


def _normalizar(texto: str) -> str:
    """minúsculas, sem acento — pra 'É Pico' bater com 'epico'."""
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _texto_buscavel(musica: dict) -> str:
    partes = [musica["nome"], musica["origem"]["nome"], musica["origem"]["tipo"], *musica["temas"]]
    return _normalizar(" ".join(partes))


def _parse_query(texto: str) -> list[list[tuple[bool, str]]]:
    """'triste e bloodborne ou calmo sem triste' ->
    [[(F,'triste'),(F,'bloodborne')], [(F,'calmo'),(T,'triste')]]

    Formato: lista de grupos OR; cada grupo é uma lista de termos AND,
    cada termo é (negado: bool, termo: str). 'e' separa termo normal,
    'sem'/'nao' separa termo negado — ambos funcionam como ponto de corte
    dentro do grupo (não precisam vir logo no início dele).
    """
    texto = _normalizar(texto)
    grupos = []
    for bruto_ou in re.split(r"\bou\b", texto):
        # captura o separador junto: ['termo0', 'e'|'sem'|'nao', 'termo1', ...]
        pedacos = re.split(r"\b(e|sem|nao)\b", bruto_ou)
        termos = []
        negado_atual = False
        for pedaco in pedacos:
            pedaco = pedaco.strip()
            if pedaco in ("e", "sem", "nao"):
                negado_atual = pedaco in ("sem", "nao")
                continue
            palavras = [p for p in pedaco.split() if p not in _FILLER_WORDS]
            termo_limpo = " ".join(palavras).strip()
            if termo_limpo:
                termos.append((negado_atual, termo_limpo))
            negado_atual = False
        if termos:
            grupos.append(termos)
    return grupos


def _termo_bate(alvo: str, negado: bool, termo: str) -> bool:
    contido = termo in alvo
    return (not contido) if negado else contido


def _musica_bate(alvo: str, grupos_ou: list[list[tuple[bool, str]]]) -> bool:
    return any(
        all(_termo_bate(alvo, negado, termo) for negado, termo in grupo_and)
        for grupo_and in grupos_ou
    )


def buscar_por_tags(texto_busca: str, dataset: list[dict] | None = None) -> list[dict]:
    """Busca booleana em linguagem natural no dataset de músicas.

    Retorna a lista de entradas do dataset que batem com a query. Lista
    vazia significa "nada encontrado" (não confundir com query vazia,
    que também retorna lista vazia — o cog.py trata os dois casos com
    mensagens diferentes pro usuário).
    """
    grupos = _parse_query(texto_busca)
    if not grupos:
        return []
    musicas = dataset if dataset is not None else carregar_dataset()
    return [m for m in musicas if _musica_bate(_texto_buscavel(m), grupos)]


# ---------------------------------------------------------------------------
# Fila de reprodução, uma por servidor (guild_id -> deque de entradas do
# dataset ou de músicas avulsas resolvidas por link direto).
# ---------------------------------------------------------------------------

_filas: dict[int, deque] = {}


def _fila_do_servidor(guild_id: int) -> deque:
    if guild_id not in _filas:
        _filas[guild_id] = deque()
    return _filas[guild_id]


def adicionar_na_fila(guild_id: int, musica: dict) -> None:
    _fila_do_servidor(guild_id).append(musica)


def adicionar_varias_na_fila(guild_id: int, musicas: list[dict]) -> None:
    fila = _fila_do_servidor(guild_id)
    fila.extend(musicas)


def proxima_da_fila(guild_id: int) -> dict | None:
    fila = _fila_do_servidor(guild_id)
    return fila.popleft() if fila else None


def ver_fila(guild_id: int) -> list[dict]:
    return list(_fila_do_servidor(guild_id))


def limpar_fila(guild_id: int) -> None:
    _fila_do_servidor(guild_id).clear()
