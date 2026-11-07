"""Entender pedidos de música em português: "toca triste e bloodborne",
"pula", "volume 30", "para de repetir".

Porta fiel em TypeScript: frontend/src/navegador/pedido.ts (mudou uma regra
aqui, muda lá, e os testes dos dois lados).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from freddy.nucleo.texto import YOUTUBE_URL_RE, extrair_link_youtube

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
_REPETIR_RE = re.compile(r"\b(repete|repetir|repita|loop)\b", re.IGNORECASE)
# "para de repetir", "repete não", "chega de loop", "desliga o repetir".
_DESLIGAR_REPETIR_RE = re.compile(r"\b(n[ãa]o|para|pare|parar|chega|desliga|tira)\b", re.IGNORECASE)
_VOLUME_RE = re.compile(r"\bvolume\b", re.IGNORECASE)
_AUMENTAR_RE = re.compile(r"\b(aumenta|sobe|mais alto)\b", re.IGNORECASE)
_DIMINUIR_RE = re.compile(r"\b(abaixa|baixa|diminui|mais baixo)\b", re.IGNORECASE)
_NUMERO_RE = re.compile(r"\b(\d{1,3})\s*%?")

VOLUME_PADRAO = 50  # %; o áudio do YouTube a 100% fica alto demais no Discord
PASSO_VOLUME = 20  # %; quanto "aumenta"/"abaixa" o volume mexe


@dataclass(frozen=True)
class Pedido:
    """O que pediram pro Freddy fazer com a música.

    acao: "tocar", "pausar", "continuar", "parar", "volume", "pular", "fila",
        "limpar_fila" ou "repetir".
    link: só em "tocar"; None se pediram pra tocar sem mandar link.
    busca: só em "tocar" sem link; o que vem depois do verbo ("triste e
        bloodborne"), pra buscar_musicas(). None se não sobrou nada.
    volume: só em "volume"; valor absoluto (0-100) pedido.
    delta_volume: só em "volume"; +/-PASSO_VOLUME para "aumenta"/"abaixa".
    Em "volume" sem número nem direção, os dois ficam None (é pergunta).
    repetir: só em "repetir"; False = desligar ("para de repetir", "repete
        não"), None = alternar ("repete" liga, de novo desliga).
    """

    acao: str
    link: str | None = None
    busca: str | None = None
    volume: int | None = None
    delta_volume: int | None = None
    repetir: bool | None = None


def interpretar_pedido(texto: str) -> Pedido | None:
    """Traduz um pedido em linguagem natural num Pedido, ou None se não for de música.

    Não verifica se o texto é dirigido ao bot: isso é com quem chama (o bot
    do Freddy exige menção de verdade, @Freddy ou o cargo dele).
    """
    link = extrair_link_youtube(texto)
    # O link sai antes das outras regras: "para" ou "volta" dentro de uma
    # URL não pode virar comando.
    sem_link = YOUTUBE_URL_RE.sub(" ", texto)

    if link and _TOCAR_RE.search(sem_link):
        return Pedido("tocar", link=link)
    # Fila antes de parar/tocar: "limpa a fila" não é "para", e
    # "toca a próxima" é pular, não pedido sem link.
    if _FILA_RE.search(sem_link) and _LIMPAR_RE.search(sem_link):
        return Pedido("limpar_fila")
    # Repetir antes de parar: "para de repetir" desliga o loop, não para
    # a música. Mas se "toca" vem antes, é busca ("toca Repete Comigo").
    repetir = _REPETIR_RE.search(sem_link)
    tocar_antes = _TOCAR_RE.search(sem_link)
    if repetir and not (tocar_antes and tocar_antes.start() < repetir.start()):
        desligar = _DESLIGAR_REPETIR_RE.search(sem_link)
        return Pedido("repetir", repetir=False if desligar else None)
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
    # Depois de pausar/continuar: "para de pausar" é esquisito, mas
    # "para de tocar" tem que parar, não pedir link. Quem vem primeiro
    # decide: em "toca uma música para relaxar" o "para" é preposição.
    parar = _PARAR_RE.search(sem_link)
    tocar = _TOCAR_RE.search(sem_link)
    if parar and _para_de_outra_coisa(sem_link[parar.end():]):
        # "para de transcrever" é pedido pra outro bot: "para de X" só para
        # a música se X for tocar/cantar/música.
        return None
    if parar and not (tocar and tocar.start() < parar.start()):
        return Pedido("parar")
    if tocar:
        # A menção (<@id>) e o nome do Freddy vêm antes do verbo, então o que
        # sobra depois dele é só a busca.
        busca = sem_link[tocar.end():].strip(" \t\n,.!?:;")
        return Pedido("tocar", busca=busca or None)
    return None


_PARA_DE_RE = re.compile(r"^\s+de\s+(\w+)", re.IGNORECASE)
_O_QUE_PARA_A_MUSICA = {"tocar", "tocando", "cantar", "cantando", "música", "musica", "som", "barulho"}


def _para_de_outra_coisa(depois_do_para: str) -> bool:
    """True em "para de X" quando X não é música: "para de transcrever", "para de pausar"."""
    m = _PARA_DE_RE.match(depois_do_para)
    return bool(m) and m.group(1).lower() not in _O_QUE_PARA_A_MUSICA


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
