"""Módulo Bardo — camada de serviço.

Reconhece pedidos de música em linguagem natural ("natty toca <link>",
"natty pausa", "natty volume 30") e resolve links do YouTube num stream de
áudio tocável. Segue o mesmo padrão do NAT-CORE: lógica pura aqui, sem
nenhuma dependência de discord.py, pra qualquer outro módulo (inclusive um
futuro módulo de LLM) poder chamar direto.

A busca por tags, dataset local e playlist dinâmica ficam para depois.
"""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass

from modules.bardo import youtube

# "natty ...", "ei natty, ...", "@Natty ..." escrito como texto. A menção de
# verdade (<@id>) quem reconhece é o cog, que sabe o id do bot.
_CHAMOU_NATTY_RE = re.compile(r"^\W*(?:(?:ei|oi|ô|o)\s+)?natty\b", re.IGNORECASE)

_YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.|music\.)?(youtube\.com/watch\?v=[\w-]+|youtu\.be/[\w-]+)(\S*)?",
    re.IGNORECASE,
)

_TOCAR_RE = re.compile(
    r"\b(toca|toque|tocar|bota|coloca|põe|poe|play|adiciona|adicione|add)\b", re.IGNORECASE
)
_PULAR_RE = re.compile(r"\b(pula|pule|pular|pr[oó]xima|skip|next)\b", re.IGNORECASE)
_FILA_RE = re.compile(r"\b(fila|playlist|queue)\b", re.IGNORECASE)
_LIMPAR_RE = re.compile(r"\b(limpa|limpe|limpar|esvazia|esvazie|apaga|zera|clear)\b", re.IGNORECASE)
_PAUSAR_RE = re.compile(r"\b(pausa|pause|pausar)\b", re.IGNORECASE)
_CONTINUAR_RE = re.compile(
    r"\b(continua|continue|continuar|despausa|retoma|volta|resume)\b", re.IGNORECASE
)
_PARAR_RE = re.compile(r"\b(para|pare|parar|stop|chega|desliga|sai|sair)\b", re.IGNORECASE)
_VOLUME_RE = re.compile(r"\bvolume\b", re.IGNORECASE)
_AUMENTAR_RE = re.compile(r"\b(aumenta|sobe|mais alto)\b", re.IGNORECASE)
_DIMINUIR_RE = re.compile(r"\b(abaixa|baixa|diminui|mais baixo)\b", re.IGNORECASE)
_NUMERO_RE = re.compile(r"\b(\d{1,3})\s*%?")

VOLUME_PADRAO = 50  # %; o áudio do YouTube a 100% fica alto demais no Discord
PASSO_VOLUME = 20  # %; quanto "aumenta"/"abaixa" o volume mexe
MAX_FILA = 50  # músicas esperando, sem contar a que está tocando

# Flags de reconexão recomendadas pelo próprio discord.py para streaming via
# FFmpeg: sem elas, uma soluço de rede na fonte derruba o playback de vez.
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


@dataclass(frozen=True)
class Pedido:
    """O que pediram pra Natty fazer com a música.

    acao: "tocar", "pausar", "continuar", "parar", "volume", "pular", "fila"
        ou "limpar_fila".
    link: só em "tocar"; None se pediram pra tocar sem mandar link.
    volume: só em "volume"; valor absoluto (0-100) pedido.
    delta_volume: só em "volume"; +/-PASSO_VOLUME para "aumenta"/"abaixa".
    Em "volume" sem número nem direção, os dois ficam None (é pergunta).
    """

    acao: str
    link: str | None = None
    volume: int | None = None
    delta_volume: int | None = None


def chamou_a_natty(texto: str) -> bool:
    """True se o texto começa chamando a Natty pelo nome ("natty ...")."""
    return bool(_CHAMOU_NATTY_RE.search(texto))


