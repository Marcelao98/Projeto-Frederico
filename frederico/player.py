"""O tocador do Frederico: fila, repetir, pular, pausar, volume — sem Discord.

É o que o cog do Bardo fazia em volta do voice_client, tirado de lá. A API é
síncrona (funções normais, chamáveis de qualquer thread); o áudio sai por
`ler()`, que quem toca (o motor de áudio, ou um AudioSource do Discord no
futuro) chama a cada bloco. Em vez de responder num canal, o player devolve
texto nas chamadas e registra eventos ("tocando agora", "pulei") que cada
interface mostra do jeito dela.
"""

from __future__ import annotations

import itertools
import logging
import os
import queue
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Protocol

import numpy as np

from frederico import service
from frederico.fonte import CANAIS, FonteFFmpeg, comando_ffmpeg

log = logging.getLogger(__name__)

VOLUME_PADRAO = 30  # %; por cima da voz, mais baixo que o padrão do Bardo (50)
MAX_EVENTOS = 50


class Fonte(Protocol):
    terminou: bool

    def ler(self, quadros: int) -> np.ndarray: ...
    def fechar(self) -> None: ...


def eh_arquivo_local(texto: str) -> bool:
    return os.path.isfile(texto.strip().strip('"'))


def abrir_fonte(musica: service.Musica, info: dict | None = None) -> FonteFFmpeg:
    """Abre `musica` no FFmpeg: arquivo local direto; link resolvido pelo yt-dlp (URL nova a cada vez)."""
    if eh_arquivo_local(musica.link):
        return FonteFFmpeg(comando_ffmpeg(musica.link.strip().strip('"')))
    if info is None:
        info = service.resolver_musica(musica.link)
    return FonteFFmpeg(comando_ffmpeg(info["stream_url"], service.opcoes_ffmpeg(info.get("http_headers"))))


