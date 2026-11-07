"""A fila: a música que toca e as que esperam. Só estado, sem tocar nada.

Porta fiel de frontend/src/motor/fila.ts: mesmas regras, mesmos nomes.
Imutável como lá: cada operação devolve uma Fila nova. As músicas são dicts
no formato do protocolo (os mesmos campos de `Musica` no tipos.ts:
titulo, link, faixaId, origem, duracaoSegundos), mais o `uid` na fila.
"""

from __future__ import annotations

import itertools
import random
import time
from dataclasses import dataclass, field, replace

MAX_FILA = 50  # músicas esperando, sem contar a que toca

_contador = itertools.count(1)


def _base36(n: int) -> str:
    digitos = "0123456789abcdefghijklmnopqrstuvwxyz"
    s = ""
    while True:
        n, r = divmod(n, 36)
        s = digitos[r] + s
        if n == 0:
            return s


def novo_uid() -> str:
    return f"{_base36(int(time.time() * 1000))}-{_base36(next(_contador))}"


def como_item(musica: dict) -> dict:
    return {**musica, "uid": novo_uid()}


@dataclass(frozen=True)
class Fila:
    tocando: dict | None = None
    proximas: tuple[dict, ...] = field(default_factory=tuple)
    repetir: bool = False


FILA_VAZIA = Fila()


@dataclass(frozen=True)
class Adicao:
    fila: Fila
    entraram: int
    posicao: int


def adicionar(fila: Fila, musicas: list[dict], onde: str = "fim") -> Adicao:
    """Põe as músicas que couberem (até MAX_FILA esperando).

    "fim" vai pro fim; "proxima" entra na frente da fila; "agora" toca a
    primeira já (a que tocava sai) e o resto vira as próximas.
    """
    itens = [como_item(m) for m in musicas]
    if not itens:
        return Adicao(fila, 0, -1)

    cabem = max(MAX_FILA - len(fila.proximas), 0)
    if onde == "agora":
        primeira, resto = itens[0], itens[1:]
        entram = tuple(resto[:cabem])
        return Adicao(Fila(primeira, entram + fila.proximas, False), 1 + len(entram), 0)

    entram = tuple(itens[:cabem])
    if not entram:
        return Adicao(fila, 0, -1)
    if onde == "proxima":
        return Adicao(replace(fila, proximas=entram + fila.proximas), len(entram), 1)
    return Adicao(replace(fila, proximas=fila.proximas + entram), len(entram), len(fila.proximas) + 1)


def avancar(fila: Fila) -> Fila:
    """A próxima vira a que toca (None se acabou)."""
    if not fila.proximas:
        return replace(fila, tocando=None)
    return replace(fila, tocando=fila.proximas[0], proximas=fila.proximas[1:])


def limpar(fila: Fila) -> Fila:
    """Tira as que esperam; a atual continua."""
    return replace(fila, proximas=())


def resetar() -> Fila:
    """Esvazia tudo, inclusive a atual, e desliga o repetir."""
    return FILA_VAZIA


def remover(fila: Fila, uid: str) -> Fila:
    return replace(fila, proximas=tuple(m for m in fila.proximas if m["uid"] != uid))


def mover(fila: Fila, uid: str, para: int) -> Fila:
    """Move a música `uid` pra posição `para` (0 = a próxima a tocar)."""
    proximas = list(fila.proximas)
    de = next((i for i, m in enumerate(proximas) if m["uid"] == uid), -1)
    if de < 0:
        return fila
    item = proximas.pop(de)
    proximas.insert(max(0, min(para, len(proximas))), item)
    return replace(fila, proximas=tuple(proximas))


def tocar_item(fila: Fila, uid: str) -> Fila:
    """Pula direto pra música `uid`: as que vinham antes dela continuam esperando."""
    item = next((m for m in fila.proximas if m["uid"] == uid), None)
    if item is None:
        return fila
    return Fila(item, tuple(m for m in fila.proximas if m["uid"] != uid), False)


def embaralhar(fila: Fila, aleatorio=random.random) -> Fila:
    proximas = list(fila.proximas)
    for i in range(len(proximas) - 1, 0, -1):
        j = int(aleatorio() * (i + 1))
        proximas[i], proximas[j] = proximas[j], proximas[i]
    return replace(fila, proximas=tuple(proximas))