def interpretar_pedido(texto: str) -> Pedido | None:
    """Traduz um pedido em linguagem natural num Pedido, ou None se não for de música.

    Não verifica se o texto é dirigido à Natty — isso é com quem chama
    (menção ou chamou_a_natty).
    """
    link = extrair_link_youtube(texto)
    # O link sai antes das outras regras: "para" ou "volta" dentro de uma
    # URL não pode virar comando.
    sem_link = _YOUTUBE_URL_RE.sub(" ", texto)

    if link and _TOCAR_RE.search(sem_link):
        return Pedido("tocar", link=link)
    # Fila antes de parar/tocar: "natty limpa a fila" não é "para", e
    # "natty toca a próxima" é pular, não pedido sem link.
    if _FILA_RE.search(sem_link) and _LIMPAR_RE.search(sem_link):
        return Pedido("limpar_fila")
    if _PULAR_RE.search(sem_link):
        return Pedido("pular")
    if _FILA_RE.search(sem_link):
        return Pedido("fila")
    if _VOLUME_RE.search(sem_link) or _AUMENTAR_RE.search(sem_link) or _DIMINUIR_RE.search(sem_link):
        return _pedido_de_volume(sem_link)
    if _PAUSAR_RE.search(sem_link):
        return Pedido("pausar")
    if _CONTINUAR_RE.search(sem_link):
        return Pedido("continuar")
    # Depois de pausar/continuar: "natty para de pausar" é esquisito, mas
    # "natty para de tocar" tem que parar, não pedir link. Quem vem primeiro
    # decide: em "natty toca uma música para relaxar" o "para" é preposição.
    parar = _PARAR_RE.search(sem_link)
    tocar = _TOCAR_RE.search(sem_link)
    if parar and not (tocar and tocar.start() < parar.start()):
        return Pedido("parar")
    if tocar:
        return Pedido("tocar", link=None)
    return None


def _pedido_de_volume(texto: str) -> Pedido:
    numero = _NUMERO_RE.search(texto)
    if numero:
        return Pedido("volume", volume=limitar_volume(int(numero.group(1))))
    if _AUMENTAR_RE.search(texto):
        return Pedido("volume", delta_volume=PASSO_VOLUME)
    if _DIMINUIR_RE.search(texto):
        return Pedido("volume", delta_volume=-PASSO_VOLUME)
    return Pedido("volume")


def limitar_volume(volume: int) -> int:
    return max(0, min(100, volume))


def novo_volume(atual: int, pedido: Pedido) -> int:
    """Volume (0-100) depois de aplicar um Pedido de volume sobre `atual`."""
    if pedido.volume is not None:
        return pedido.volume
    if pedido.delta_volume is not None:
        return limitar_volume(atual + pedido.delta_volume)
    return atual


@dataclass(frozen=True)
class Musica:
    titulo: str
    # O link, não a URL do stream: a URL de áudio do YouTube expira, então
    # quem toca resolve de novo na hora.
    link: str
    duracao_segundos: int | None = None


class FilaCheia(Exception):
    pass


class Fila:
    """A música tocando e as que esperam a vez, de um servidor.

    Só guarda estado; quem toca de verdade (cog.py) chama avancar() quando
    uma música acaba.
    """

    def __init__(self):
        self.tocando: Musica | None = None
        self._proximas: deque[Musica] = deque()

    @property
    def proximas(self) -> tuple[Musica, ...]:
        return tuple(self._proximas)

    def adicionar(self, musica: Musica) -> int:
        """Põe no fim da fila e devolve a posição (1 = a próxima a tocar)."""
        if len(self._proximas) >= MAX_FILA:
            raise FilaCheia(f"A fila já tem {MAX_FILA} músicas.")
        self._proximas.append(musica)
        return len(self._proximas)

    def avancar(self) -> Musica | None:
        """Passa pra próxima música (que vira a `tocando`) e a devolve; None se acabou."""
        self.tocando = self._proximas.popleft() if self._proximas else None
        return self.tocando

    def limpar(self) -> int:
        """Tira as músicas que esperam (a atual continua). Devolve quantas saíram."""
        quantas = len(self._proximas)
        self._proximas.clear()
        return quantas

    def resetar(self) -> None:
        """Esvazia tudo, inclusive a atual."""
        self.limpar()
        self.tocando = None


def extrair_link_youtube(texto: str) -> str | None:
    """Extrai a primeira URL de YouTube encontrada no texto, ou None."""
    m = _YOUTUBE_URL_RE.search(texto)
    return m.group(0) if m else None


def resolver_musica(url: str) -> dict:
    """Resolve um link de YouTube em algo tocável.

    Retorna {"titulo": str, "stream_url": str, "duracao_segundos": int|None}.
    """
    return youtube.resolver_stream(url)
