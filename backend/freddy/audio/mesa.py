"""A Mesa: onde o som é montado antes de sair, quadro a quadro.

Hoje tem uma camada só (a música). Na Fase 4 ganha ambiente e efeitos,
crossfade e ducking: tudo aqui, e as saídas não mudam. Quem dita o ritmo é
a saída (a caixa de som pede quadros; o Discord também pedirá): a Mesa
sempre responde na hora, com silêncio se não tiver nada.
"""

from __future__ import annotations

import threading
from typing import Callable

import numpy as np

from freddy.audio.fonte_ffmpeg import FonteFfmpeg
from freddy.audio.pcm import BYTES_POR_QUADRO, SILENCIO


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

    def _quadro(self) -> bytes:
        with self._trava:
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
