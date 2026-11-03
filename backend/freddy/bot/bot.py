"""O bot do Freddy no Discord: conecta, lista servidores e canais, entra na call.

O jeito de conectar vem do Kenku FM (src/main/broadcast/DiscordBroadcast.ts,
© Owlbear Rodeo, GPL-3.0), reescrito em Python com discord.py:
- intents mínimos (servidores e estados de voz; mais mensagens de servidor,
  pro "@Freddy toca"). Mensagem que menciona o bot chega com o texto mesmo
  sem o intent privilegiado de conteúdo, então não precisa ligar nada no portal;
- ao conectar, lista os servidores do bot e os canais de voz de cada um, na
  ordem do Discord, pro painel escolher;
- toca quando tem som e para quando acaba, igual ao PlaybackManager.ts do
  Kenku (play com uma saída nova / stop); erros viram aviso no painel.

Diferenças do Kenku: um bot compartilhado (token só no backend), o chat do
Discord manda na mesma fila do painel, e ele sai sozinho da call vazia.
Roda no mesmo loop do servidor (FastAPI): nada de thread extra.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Callable

import discord

from freddy.audio.reprodutor import Reprodutor
from freddy.bot.conversa import Conversa, fala_do_evento
from freddy.bot.saida import SaidaDiscord
from freddy.dados.segredos import Segredos
from freddy.motor.motor import Motor
from modules.bardo import service

log = logging.getLogger("freddy.bot")

# Ver canais, Enviar mensagens, Ler histórico, Conectar e Falar.
PERMISSOES_DO_CONVITE = 1024 | 2048 | 65536 | 1048576 | 2097152
SEGUNDOS_SOZINHO = 300  # sozinho na call esse tempo → sai
LIMITE_DE_MENSAGEM = 1900
_MENCAO_RE = re.compile(r"<@!?\d+>|<@&\d+>")


class ErroDoBot(Exception):
    """Algo que a pessoa precisa saber (vira mensagem no painel)."""


def link_de_convite(aplicativo_id: int | str) -> str:
    return (
        f"https://discord.com/oauth2/authorize?client_id={aplicativo_id}"
        f"&scope=bot&permissions={PERMISSOES_DO_CONVITE}"
    )


class BotDoFreddy:
    def __init__(self, motor: Motor, reprodutor: Reprodutor, conversa: Conversa, segredos: Segredos):
        self.motor = motor
        self.reprodutor = reprodutor
        self.conversa = conversa
        self.segredos = segredos
        self.cliente: discord.Client | None = None
        self._tarefa: asyncio.Task | None = None
        self.situacao = "desligado"  # desligado | conectando | conectado | erro
        self.erro: str | None = None
        self.voz: discord.VoiceClient | None = None
        self.saida: SaidaDiscord | None = None
        self.canal_de_texto: discord.abc.Messageable | None = None
        self._sozinho: asyncio.Task | None = None
        self._saindo = False
        self.ao_mudar: Callable[[], None] = lambda: None
        motor.ao_evento(self._evento)
        motor.inscrever(self._atualizar_player)
        # "Ouvir aqui" (ou só na call) fica guardado entre uma vez e outra.
        self._arquivo_preferencias = segredos.arquivo.with_name("preferencias.json")
        if self.mesa is not None:
            self.mesa.ouvir_aqui = self._preferencias().get("ouvirAqui", True)

    @property
    def mesa(self):
        return getattr(self.reprodutor, "mesa", None)

    # --- o que o painel vê -------------------------------------------------

    def estado(self) -> dict:
        c = self.cliente
        pronto = c is not None and c.is_ready()
        eu = c.user if pronto else None
        servidores = []
        if pronto:
            for g in sorted(c.guilds, key=lambda g: g.name.lower()):
                canais = sorted(g.voice_channels, key=lambda ch: ch.position)
                servidores.append(
                    {
                        "id": str(g.id),
                        "nome": g.name,
                        "icone": g.icon.url if g.icon else None,
                        "canais": [
                            {"id": str(ch.id), "nome": ch.name, "pessoas": sum(not m.bot for m in ch.members)}
                            for ch in canais
                        ],
                    }
                )
        canal = None
        if self.voz is not None and self.voz.is_connected() and self.voz.channel is not None:
            ch = self.voz.channel
            canal = {"id": str(ch.id), "nome": ch.name, "servidorId": str(ch.guild.id), "servidor": ch.guild.name}
        mesa = self.mesa
        return {
            "configurado": self.segredos.token() is not None,
            "doAmbiente": self.segredos.do_ambiente,
            "situacao": self.situacao,
            "erro": self.erro,
            "bot": {"id": str(eu.id), "nome": eu.name, "avatar": eu.display_avatar.url} if eu else None,
            "convite": link_de_convite(c.application_id or eu.id) if eu else None,
            "servidores": servidores,
            "canal": canal,
            "ouvirAqui": mesa.ouvir_aqui if mesa is not None else True,
            "podeTocar": mesa is not None,
            "transmissao": self._transmissao(),
        }

    def _transmissao(self) -> dict | None:
        """O que de fato está indo pra call (pra testar sem ouvir)."""
        voz, saida = self.voz, self.saida
        if voz is None or saida is None:
            return None
        return {"conectado": voz.is_connected(), "tocando": voz.is_playing(), "dave": _dave(voz), **saida.medidor()}

    def _notificar(self) -> None:
        try:
            self.ao_mudar()
        except Exception:  # noqa: BLE001 — avisar o painel nunca derruba o bot
            log.exception("Falha ao avisar o painel")

    def _mudar(self, situacao: str, erro: str | None = None) -> None:
        self.situacao, self.erro = situacao, erro
        self._notificar()

    # --- conectar ----------------------------------------------------------

    async def ligar(self) -> None:
        """Ao subir o Freddy: conecta sozinho se já tem token guardado."""
        token = self.segredos.token()
        if token:
            await self.conectar(token)

    async def conectar(self, token: str) -> None:
        await self.desconectar()
        self._mudar("conectando")
        intents = discord.Intents.none()
        intents.guilds = True
        intents.voice_states = True
        intents.guild_messages = True
        cliente = discord.Client(intents=intents)
        pronto = asyncio.Event()
        self._registrar(cliente, pronto)

        tarefa = asyncio.create_task(cliente.start(token))
        espera = asyncio.create_task(pronto.wait())
        feito, _ = await asyncio.wait({tarefa, espera}, timeout=30, return_when=asyncio.FIRST_COMPLETED)
        if espera in feito:
            self.cliente, self._tarefa = cliente, tarefa
            tarefa.add_done_callback(self._caiu)
            log.info("Bot conectado como %s", cliente.user)
            self._mudar("conectado")
            return
        espera.cancel()
        if tarefa in feito and tarefa.exception() is not None:
            e = tarefa.exception()
            log.warning("Não conectei no Discord: %r", e)
            if isinstance(e, discord.LoginFailure):
                motivo = "token inválido (confere se copiou o token do bot inteiro, em Bot → Reset Token)"
            elif isinstance(e, OSError):  # inclui o "Cannot connect to host" do aiohttp
                motivo = "não alcancei o Discord (sem internet, ou algo bloqueando)"
            else:
                motivo = f"não consegui conectar ({e})"
        else:
            tarefa.cancel()
            motivo = "o Discord não respondeu (sem internet?)"
        await cliente.close()
        self._mudar("erro", motivo)

    async def desconectar(self) -> None:
        await self.sair()
        cliente, self.cliente = self.cliente, None
        if cliente is not None:
            self._saindo = True
            try:
                await cliente.close()
            finally:
                self._saindo = False
        self._tarefa = None
        if self.situacao != "desligado":
            self._mudar("desligado")

    def _caiu(self, tarefa: asyncio.Task) -> None:
        if self._saindo or tarefa is not self._tarefa:
            return
        erro = tarefa.exception() if not tarefa.cancelled() else None
        self.cliente = None
        self.voz = None
        if self.mesa is not None:
            self.mesa.sair_do_discord()
        self._mudar("erro", f"a conexão com o Discord caiu ({erro})" if erro else "a conexão com o Discord caiu")

    # --- call --------------------------------------------------------------

    async def entrar(self, canal_id: int) -> None:
        if self.cliente is None or not self.cliente.is_ready():
            raise ErroDoBot("o bot não está conectado")
        mesa = self.mesa
        if mesa is None:
            raise ErroDoBot("no modo --sem-som não tem som pra mandar pro Discord")
        canal = self.cliente.get_channel(canal_id)
        if not isinstance(canal, (discord.VoiceChannel, discord.StageChannel)):
            raise ErroDoBot("não achei esse canal de voz")
        permissoes = canal.permissions_for(canal.guild.me)
        if not (permissoes.connect and permissoes.speak):
            raise ErroDoBot(f"o bot não tem permissão de entrar e falar em #{canal.name}")
        if canal.user_limit and len(canal.members) >= canal.user_limit and not permissoes.move_members:
            raise ErroDoBot(f"#{canal.name} está cheio")

        if self.voz is not None and self.voz.is_connected():
            if self.voz.guild.id == canal.guild.id:
                await self.voz.move_to(canal)
                self._notificar()
                self._conferir_sozinho()
                return
            await self.sair()

        try:
            voz = await canal.connect(self_deaf=True, timeout=20, reconnect=True)
        except asyncio.TimeoutError as e:
            raise ErroDoBot("o Discord não deixou entrar na call (demorou demais)") from e
        except discord.ClientException as e:
            raise ErroDoBot(f"não consegui entrar na call ({e})") from e
        if not discord.opus.is_loaded() and not discord.opus._load_default():
            await voz.disconnect(force=True)
            raise ErroDoBot("falta a biblioteca Opus (Fedora: sudo dnf install opus)")
        mesa.entrar_no_discord()
        self.voz = voz
        self._atualizar_player()
        log.info("Entrei em #%s (%s)", canal.name, canal.guild.name)
        self._notificar()
        self._conferir_sozinho()

    async def sair(self) -> None:
        self._cancelar_sozinho()
        voz, self.voz = self.voz, None
        self.saida = None
        if voz is not None and voz.is_playing():
            voz.stop()
        if voz is not None:
            try:
                await voz.disconnect(force=True)
            except Exception:  # noqa: BLE001
                log.exception("Erro ao sair da call")
        if self.mesa is not None:
            self.mesa.sair_do_discord()
        self.canal_de_texto = None
        self._notificar()

    def definir_ouvir_aqui(self, ligado: bool) -> None:
        if self.mesa is not None:
            self.mesa.ouvir_aqui = ligado
        self._guardar_preferencia("ouvirAqui", ligado)
        self._notificar()

    def _preferencias(self) -> dict:
        try:
            return json.loads(self._arquivo_preferencias.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _guardar_preferencia(self, chave: str, valor) -> None:
        from freddy.dados.playlists import gravar_json

        try:
            gravar_json(self._arquivo_preferencias, {**self._preferencias(), chave: valor})
        except OSError:
            log.warning("Não consegui guardar a preferência %s", chave)

    # --- teste e diagnóstico -----------------------------------------------

    async def assobiar(self) -> None:
        """O teste da call: o PC fica mudo e o Frederico assobia só pelo Discord."""
        mesa = self.mesa
        if mesa is None:
            raise ErroDoBot("no modo --sem-som não tem som pra mandar pro Discord")
        if self.voz is None or not self.voz.is_connected():
            raise ErroDoBot("o bot não está em nenhuma call: entra num canal primeiro")
        if mesa.assobiando:
            return
        ouvia = mesa.ouvir_aqui
        mesa.ouvir_aqui = False  # sem tocar no arquivo: é só durante o assobio
        self._notificar()
        try:
            segundos = mesa.assobiar()
            self._atualizar_player()
            await asyncio.sleep(segundos + 0.6)  # + a folga da cópia
        finally:
            mesa.ouvir_aqui = ouvia
            self._atualizar_player()
            self._notificar()

    def diagnostico(self) -> dict:
        """Tudo que ajuda a saber por onde o som está saindo (modo debug do painel)."""
        mesa = self.mesa
        tocando = self.motor.estado().get("tocando")
        return {
            "bot": self.situacao,
            "canal": self.voz.channel.name if self.voz is not None and self.voz.channel is not None else None,
            "transmissao": self._transmissao(),
            "mesa": mesa.diagnostico() if mesa is not None else None,
            "motor": {"situacao": self.motor.estado().get("situacao"), "titulo": tocando.get("titulo") if tocando else None},
        }

    def _player_parou(self, erro: Exception | None) -> None:
        if erro:
            log.error("O player do Discord parou: %s", erro)

    # --- o player da call, do jeito do Kenku -------------------------------
    # Kenku (PlaybackManager.ts): som começou → audioPlayer.play(recurso novo);
    # som acabou → audioPlayer.stop(). Aqui: motor tocando/carregando (ou o
    # assobio) → voz.play(SaidaDiscord nova); parou → voz.stop().

    def _deve_tocar(self) -> bool:
        mesa = self.mesa
        if mesa is not None and mesa.assobiando:
            return True
        return self.motor.estado().get("situacao") in ("tocando", "carregando")

    def _atualizar_player(self) -> None:
        voz, mesa = self.voz, self.mesa
        if voz is None or mesa is None or not voz.is_connected():
            return
        if self._deve_tocar():
            if not voz.is_playing():
                saida = SaidaDiscord(mesa)
                try:
                    voz.play(saida, after=self._player_parou)
                except Exception as e:  # noqa: BLE001
                    log.exception("Não consegui tocar na call")
                    self._mudar(self.situacao, f"não consegui tocar na call ({e})")
                    return
                self.saida = saida
                log.info("Tocando na call")
        elif voz.is_playing():
            voz.stop()
            log.info("Parei de tocar na call")

    # --- sozinho na call ---------------------------------------------------

    def _conferir_sozinho(self) -> None:
        if self.voz is None or self.voz.channel is None:
            return self._cancelar_sozinho()
        tem_gente = any(not m.bot for m in self.voz.channel.members)
        if tem_gente:
            self._cancelar_sozinho()
        elif self._sozinho is None:
            self._sozinho = asyncio.get_running_loop().create_task(self._sair_se_continuar_sozinho())

    def _cancelar_sozinho(self) -> None:
        if self._sozinho is not None:
            self._sozinho.cancel()
            self._sozinho = None

    async def _sair_se_continuar_sozinho(self) -> None:
        await asyncio.sleep(SEGUNDOS_SOZINHO)
        self._sozinho = None
        canal = self.canal_de_texto
        await self.sair()
        if canal is not None:
            await self._enviar(canal, "Saí da call porque fiquei sozinho 🦜")

    # --- eventos do Discord ------------------------------------------------

    def _registrar(self, cliente: discord.Client, pronto: asyncio.Event) -> None:
        @cliente.event
        async def on_ready():
            pronto.set()
            self._notificar()

        def avisar_quando(nome: str):
            async def mudou(*_):
                self._notificar()

            mudou.__name__ = nome
            cliente.event(mudou)

        for nome in (
            "on_guild_join",
            "on_guild_remove",
            "on_guild_update",
            "on_guild_channel_create",
            "on_guild_channel_delete",
            "on_guild_channel_update",
        ):
            avisar_quando(nome)

        @cliente.event
        async def on_voice_state_update(membro: discord.Member, antes: discord.VoiceState, depois: discord.VoiceState):
            if cliente.user and membro.id == cliente.user.id and depois.channel is None and self.voz is not None:
                # Tiraram o bot da call (ou caiu sem volta).
                canal = self.canal_de_texto
                self.voz = None
                await self.sair()
                if canal is not None:
                    await self._enviar(canal, "Me tiraram da call. Pra voltar, escolhe o canal no painel.")
                return
            self._conferir_sozinho()
            self._notificar()

        @cliente.event
        async def on_message(mensagem: discord.Message):
            await self._mensagem(cliente, mensagem)

    async def _mensagem(self, cliente: discord.Client, mensagem: discord.Message) -> None:
        if mensagem.author.bot or mensagem.guild is None or cliente.user is None:
            return
        papel = mensagem.guild.self_role
        if cliente.user not in mensagem.mentions and not (papel is not None and papel in mensagem.role_mentions):
            return
        texto = _MENCAO_RE.sub(" ", mensagem.content).strip()
        self.canal_de_texto = mensagem.channel

        if Conversa.quer_sair(texto):
            if self.voz is None:
                return await self._responder(mensagem, "Não estou em call nenhuma.")
            await self.sair()
            self.canal_de_texto = mensagem.channel
            return await self._responder(mensagem, "Saí da call 👋")

        if self._quer_tocar(texto):
            erro = await self._garantir_call(mensagem)
            if erro:
                return await self._responder(mensagem, erro)

        try:
            resposta = await self.conversa.responder(texto)
        except Exception as e:  # noqa: BLE001
            log.exception("Erro respondendo no Discord")
            resposta = f"Deu ruim aqui 😕 ({e})"
        await self._responder(mensagem, resposta)

    @staticmethod
    def _quer_tocar(texto: str) -> bool:
        if re.match(r"^(?:toca|toque|tocar|p[õo]e|bota|coloca|play|carrega|abre|adiciona|add)\s+(?:a\s+)?playlist\b", texto, re.I):
            return True
        pedido = service.interpretar_pedido(texto)
        return pedido is not None and pedido.acao == "tocar" and bool(pedido.link or pedido.busca)

    async def _garantir_call(self, mensagem: discord.Message) -> str | None:
        """Pedido de tocar: entra na call de quem pediu, se o bot não está em nenhuma."""
        if self.voz is not None and self.voz.is_connected():
            if self.voz.guild.id != mensagem.guild.id:
                return (
                    f"Agora estou tocando em **{self.voz.guild.name}**. Por enquanto é uma mesa por vez: "
                    "me tira de lá pelo painel (ou `@Freddy sai` lá) e me chama de novo."
                )
            return None
        voz_do_autor = getattr(mensagem.author, "voice", None)
        if voz_do_autor is None or voz_do_autor.channel is None:
            return "Entra num canal de voz primeiro, aí eu vou junto e toco."
        try:
            await self.entrar(voz_do_autor.channel.id)
        except ErroDoBot as e:
            return f"Não consegui entrar na call: {e}."
        return None

    async def _responder(self, mensagem: discord.Message, texto: str) -> None:
        try:
            await mensagem.reply(_cortar(texto), mention_author=False)
        except discord.HTTPException:
            log.exception("Não consegui responder no Discord")

    async def _enviar(self, canal: discord.abc.Messageable, texto: str) -> None:
        try:
            await canal.send(_cortar(texto))
        except discord.HTTPException:
            log.exception("Não consegui avisar no Discord")

    def _evento(self, evento: dict) -> None:
        """A fila andou sozinha: avisa no canal do último pedido feito pelo Discord."""
        if self.canal_de_texto is None or self.voz is None:
            return
        asyncio.get_running_loop().create_task(self._enviar(self.canal_de_texto, fala_do_evento(evento)))


def _dave(voz) -> dict | None:
    """A criptografia de ponta a ponta da call (DAVE): se o som sai cifrado do jeito que o Discord espera."""
    con = getattr(voz, "_connection", None)
    if con is None:
        return None
    sessao = getattr(con, "dave_session", None)
    return {
        "versao": getattr(con, "dave_protocol_version", None),
        "pronta": bool(sessao and sessao.ready),
        "criptografando": bool(getattr(con, "can_encrypt", False)),
        "modo": getattr(voz, "mode", None),
    }

def _cortar(texto: str) -> str:
    return texto if len(texto) <= LIMITE_DE_MENSAGEM else texto[: LIMITE_DE_MENSAGEM - 1] + "…"