class Player:
    def __init__(
        self,
        abrir: Callable[[service.Musica, dict | None], Fonte] = abrir_fonte,
        relogio: Callable[[], float] = time.monotonic,
    ):
        self._abrir = abrir
        self._relogio = relogio
        self.fila = service.Fila()
        self.volume = VOLUME_PADRAO
        self.pausado = False
        self._fonte: Fonte | None = None
        self._inicio = 0.0
        self._tentativa = 0
        self._trava = threading.RLock()
        self._ids = itertools.count(1)
        self.eventos: deque[tuple[int, str]] = deque(maxlen=MAX_EVENTOS)
        # Fim de música é detectado na thread de áudio, mas tratado aqui fora:
        # resolver a próxima no YouTube leva segundos.
        self._fins: queue.Queue[Fonte] = queue.Queue()
        threading.Thread(target=self._tratar_fins, daemon=True).start()

    # ------------------------------------------------------------ áudio

    def ler(self, quadros: int) -> np.ndarray:
        """Próximo bloco de música (float32, estéreo), já com o volume. Silêncio se nada toca."""
        fonte = self._fonte
        if fonte is None or self.pausado:
            return np.zeros((quadros, CANAIS), np.float32)
        bloco = fonte.ler(quadros)
        if len(bloco) < quadros:
            if fonte.terminou:
                self._fonte = None
                self._fins.put(fonte)
            bloco = np.concatenate([bloco, np.zeros((quadros - len(bloco), CANAIS), np.float32)])
        return bloco * (self.volume / 100)

    # ------------------------------------------------------------ comandos

    def executar(self, texto: str) -> str:
        """Frase em português ("pula", "volume 30", "toca triste e bloodborne"). Sem verbo, é o que tocar."""
        pedido = service.interpretar_pedido(texto)
        if pedido is None:
            return self.tocar(texto)
        if pedido.acao == "tocar":
            return self.tocar(pedido.link or pedido.busca or "")
        if pedido.acao == "volume":
            if pedido.volume is None and pedido.delta_volume is None:
                return f"O volume está em {self.volume}%."
            return self.mudar_volume(service.novo_volume(self.volume, pedido))
        if pedido.acao == "repetir":
            return self.repetir(pedido.repetir)
        acoes = {
            "pular": self.pular, "fila": self.descrever_fila, "limpar_fila": self.limpar_fila,
            "pausar": self.pausar, "continuar": self.continuar, "parar": self.parar,
        }
        return acoes[pedido.acao]()

    def tocar(self, texto: str) -> str:
        """Link do YouTube, caminho de arquivo, ou temas/nome pra buscar (dataset, senão YouTube)."""
        texto = texto.strip()
        if not texto:
            return "Manda um link, um arquivo ou uns temas (ex: triste e bloodborne)."
        info = None
        if eh_arquivo_local(texto):
            caminho = texto.strip('"')
            musicas = [service.Musica(Path(caminho).stem, caminho)]
            aviso = ""
        elif link := service.extrair_link_youtube(texto):
            try:
                info = service.resolver_musica(link)
            except Exception:
                log.exception("falha ao resolver %s", link)
                return "Não consegui pegar essa música. Confere o link?"
            musicas = [service.Musica(info["titulo"], link, info["duracao_segundos"])]
            aviso = ""
        else:
            musicas, achadas = service.buscar_musicas(texto)
            aviso = f" (achei {achadas}, sorteei {len(musicas)})" if achadas > len(musicas) else ""
            if not musicas:
                try:
                    info = service.resolver_por_busca_livre(texto)
                except Exception:
                    log.exception("falha na busca livre por %r", texto)
                    return f'Não achei nada pra "{texto}", nem no dataset nem no YouTube.'
                musicas = [service.Musica(info["titulo"], info["link"], info["duracao_segundos"])]
                aviso = " (do YouTube)"

        with self._trava:
            entraram = self.fila.adicionar_varias(musicas)
            if entraram == 0:
                return f"A fila já tem {service.MAX_FILA} músicas."
            if self.fila.tocando is not None:
                if entraram == 1:
                    return f"Na fila: {musicas[0].titulo} (posição {len(self.fila.proximas)}){aviso}"
                return f"Adicionei {entraram} músicas na fila{aviso}"
            tocando = self._tocar_proxima(info, avisar=False)
        if tocando is None:
            return "Não consegui tocar nada disso."
        resto = len(self.fila.proximas)
        return f"Tocando {tocando.titulo}{f' — mais {resto} na fila' if resto else ''}{aviso}"

    def pular(self) -> str:
        with self._trava:
            if self.fila.tocando is None:
                return "Não tem nada tocando."
            repetia, self.fila.repetir = self.fila.repetir, False
            self._fechar_fonte()
            self.pausado = False
            proxima = self._tocar_proxima(avisar=False)
        aviso = " (repetição desligada)" if repetia else ""
        return f"Pulei ⏭️ Tocando {proxima.titulo}{aviso}" if proxima else f"Pulei ⏭️ A fila acabou.{aviso}"

    def parar(self) -> str:
        with self._trava:
            self.fila.resetar()
            self.fila.repetir = False
            self._fechar_fonte()
            self.pausado = False
        return "Parei ⏹️"

    def pausar(self) -> str:
        if self._fonte is None:
            return "Não tem nada tocando."
        self.pausado = True
        return "Pausei ⏸️"

    def continuar(self) -> str:
        if not self.pausado:
            return "Não tem nada pausado."
        self.pausado = False
        return "Continuando ▶️"

    def repetir(self, ligar: bool | None = None) -> str:
        with self._trava:
            if self.fila.tocando is None and not self.fila.repetir:
                return "Não tem nada tocando pra repetir."
            self.fila.repetir = (not self.fila.repetir) if ligar is None else ligar
            return "🔁 Repetindo a música atual" if self.fila.repetir else "➡️ Repetição desligada"

    def limpar_fila(self) -> str:
        quantas = self.fila.limpar()
        return f"Limpei a fila ({quantas})" if quantas else "A fila já está vazia."

    def mudar_volume(self, volume: int) -> str:
        self.volume = service.limitar_volume(int(volume))
        return f"Volume em {self.volume}% 🔊"

    def descrever_fila(self) -> str:
        if self.fila.tocando is None:
            return "Não tem nada tocando."
        linhas = [f"Tocando: {self.fila.tocando.titulo}"]
        linhas += [f"{i}. {m.titulo}" for i, m in enumerate(self.fila.proximas, start=1)]
        return "\n".join(linhas)

    def estado(self) -> dict:
        tocando = self.fila.tocando
        return {
            "tocando": tocando.titulo if tocando else None,
            "link": tocando.link if tocando else None,
            "proximas": [m.titulo for m in self.fila.proximas],
            "volume": self.volume,
            "pausado": self.pausado,
            "repetir": self.fila.repetir,
            "eventos": list(self.eventos),
        }

    # ------------------------------------------------------------ por dentro

    def _avisar(self, texto: str) -> None:
        self.eventos.append((next(self._ids), texto))

    def _fechar_fonte(self) -> None:
        fonte, self._fonte = self._fonte, None
        if fonte is not None:
            fonte.fechar()

    def _comecar(self, musica: service.Musica, info: dict | None = None) -> None:
        """Abre `musica` e põe pra tocar. Levanta se não der (link morto, arquivo ruim)."""
        fonte = self._abrir(musica, info)
        self._inicio = self._relogio()
        self._fonte = fonte

    def _tocar_proxima(self, info: dict | None = None, avisar: bool = True) -> service.Musica | None:
        """Avança a fila até uma música abrir. `info` é a da primeira, já resolvida."""
        while True:
            musica = self.fila.avancar()
            if musica is None:
                if avisar:
                    self._avisar("A fila acabou.")
                return None
            self._tentativa = 0
            try:
                self._comecar(musica, info)
            except Exception:
                log.exception("falha ao tocar %s", musica.link)
                self._avisar(f"Não consegui tocar {musica.titulo}, pulei.")
                info = None
                continue
            self._avisar(f"Tocando agora: {musica.titulo}")
            return musica

    def _tratar_fins(self) -> None:
        while True:
            fonte = self._fins.get()
            fonte.fechar()
            try:
                with self._trava:
                    self._depois_de_tocar()
            finally:
                self._fins.task_done()

    def _depois_de_tocar(self) -> None:
        """A música acabou sozinha: tenta de novo se falhou logo de cara, repete se pedido, senão anda a fila."""
        musica = self.fila.tocando
        if musica is None or self._fonte is not None:
            return  # pararam ou trocaram enquanto isso
        falhou = self._relogio() - self._inicio < service.SEGUNDOS_PARA_FALHA_RAPIDA
        if falhou and self._tentativa == 0:
            log.warning("%s acabou logo de cara, tentando de novo", musica.link)
            self._tentativa = 1
            try:
                self._comecar(musica)
                return
            except Exception:
                log.exception("falha ao tentar de novo %s", musica.link)
        elif not falhou and self.fila.repetir:
            try:
                self._comecar(musica)
                return
            except Exception:
                log.exception("falha ao repetir %s", musica.link)
                self.fila.repetir = False
        if falhou:
            self._avisar(f"Não consegui tocar {musica.titulo}, pulei.")
        self._tocar_proxima()
