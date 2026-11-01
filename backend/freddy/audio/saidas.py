"""Pra onde o som da Mesa vai. Cada saída puxa os quadros no ritmo dela.

- SaidaLocal: a caixa de som deste computador (PortAudio, via sounddevice;
  no Fedora vai pro PipeWire, no Windows pro WASAPI/MME).
- SaidaMuda: puxa no ritmo do relógio e joga fora. Serve pros testes e pra
  quando não tem placa de som.
- SaidaDiscord (freddy/bot/saida.py): o discord.AudioSource cujo read() é
  mesa.ler_para_discord(). Com ela ativa, as daqui tocam a cópia.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Protocol

from freddy.audio.mesa import Mesa
from freddy.audio.pcm import AMOSTRAS_POR_QUADRO, BYTES_POR_AMOSTRA, BYTES_POR_QUADRO, CANAIS, QUADRO_MS, TAXA

log = logging.getLogger("freddy.audio")


class Saida(Protocol):
    nome: str

    def comecar(self) -> None: ...
    def fechar(self) -> None: ...


class SaidaLocal:
    nome = "local"

    def __init__(self, mesa: Mesa, dispositivo: int | str | None = None):
        self.mesa = mesa
        self.dispositivo = dispositivo
        self._stream = None

    def comecar(self) -> None:
        # Importa só aqui: sem PortAudio instalado, o resto do Freddy ainda sobe.
        import sounddevice as sd

        def pedir(saida, quadros, _tempo, status):
            if status.output_underflow:
                log.debug("a caixa de som ficou sem som por um instante")
            saida[:] = self.mesa.ler_para_local(quadros * CANAIS * BYTES_POR_AMOSTRA)

        self._stream = sd.RawOutputStream(
            samplerate=TAXA,
            channels=CANAIS,
            dtype="int16",
            blocksize=AMOSTRAS_POR_QUADRO,
            latency="high",  # folga contra engasgo; o atraso não importa pra música
            device=self.dispositivo,
            callback=pedir,
        )
        self._stream.start()

    def fechar(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None


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


def abrir_saida_local(mesa: Mesa) -> Saida:
    """A caixa de som; se não der (sem PortAudio, sem placa), avisa e segue mudo."""
    saida = SaidaLocal(mesa)
    try:
        saida.comecar()
        return saida
    except Exception as e:  # noqa: BLE001 — qualquer falha aqui vira "sem som", não queda
        log.warning("Não consegui abrir a caixa de som (%s). Sigo sem som.", e)
        muda = SaidaMuda(mesa)
        muda.comecar()
        return muda
