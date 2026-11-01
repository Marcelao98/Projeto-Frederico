"""O som indo pra call: um discord.AudioSource que entrega a Mesa, quadro a quadro.

Ideia do Kenku FM (DiscordBroadcast.ts, © Owlbear Rodeo, GPL-3.0): um player
só, que nunca para. O Kenku usa `noSubscriber: Play` e tolera até 60 s de
buraco; aqui, o read() nunca devolve vazio (silêncio quando não toca nada),
então o discord.py segue "tocando" pra sempre e trocar de música não mexe no
Discord, só na Mesa.
"""

from __future__ import annotations

import discord

from freddy.audio.mesa import Mesa


class SaidaDiscord(discord.AudioSource):
    """O discord.py chama read() a cada 20 ms, da thread do player dele."""

    def __init__(self, mesa: Mesa):
        self.mesa = mesa

    def read(self) -> bytes:
        return self.mesa.ler_para_discord()  # 3840 bytes: 20 ms de 48 kHz estéreo 16 bits

    def is_opus(self) -> bool:
        return False  # o discord.py codifica em Opus

    def cleanup(self) -> None:
        self.mesa.sair_do_discord()
