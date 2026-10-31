"""Reprodutor que não toca nada: pros testes e pro `python -m freddy --sem-som`.

Guarda o que mandaram e deixa quem testa disparar os eventos (como o
ReprodutorFalso do motorLocal.test.ts). Com `simular=True` ele finge que
tocou: avisa "tocando" logo depois de carregar, o relógio anda sozinho e,
no fim da duração simulada, avisa "fim". Os avisos saem por `agendar` (o
servidor passa o loop.call_soon), nunca no meio da chamada do motor.
"""

from __future__ import annotations

import time
from typing import Callable

from freddy.audio.reprodutor import OuvinteReprodutor


class ReprodutorFalso:
    def __init__(
        self,
        simular: bool = False,
        duracao_simulada: float = 180.0,
        agendar: Callable[[Callable[[], None]], object] | None = None,
    ):
        self.agendar = agendar or (lambda f: f())
        self._carga = 0  # muda a cada carregar(): aviso de carga velha é ignorado
        self.ouvinte: OuvinteReprodutor | None = None
        self.carregados: list[str] = []
        self.volume = 0
        self.simular = simular
        self.duracao_simulada = duracao_simulada
        self._inicio: float | None = None  # relógio da simulação
        self._acumulado = 0.0

    def ouvir(self, ouvinte: OuvinteReprodutor) -> None:
        self.ouvinte = ouvinte

    def carregar(self, link: str) -> None:
        self.carregados.append(link)
        self._acumulado = 0.0
        self._inicio = None
        self._carga += 1
        if self.simular and self.ouvinte:
            self._inicio = time.monotonic()
            self._avisar("tocando")

    def _avisar(self, nome: str) -> None:
        carga = self._carga

        def avisar():
            if carga == self._carga and self.ouvinte:
                getattr(self.ouvinte, nome)()

        self.agendar(avisar)

    def tocar(self) -> None:
        if self.simular and self._inicio is None:
            self._inicio = time.monotonic()

    def pausar(self) -> None:
        if self._inicio is not None:
            self._acumulado += time.monotonic() - self._inicio
            self._inicio = None

    def parar(self) -> None:
        self._carga += 1
        self._inicio = None
        self._acumulado = 0.0

    def buscar(self, segundos: float) -> None:
        self._acumulado = segundos
        if self._inicio is not None:
            self._inicio = time.monotonic()

    def definir_volume(self, volume: int) -> None:
        self.volume = volume

    def posicao(self) -> float:
        if not self.simular:
            return 0.0
        andou = self._acumulado + (time.monotonic() - self._inicio if self._inicio is not None else 0.0)
        if andou >= self.duracao_simulada and self._inicio is not None:
            self._inicio = None
            self._acumulado = self.duracao_simulada
            self._avisar("fim")
        return round(min(andou, self.duracao_simulada), 1)

    def duracao(self) -> float:
        return self.duracao_simulada if self.simular and self.carregados else 0.0
