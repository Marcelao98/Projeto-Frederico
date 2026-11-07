"""Saída que puxa a Mesa no ritmo do relógio e joga o som fora: pros testes e
pra quando não tem placa de som."""

from __future__ import annotations

import threading
import time

from freddy.audio.mesa import Mesa
from freddy.audio.pcm import BYTES_POR_QUADRO, QUADRO_MS


class SaidaMuda:
    nome = "muda"

    def __init__(self, mesa: Mesa, velocidade: float = 1.0):
        self.mesa = mesa
        self.velocidade = velocidade  # >1 nos testes: a música "toca" mais rápido
        self._parar = threading.Event()
        self._thread: threading.Thread | None = None

    def comecar(self) -> None:
        self._parar.clear()
        self._thread = threading.Thread(target=self._rodar, name="saida-muda", daemon=True)
        self._thread.start()

    def _rodar(self) -> None:
        passo = QUADRO_MS / 1000 / self.velocidade
        proximo = time.monotonic()
        while not self._parar.is_set():
            self.mesa.ler_para_local(BYTES_POR_QUADRO)
            proximo += passo
            espera = proximo - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            else:
                proximo = time.monotonic()

    def fechar(self) -> None:
        self._parar.set()
        if self._thread:
            self._thread.join(timeout=1)
