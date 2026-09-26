"""Módulo Bardo — interface Discord.

Só traduz mensagem em linguagem natural → chamada de service.py, e cuida da
parte que é inerentemente Discord (conectar em canal de voz, tocar o
áudio). Nenhuma lógica de reconhecimento de link mora aqui.

Sem slash command de propósito: o pedido é "@Natty toca <link>", do mesmo
jeito que o módulo Dice reconhece "1d20 com vantagem" em vez de exigir um
comando formal.
"""

from __future__ import annotations

import asyncio

import discord
from discord.ext import commands

from modules.bardo import service


class BardoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if self.bot.user not in message.mentions:
            return
        if not service.eh_pedido_de_musica(message.content):
            return

        link = service.extrair_link_youtube(message.content)
        if not link:
            await message.reply("Me manda o link do YouTube da música junto do pedido.")
            return

        voice_state = message.author.voice
        if not voice_state or not voice_state.channel:
            await message.reply("Entra num canal de voz primeiro, aí eu toco.")
            return

        canal = voice_state.channel

        try:
            info = await asyncio.to_thread(service.resolver_musica, link)
        except Exception:
            await message.reply("Não consegui pegar essa música. Confere o link?")
            raise

        voice_client = message.guild.voice_client
        if voice_client is None:
            voice_client = await canal.connect()
        elif voice_client.channel != canal:
            await voice_client.move_to(canal)

        if voice_client.is_playing():
            voice_client.stop()

        fonte = discord.FFmpegPCMAudio(info["stream_url"], **service.FFMPEG_OPTIONS)
        voice_client.play(fonte)

        await message.reply(f"Tocando **{info['titulo']}** 🎵")


async def setup(bot: commands.Bot):
    await bot.add_cog(BardoCog(bot))
