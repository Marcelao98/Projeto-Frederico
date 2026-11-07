"""A Mesa: onde o som é montado antes de sair, quadro a quadro.

Hoje tem uma camada só (a música). Na Fase 4 ganha ambiente e efeitos,
crossfade e ducking: tudo aqui, e as saídas não mudam. Quem dita o ritmo é
a saída (a caixa de som pede quadros; o Discord também): a Mesa sempre
responde na hora, com silêncio se não tiver nada.

Um relógio só: com o bot numa call, quem puxa a Mesa é o Discord (ele pede
um quadro a cada 20 ms). A caixa de som então toca uma CÓPIA do que foi pra
call (se "ouvir aqui" estiver ligado), senão a música andaria em dobro. É o
"loopback" do Kenku FM.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Callable

import numpy as np

from freddy.audio.fontes.assobio import quadros_do_assobio
from freddy.audio.fontes.ffmpeg import FonteFfmpeg
from freddy.audio.pcm import BYTES_POR_QUADRO, QUADROS_POR_SEGUNDO, SILENCIO

MAX_COPIAS = 25  # 0,5 s de folga entre o Discord e a caixa de som


class Mesa:
    def __init__(self):
        self._trava = threading.Lock()
        self._fonte: FonteFfmpeg | None = None
        self._etiqueta: object = None
        self.ganho = 0.5
        self.pausada = False
        self.quadros_tocados = 0  # da fonte atual
        self._sobra = b""
        self._avisou_primeiro = False
        # Discord puxando (a caixa de som só ouve a cópia).
        self.no_discord = False
        self.ouvir_aqui = True
        self._copias: deque[bytes] = deque(maxlen=MAX_COPIAS)
        self._sobra_copia = b""
        # O assobio de teste (toca no lugar da música enquanto durar).
        self._assobio: list[bytes] = []
        # Pro diagnóstico: o volume do que saiu na caixa de som (últimos ~0,5 s).
        self._picos_local: deque[int] = deque(maxlen=25)
        # Chamados da thread do áudio, com a etiqueta da fonte: quem recebe
        # repassa pro loop do servidor e ignora etiqueta velha.
        self.ao_primeiro_quadro: Callable[[object], None] = lambda etiqueta: None
        self.ao_esgotar: Callable[[object, FonteFfmpeg, int], None] = lambda etiqueta, fonte, quadros: None

    def trocar(self, fonte: FonteFfmpeg | None, etiqueta: object = None, ja_tocando: bool = False) -> None:
        """Põe outra fonte no lugar (fecha a anterior). `ja_tocando`: é a mesma música, de outro ponto."""
        with self._trava:
            antiga, self._fonte, self._etiqueta = self._fonte, fonte, etiqueta
            self.quadros_tocados = 0
            self._avisou_primeiro = ja_tocando
            self._sobra = b""
        if antiga is not None and antiga is not fonte:
            antiga.fechar()

    def ler(self, nbytes: int = BYTES_POR_QUADRO) -> bytes:
        """`nbytes` de som pronto pra sair (sempre exatamente isso)."""
        partes = [self._sobra]
        tem = len(self._sobra)
        while tem < nbytes:
            q = self._quadro()
            partes.append(q)
            tem += len(q)
        junto = b"".join(partes)
        self._sobra = junto[nbytes:]
        return junto[:nbytes]

    def ler_para_discord(self) -> bytes:
        """O quadro que vai pra call (e a cópia pra caixa de som, se pedirem)."""
        quadro = self.ler(BYTES_POR_QUADRO)
        if self.ouvir_aqui:
            self._copias.append(quadro)
        return quadro

    def ler_para_local(self, nbytes: int = BYTES_POR_QUADRO) -> bytes:
        """O que a caixa de som toca: a Mesa mesmo, ou a cópia do Discord."""
        if not self.no_discord:
            saiu = self.ler(nbytes)
            self._picos_local.append(pico(saiu))
            return saiu
        partes, tem = [self._sobra_copia], len(self._sobra_copia)
        while tem < nbytes:
            try:
                q = self._copias.popleft()
            except IndexError:
                q = bytes(nbytes - tem)  # o Discord ainda não puxou: silêncio
            partes.append(q)
            tem += len(q)
        junto = b"".join(partes)
        self._sobra_copia = junto[nbytes:]
        saiu = junto[:nbytes]
        self._picos_local.append(pico(saiu))
        return saiu

    def entrar_no_discord(self) -> None:
        self._copias.clear()
        self._sobra_copia = b""
        self.no_discord = True

    def sair_do_discord(self) -> None:
        self.no_discord = False
        self._copias.clear()

    def assobiar(self) -> float:
        """Toca o assobio do Frederico (no lugar da música). Devolve quantos segundos dura."""
        quadros = list(quadros_do_assobio())
        with self._trava:
            self._assobio = quadros
        return len(quadros) / QUADROS_POR_SEGUNDO

    @property
    def assobiando(self) -> bool:
        return bool(self._assobio)

    def diagnostico(self) -> dict:
        """O que a Mesa está fazendo agora (pro modo debug do painel)."""
        fonte = self._fonte
        buffer = getattr(fonte, "segundos_no_buffer", 0.0) if fonte is not None else 0.0
        if self._assobio:
            musica = "assobiando"
        elif fonte is None:
            musica = "sem música"
        elif self.pausada:
            musica = "pausada"
        elif buffer > 0:
            musica = "tocando"
        else:
            musica = "engasgou" if self.quadros_tocados else "carregando"
        return {
            "musica": musica,
            "bufferSegundos": round(buffer, 1),
            "nivelLocal": max(self._picos_local, default=0),
            "mudoLocal": self.no_discord and not self.ouvir_aqui,
        }

    def _quadro(self) -> bytes:
        with self._trava:
            if self._assobio:
                return self._assobio.pop(0)
            fonte, etiqueta = self._fonte, self._etiqueta
            if fonte is None or self.pausada:
                return SILENCIO
            quadro = fonte.ler_quadro()
            if quadro is None:
                if fonte.esgotada:
                    self._fonte = None
                    quadros = self.quadros_tocados
                    avisar = lambda: self.ao_esgotar(etiqueta, fonte, quadros)  # noqa: E731
                else:
                    return SILENCIO  # ainda carregando, ou a rede engasgou
            else:
                self.quadros_tocados += 1
                primeiro = not self._avisou_primeiro
                self._avisou_primeiro = True
                avisar = (lambda: self.ao_primeiro_quadro(etiqueta)) if primeiro else None
                ganho = self.ganho
        if quadro is None:
            avisar()
            return SILENCIO
        if avisar:
            avisar()
        return aplicar_ganho(quadro, ganho)


def aplicar_ganho(quadro: bytes, ganho: float) -> bytes:
    if ganho >= 0.999:
        return quadro
    if ganho <= 0.001:
        return SILENCIO
    amostras = np.frombuffer(quadro, dtype=np.int16).astype(np.float32) * ganho
    return np.clip(amostras, -32768, 32767).astype(np.int16).tobytes()


def pico(quadro: bytes) -> int:
    """O volume mais alto do trecho (0 a 32767)."""
    if not quadro or quadro == SILENCIO:
        return 0
    return int(np.abs(np.frombuffer(quadro[: len(quadro) // 2 * 2], dtype=np.int16).astype(np.int32)).max())
