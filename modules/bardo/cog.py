"""Módulo Bardo — interface Discord.

Só traduz mensagem em linguagem natural → chamada de service.py, e cuida da
parte que é inerentemente Discord (conectar em canal de voz, tocar o
áudio, avançar a fila). Nenhuma lógica de reconhecimento de link, busca
booleana ou fila mora aqui — tudo isso é service.py.

Sem slash command de propósito: o pedido é "@Natty toca <link>" ou
"@Natty toca <busca em linguagem natural>", do mesmo jeito que o módulo
Dice reconhece "1d20 com vantagem" em vez de exigir um comando formal.
"""

from __future__ import annotations

import asyncio
import random

import discord
from discord.ext import commands

from modules.bardo import service

# Se a busca por tags achar mais que isso, sorteamos um subconjunto em vez
# de enfileirar tudo de uma vez (algumas franquias no dataset têm 200+
# faixas — enfileirar tudo travaria a mesa numa única franquia por horas).
_MAX_RESULTADOS_NA_FILA = 15


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

        voice_state = message.author.voice
        if not voice_state or not voice_state.channel:
            await message.reply("Entra num canal de voz primeiro, aí eu toco.")
            return

        link = service.extrair_link_youtube(message.content)
        if link:
            await self._pedido_por_link(message, voice_state.channel, link)
            return

        texto_busca = service.extrair_texto_de_busca(self._sem_mencoes(message))
        await self._pedido_por_busca(message, voice_state.channel, texto_busca)

    @staticmethod
    def _sem_mencoes(message: discord.Message) -> str:
        """Tira as menções (<@id> / <@!id>) do texto — formato específico de
        Discord, então fica aqui e não em service.py."""
        texto = message.content
        for usuario in message.mentions:
            texto = texto.replace(f"<@{usuario.id}>", "").replace(f"<@!{usuario.id}>", "")
        return texto.strip()

    # -- pedido com link direto: toca na hora, substitui o que tava rolando --

    async def _pedido_por_link(self, message: discord.Message, canal: discord.VoiceChannel, link: str):
        guild_id = message.guild.id
        try:
            info = await asyncio.to_thread(service.resolver_musica, link)
        except Exception:
            await message.reply("Não consegui pegar essa música. Confere o link?")
            raise

        voice_client = await self._garantir_conectado(message.guild, canal)
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()
        service.limpar_fila(guild_id)  # link direto é pedido explícito: substitui a fila também

        await self._tocar_agora(voice_client, guild_id, info)
        await message.reply(f"Tocando **{info['titulo']}** 🎵")

    # -- pedido por tema/origem: busca booleana no dataset, enfileira --

    async def _pedido_por_busca(self, message: discord.Message, canal: discord.VoiceChannel, texto_busca: str):
        if not texto_busca:
            await message.reply(
                "Me manda o link do YouTube, ou descreve o que quer ouvir "
                "(ex: \"toca triste e bloodborne\")."
            )
            return

        guild_id = message.guild.id
        resultados = service.buscar_por_tags(texto_busca)
        if not resultados:
            await message.reply(f'Não achei nada pra "{texto_busca}" no dataset. Tenta outros termos?')
            return

        limitado = len(resultados) > _MAX_RESULTADOS_NA_FILA
        selecionados = random.sample(resultados, _MAX_RESULTADOS_NA_FILA) if limitado else resultados

        voice_client = await self._garantir_conectado(message.guild, canal)
        ja_tocando = voice_client.is_playing() or voice_client.is_paused()
        service.adicionar_varias_na_fila(guild_id, selecionados)

        aviso = ""
        if limitado:
            aviso = (
                f" (achei {len(resultados)}, botei {_MAX_RESULTADOS_NA_FILA} aleatórias na fila "
                "pra não lotar demais — busca mais específica se quiser menos variedade)"
            )

        if not ja_tocando:
            await self._tocar_proxima_da_fila(voice_client, guild_id)
            primeira = selecionados[0]
            resto = len(selecionados) - 1
            complemento = f" — mais {resto} na fila" if resto else ""
            await message.reply(f"Tocando **{primeira['nome']}** 🎵{complemento}{aviso}")
        else:
            await message.reply(f"Adicionei {len(selecionados)} música(s) à fila{aviso}")

    # -- mecânica de conexão / playback / avanço de fila, compartilhada --

    async def _garantir_conectado(
        self, guild: discord.Guild, canal: discord.VoiceChannel
    ) -> discord.VoiceClient:
        voice_client = guild.voice_client
        if voice_client is None:
            voice_client = await canal.connect()
        elif voice_client.channel != canal:
            await voice_client.move_to(canal)
        return voice_client

    async def _tocar_agora(self, voice_client: discord.VoiceClient, guild_id: int, info: dict):
        fonte = discord.FFmpegPCMAudio(info["stream_url"], **service.FFMPEG_OPTIONS)

        def _ao_terminar(erro: Exception | None):
            # discord.py chama isso numa thread separada (a do AudioPlayer),
            # não na do asyncio — por isso run_coroutine_threadsafe em vez
            # de só dar await direto.
            asyncio.run_coroutine_threadsafe(
                self._proxima_ou_silencio(voice_client, guild_id), self.bot.loop
            )

        voice_client.play(fonte, after=_ao_terminar)

    async def _proxima_ou_silencio(self, voice_client: discord.VoiceClient, guild_id: int):
        if voice_client.is_connected():
            await self._tocar_proxima_da_fila(voice_client, guild_id)

    async def _tocar_proxima_da_fila(self, voice_client: discord.VoiceClient, guild_id: int):
        proxima = service.proxima_da_fila(guild_id)
        if proxima is None:
            return
        try:
            info = await asyncio.to_thread(service.resolver_musica, proxima["link"])
        except Exception:
            # uma faixa da fila falhou em resolver (link morto, por exemplo)
            # — pula pra próxima em vez de travar a fila inteira.
            await self._tocar_proxima_da_fila(voice_client, guild_id)
            return
        await self._tocar_agora(voice_client, guild_id, info)


async def setup(bot: commands.Bot):
    await bot.add_cog(BardoCog(bot))
