"""O som indo pra call: um discord.AudioSource que entrega a Mesa, quadro a quadro.

Do jeito do Kenku FM (PlaybackManager.ts, © Owlbear Rodeo, GPL-3.0): cada
vez que o som começa o bot cria uma SaidaDiscord nova e dá play; quando
para, dá stop (bot.py, _atualizar_player). Enquanto toca, o read() sempre
devolve um quadro (silêncio se a música ainda está carregando).
"""

from __future__ import annotations

import time
from collections import deque

import discord

from freddy.audio.mesa import Mesa, pico


class SaidaDiscord(discord.AudioSource):
    """O discord.py chama read() a cada 20 ms, da thread do player dele."""

    def __init__(self, mesa: Mesa):
        self.mesa = mesa
        # O medidor (GET /discord → transmissao): prova que o som saiu pra call.
        self.quadros = 0
        self.quadros_com_som = 0
        self.ultimo = 0.0  # time.monotonic() do último read()
        self._recentes: deque[tuple[float, int]] = deque(maxlen=100)  # (quando, pico) dos últimos ~2 s

    def read(self) -> bytes:
        quadro = self.mesa.ler_para_discord()  # 3840 bytes: 20 ms de 48 kHz estéreo 16 bits
        agora = time.monotonic()
        p = pico(quadro)
        self.quadros += 1
        self.quadros_com_som += p > 0
        self.ultimo = agora
        self._recentes.append((agora, p))
        return quadro

    def medidor(self) -> dict:
        agora = time.monotonic()
        ultimo_segundo = [p for t, p in self._recentes if agora - t <= 1.0]
        return {
            "quadros": self.quadros,
            "quadrosComSom": self.quadros_com_som,
            # O Discord pede 50 por segundo; bem menos que isso = player travado.
            "quadrosPorSegundo": len(ultimo_segundo),
            "comSomPorSegundo": sum(p > 0 for p in ultimo_segundo),
            "nivel": max((p for t, p in self._recentes if agora - t <= 0.5), default=0),
            "segundosDesdeUltimo": round(agora - self.ultimo, 2) if self.ultimo else None,
        }

    def is_opus(self) -> bool:
        return False  # o discord.py codifica em Opus

    def cleanup(self) -> None:
        # O bot para o player quando a música para (como o Kenku) e toca de
        # novo depois: quem tira a Mesa do Discord é o sair() do bot.
        pass
