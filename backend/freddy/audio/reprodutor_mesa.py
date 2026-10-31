"""O Reprodutor de verdade: yt-dlp acha o áudio, o FFmpeg decodifica, a Mesa toca.

Implementa a mesma interface do Reprodutor do painel. O trabalho lento
(yt-dlp) roda numa thread; os avisos pro Motor saem por `agendar` (o
loop.call_soon_threadsafe do servidor). Cada carregar() ganha uma "carga":
aviso de carga velha (música que já foi pulada) é jogado fora.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

from freddy.audio.fonte_ffmpeg import FonteFfmpeg
from freddy.audio.mesa import Mesa
from freddy.audio.pcm import QUADROS_POR_SEGUNDO
from freddy.audio.reprodutor import OuvinteReprodutor
from freddy.audio.saidas import Saida
from freddy.audio.youtube import Fonte, motivo_em_portugues, resolver_youtube

log = logging.getLogger("freddy.audio")

# Música que "acaba" antes disso sem ninguém pular não tocou de verdade (o
# YouTube às vezes recusa a URL de áudio e o FFmpeg sai sem som). Igual ao Bardo.
SEGUNDOS_PARA_FALHA_RAPIDA = 5


class ReprodutorMesa:
    def __init__(
        self,
        abrir_saida: Callable[[Mesa], Saida],  # devolve a saída já tocando
        resolver: Callable[[str], Fonte] = resolver_youtube,
        agendar: Callable[[Callable[[], None]], object] | None = None,
        ffmpeg: str = "ffmpeg",
    ):
        self.mesa = Mesa()
        self.mesa.ao_primeiro_quadro = self._ao_primeiro_quadro
        self.mesa.ao_esgotar = self._ao_esgotar
        self._abrir_saida = abrir_saida
        self._saida: Saida | None = None
        self.resolver = resolver
        self.agendar = agendar or (lambda f: f())
        self.ffmpeg = ffmpeg
        self.ouvinte: OuvinteReprodutor | None = None
        self._trava = threading.Lock()
        self._carga = 0
        self._fonte_info: Fonte | None = None
        self._base = 0.0  # de onde a fonte atual começou (depois de buscar)

    # --- Reprodutor --------------------------------------------------------

    def ouvir(self, ouvinte: OuvinteReprodutor) -> None:
        self.ouvinte = ouvinte

    def carregar(self, link: str) -> None:
        if self._saida is None:
            self._saida = self._abrir_saida(self.mesa)
        with self._trava:
            self._carga += 1
            carga = self._carga
            self._fonte_info = None
            self._base = 0.0
            self.mesa.trocar(None)
        self.mesa.pausada = False
        threading.Thread(target=self._preparar, args=(link, carga), name="freddy-carregar", daemon=True).start()

    def tocar(self) -> None:
        self.mesa.pausada = False

    def pausar(self) -> None:
        self.mesa.pausada = True

    def parar(self) -> None:
        with self._trava:
            self._carga += 1
            self._fonte_info = None
            self.mesa.trocar(None)

    def buscar(self, segundos: float) -> None:
        with self._trava:
            info, carga = self._fonte_info, self._carga
            if info is None:
                return
            if info.duracao:
                segundos = min(segundos, max(info.duracao - 1, 0))
            self._base = max(segundos, 0.0)
            fonte = FonteFfmpeg(info.url, info.http_headers, self._base, self.ffmpeg)
            fonte.comecar()
            # Tudo dentro da trava: um parar() no meio não deixa som velho tocando.
            self.mesa.trocar(fonte, carga, ja_tocando=True)

    def definir_volume(self, volume: int) -> None:
        self.mesa.ganho = max(0, min(100, volume)) / 100

    def posicao(self) -> float:
        if self._fonte_info is None:
            return 0.0
        return round(self._base + self.mesa.quadros_tocados / QUADROS_POR_SEGUNDO, 1)

    def duracao(self) -> float:
        return self._fonte_info.duracao if self._fonte_info else 0.0

    def fechar(self) -> None:
        self.parar()
        if self._saida:
            self._saida.fechar()
            self._saida = None

    # --- por dentro --------------------------------------------------------

    def _atual(self, carga: int) -> bool:
        return carga == self._carga

    def _avisar(self, carga: int, nome: str, *args) -> None:
        def avisar():
            if self._atual(carga) and self.ouvinte:
                getattr(self.ouvinte, nome)(*args)

        self.agendar(avisar)

    def _preparar(self, link: str, carga: int) -> None:
        try:
            info = self.resolver(link)
        except Exception as e:  # noqa: BLE001 — qualquer falha do yt-dlp vira "falha" na fila
            log.info("Falha ao resolver %s: %s", link, e)
            self._avisar(carga, "erro", motivo_em_portugues(e))
            return
        fonte = FonteFfmpeg(info.url, info.http_headers, 0.0, self.ffmpeg)
        with self._trava:
            if not self._atual(carga):
                return  # pularam enquanto o yt-dlp trabalhava
            self._fonte_info = info
            try:
                fonte.comecar()
            except OSError as e:
                log.error("Não consegui rodar o FFmpeg (%s). Ele está instalado?", e)
                self._avisar(carga, "erro", "o FFmpeg não está instalado")
                return
            self.mesa.trocar(fonte, carga)
        self._avisar(carga, "titulo", info.titulo)

    def _ao_primeiro_quadro(self, carga: object) -> None:
        self._avisar(carga, "tocando")  # type: ignore[arg-type]

    def _ao_esgotar(self, carga: object, fonte: FonteFfmpeg, quadros: int) -> None:
        tocou = quadros / QUADROS_POR_SEGUNDO
        info = self._fonte_info
        curta_demais = tocou < SEGUNDOS_PARA_FALHA_RAPIDA and (info is None or info.duracao > SEGUNDOS_PARA_FALHA_RAPIDA * 2)
        if fonte.codigo_saida and curta_demais:
            log.info("FFmpeg saiu com %s: %s", fonte.codigo_saida, fonte.erro)
            self._avisar(carga, "erro", motivo_em_portugues(fonte.erro))  # type: ignore[arg-type]
        elif curta_demais and fonte.inicio == 0:
            self._avisar(carga, "erro", "o YouTube recusou o áudio")  # type: ignore[arg-type]
        else:
            self._avisar(carga, "fim")  # type: ignore[arg-type]
