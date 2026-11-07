"""O chat do Discord: "@Freddy toca triste e bloodborne" → comando no Motor → resposta.

O mesmo Motor do painel: uma fila só pros dois. As regras de entender o
pedido são as do núcleo (freddy.nucleo.pedido).
Playlists salvas valem aqui igual ao chat do painel (playlistsChat.ts).
Sem discord.py aqui: o bot (bot.py) só entrega o texto e manda a resposta.
"""

from __future__ import annotations

import asyncio
import re
from typing import Protocol

from freddy.dados.acervo import Acervo
from freddy.dados.playlists import Playlists, achar_playlist, mesmo_nome
from freddy.salas.fila import MAX_FILA
from freddy.salas.motor import Motor
from freddy.nucleo.busca import sortear_da_busca
from freddy.nucleo.pedido import Pedido, interpretar_pedido

MOSTRADAS_NA_FILA = 10

AJUDA = "\n".join(
    [
        "Me chama com **@Freddy** e pede do seu jeito:",
        "• **toca triste e bloodborne**: busca no acervo (`e`, `ou`, `sem`)",
        "• **toca <link do YouTube>** · **toca <nome de uma música>** (procuro no YouTube)",
        "• **pula** · **pausa** · **continua** · **para** · **repete** · **fila** · **limpa a fila**",
        "• **volume 30** · **aumenta** · **abaixa**",
        "• **playlists** · **toca a playlist sessão 12** · **põe a playlist cripta na fila** · **salva a fila como sessão 12**",
        "• **sai**: saio da call",
        "O resto (escolher canal, arrumar o acervo, montar playlist) é no painel do Freddy.",
    ]
)

_AJUDA_RE = re.compile(r"^(ajuda|help|comandos|socorro|\?)\W*$", re.I)
_SAIR_RE = re.compile(r"^(sai|sair|vaza|tchau)(?: da call| do canal)?\W*$", re.I)
_LISTAR_RE = re.compile(r"^(?:quais (?:s[ãa]o )?(?:as )?|mostra (?:as )?|minhas |lista (?:as )?)?playlists(?: salvas)?\s*\??$", re.I)
_ENFILEIRAR_RE = re.compile(r"^(?:p[õo]e|bota|coloca|adiciona|add)\s+(?:a\s+)?playlist\s+(.+?)\s+(?:na|no fim da)\s+fila[.!]*$", re.I)
_ADICIONAR_RE = re.compile(r"^(?:adiciona|add)\s+(?:a\s+)?playlist\s+(.+?)[.!]*$", re.I)
_TOCAR_PL_RE = re.compile(r"^(?:toca|toque|tocar|p[õo]e|bota|coloca|play|carrega|abre)\s+(?:a\s+)?playlist\s+(.+?)[.!]*$", re.I)
_SALVAR_RE = re.compile(r"^salv(?:a|ar|e)\s+(?:a\s+)?(?:fila|playlist)\s+(?:como|com o nome(?: de)?)\s+(.+?)[.!]*$", re.I)


class Youtube(Protocol):
    def info(self, link: str) -> dict: ...
    def buscar(self, texto: str) -> dict: ...


def negrito(texto: str) -> str:
    return "**" + re.sub(r"([*_~`|\\])", r"\\\1", texto) + "**"


def _plural(n: int, s: str, p: str | None = None) -> str:
    return f"{n} {s if n == 1 else (p or s + 's')}"


def _duracao(m: dict) -> str:
    s = m.get("duracaoSegundos")
    return f" ({int(s) // 60}:{int(s) % 60:02d})" if s else ""


def fala_do_evento(evento: dict) -> str:
    """O que o Freddy avisa no canal quando a fila anda sozinha ."""
    if evento["tipo"] == "tocando_agora":
        return f"Tocando agora {negrito(evento['musica']['titulo'])} 🎵"
    if evento["tipo"] == "fila_acabou":
        return "A fila acabou. Pede mais uma? 🦜"
    return f"Não consegui tocar {negrito(evento['musica']['titulo'])} ({evento['motivo']}), pulei."


class Conversa:
    def __init__(self, motor: Motor, acervo: Acervo, playlists: Playlists, youtube: Youtube):
        self.motor = motor
        self.acervo = acervo
        self.playlists = playlists
        self.youtube = youtube

    async def responder(self, texto: str) -> str:
        texto = texto.strip()
        if not texto or _AJUDA_RE.match(texto):
            return AJUDA

        playlist = self._playlist(texto)
        if playlist is not None:
            return await playlist

        pedido = interpretar_pedido(texto)
        if pedido is None:
            return "Não entendi 🦜 Tenta **@Freddy toca calmo e hollow knight**, **@Freddy pula** ou **@Freddy ajuda**."
        return await self._executar(pedido)

    @staticmethod
    def quer_sair(texto: str) -> bool:
        return bool(_SAIR_RE.match(texto.strip()))

    # --- pedidos de música -------------------------------------------------

    async def _executar(self, pedido: Pedido) -> str:
        m = self.motor
        acao = pedido.acao
        if acao == "tocar":
            if pedido.link:
                return await self._tocar_link(pedido.link)
            if pedido.busca:
                return await self._tocar_busca(pedido.busca)
            return 'Me manda o link do YouTube, ou descreve o que quer ouvir (ex: "@Freddy toca triste e bloodborne").'
        if acao == "pular":
            r = m.executar({"tipo": "pular"})
            if not r["pulou"]:
                return "Não tem nada tocando."
            aviso = " (repetição desligada)" if r["repetiaAntes"] else ""
            return f"Pulei ⏭️{aviso}" if r["temProxima"] else f"Pulei ⏭️ A fila acabou.{aviso}"
        if acao == "fila":
            return self._descrever_fila()
        if acao == "limpar_fila":
            n = m.executar({"tipo": "limpar_fila"})["removidas"]
            return f"Limpei a fila ({_plural(n, 'música')}) 🧹" if n else "A fila já está vazia."
        if acao == "pausar":
            return "Pausei ⏸️" if m.executar({"tipo": "pausar"})["ok"] else "Não tem nada tocando."
        if acao == "continuar":
            return "Continuando ▶️" if m.executar({"tipo": "continuar"})["ok"] else "Não tem nada pausado."
        if acao == "parar":
            return "Parei ⏹️" if m.executar({"tipo": "parar"})["ok"] else "Não estou tocando nada."
        if acao == "repetir":
            tocando = m.estado()["tocando"]
            if tocando is None and pedido.repetir is None:
                return "Não tem nada tocando pra repetir."
            r = m.executar({"tipo": "repetir", **({"ligar": pedido.repetir} if pedido.repetir is not None else {})})
            if r["repetir"] and tocando:
                return (
                    f"🔁 Repetindo {negrito(tocando['titulo'])}: quando acabar, volta do começo. "
                    "Pra parar: **@Freddy para de repetir**."
                )
            return "➡️ Repetição desligada. Quando essa acabar, sigo a fila."
        if acao == "volume":
            if pedido.volume is None and pedido.delta_volume is None:
                return f"O volume está em {m.estado()['volume']}%."
            comando = {"tipo": "volume", "valor": pedido.volume} if pedido.volume is not None else {"tipo": "volume", "delta": pedido.delta_volume}
            return f"Volume em {m.executar(comando)['volume']}% 🔊"
        return "Não entendi 🦜"

    def _por(self, musicas: list[dict], onde: str = "fim") -> dict:
        return self.motor.executar({"tipo": "adicionar", "musicas": musicas, "onde": onde})

    async def _tocar_link(self, link: str) -> str:
        try:
            info = await asyncio.to_thread(self.youtube.info, link)
            titulo = info.get("titulo") or "Link do YouTube"
            duracao = info.get("duracaoSegundos")
        except Exception:  # noqa: BLE001 — sem título, o reprodutor descobre depois
            titulo, duracao = "Link do YouTube", None
        musica = {"titulo": titulo, "link": link, **({"duracaoSegundos": duracao} if duracao else {})}
        r = self._por([musica])
        if not r["entraram"]:
            return self._fila_cheia()
        if r["comecou"]:
            return f"Tocando {negrito(titulo)} 🎵"
        return f"Adicionei {negrito(titulo)} na fila (posição {r['posicao']}) 📜"

    async def _tocar_busca(self, busca: str) -> str:
        achadas, total = sortear_da_busca(busca, self.acervo.faixas())
        if not achadas:
            return await self._busca_livre(busca)
        musicas = [{"titulo": f["nome"], "link": f["link"], "faixaId": f["id"], "origem": f["origem"]["nome"]} for f in achadas]
        aviso = f" (achei {total}, sorteei {len(musicas)})" if total > len(musicas) else ""
        r = self._por(musicas)
        if not r["entraram"]:
            return self._fila_cheia()
        if r["comecou"]:
            resto = r["entraram"] - 1
            complemento = f", mais {resto} na fila" if resto else ""
            return f"Tocando {negrito(musicas[0]['titulo'])} 🎵{complemento}{aviso}"
        return f"Adicionei {_plural(r['entraram'], 'música')} na fila{aviso} 📜"

    async def _busca_livre(self, busca: str) -> str:
        try:
            achada = await asyncio.to_thread(self.youtube.buscar, busca)
        except LookupError:
            return f'Não achei nada pra "{busca}", nem no acervo nem no YouTube 😕'
        except Exception as e:  # noqa: BLE001
            from freddy.audio.fontes.youtube import motivo_em_portugues

            return f'Não achei "{busca}" no acervo, e o YouTube deu problema ({motivo_em_portugues(e)}) 😕'
        musica = {k: v for k, v in achada.items() if v is not None}
        r = self._por([musica])
        if not r["entraram"]:
            return self._fila_cheia()
        onde = "tocando" if r["comecou"] else f"na fila (posição {r['posicao']})"
        return (
            f'Não tinha "{busca}" no acervo, então procurei no YouTube: {negrito(musica["titulo"])}, {onde} 🔎\n'
            "Se for boa, guarda no acervo pelo painel do Freddy."
        )

    def _descrever_fila(self) -> str:
        e = self.motor.estado()
        tocando, proximas = e["tocando"], e["proximas"]
        if tocando is None:
            return "Não tem nada tocando, e a fila está vazia."
        linhas = [f"🎵 Tocando: {negrito(tocando['titulo'])}{_duracao(tocando)}{' 🔁 (repetindo)' if e['repetir'] else ''}"]
        if not proximas:
            linhas.append("A fila está vazia.")
        else:
            linhas.append("📜 Próximas:")
            linhas += [f"{i}. {m['titulo']}{_duracao(m)}" for i, m in enumerate(proximas[:MOSTRADAS_NA_FILA], 1)]
            if len(proximas) > MOSTRADAS_NA_FILA:
                linhas.append(f"… e mais {len(proximas) - MOSTRADAS_NA_FILA}")
        return "\n".join(linhas)

    def _fila_cheia(self) -> str:
        return f"A fila já tem {MAX_FILA} músicas. Espera andar um pouco ou pede **@Freddy limpa a fila**."

    # --- playlists salvas (porta do playlistsChat.ts) ----------------------

    def _playlist(self, texto: str):
        """A corrotina da resposta, se o texto é sobre playlist; senão None."""
        if _LISTAR_RE.match(texto):
            return self._listar_playlists()
        if m := _SALVAR_RE.match(texto):
            return self._salvar_fila(_sem_aspas(m.group(1)))
        if m := (_ENFILEIRAR_RE.match(texto) or _ADICIONAR_RE.match(texto)):
            return self._usar_playlist(_sem_aspas(m.group(1)), "fila")
        if m := _TOCAR_PL_RE.match(texto):
            return self._usar_playlist(_sem_aspas(m.group(1)), "tocar")
        return None

    async def _listar_playlists(self) -> str:
        lista = self.playlists.listar()
        if not lista:
            return "Nenhuma playlist salva ainda. Monta a fila e manda **@Freddy salva a fila como sessão 12**."
        linhas = [f"• {negrito(p['nome'])} ({_plural(len(p['musicas']), 'música')})" for p in lista]
        return "📁 Suas playlists:\n" + "\n".join(linhas)

    async def _salvar_fila(self, nome: str) -> str:
        import time

        from freddy.salas.fila import novo_uid

        e = self.motor.estado()
        todas = ([e["tocando"]] if e["tocando"] else []) + e["proximas"]
        if not todas:
            return "A fila está vazia: põe umas músicas antes de salvar."
        existente = next((p for p in self.playlists.listar() if mesmo_nome(p["nome"], nome)), None)
        campos = ("titulo", "link", "faixaId", "origem", "duracaoSegundos")
        playlist = {
            "id": existente["id"] if existente else novo_uid(),
            "nome": nome,
            "musicas": [{k: m[k] for k in campos if m.get(k) is not None} for m in todas],
            "atualizadaEm": time.time() * 1000,
        }
        self.playlists.salvar(playlist)
        return f"{'Atualizei' if existente else 'Salvei'} a playlist {negrito(nome)} com {_plural(len(todas), 'música')} 💾"

    async def _usar_playlist(self, nome: str, como: str) -> str:
        lista = self.playlists.listar()
        if not lista:
            return "Você ainda não tem playlist salva. Monta a fila e manda **@Freddy salva a fila como sessão 12**."
        achadas = achar_playlist(nome, lista)
        if len(achadas) > 1:
            return f'Tenho mais de uma com "{nome}": ' + ", ".join(negrito(p["nome"]) for p in achadas) + ". Qual delas?"
        if not achadas:
            return f'Não achei a playlist "{nome}". Tenho: ' + ", ".join(negrito(p["nome"]) for p in lista[:6]) + "."
        p = achadas[0]
        if not p["musicas"]:
            return f"A playlist {negrito(p['nome'])} está vazia."
        if como == "tocar":
            self.motor.executar({"tipo": "limpar_fila"})
            r = self._por(p["musicas"], "agora")
            return f"Tocando a playlist {negrito(p['nome'])} 🎵 ({_plural(r['entraram'], 'música')}){_aviso_limite(r['entraram'], len(p['musicas']))}"
        r = self._por(p["musicas"])
        if not r["entraram"]:
            return self._fila_cheia()
        return f"Pus a playlist {negrito(p['nome'])} na fila ({_plural(r['entraram'], 'música')}) 📜{_aviso_limite(r['entraram'], len(p['musicas']))}"


def _sem_aspas(t: str) -> str:
    return t.strip().strip("\"'“”«»").strip()


def _aviso_limite(entraram: int, total: int) -> str:
    return f"\n⚠️ Entraram {entraram} de {total}: a fila encheu (cabem {MAX_FILA} esperando)." if entraram < total else ""
